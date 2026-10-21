"""Execute the real addon Keycloak URI tasks against a disposable Keycloak.

Run with keycloak-tests.compose.yaml. Only the uniquely named fixture realm is
modified; Kubernetes secret reads/writes are omitted from this identity-only test.
"""
import base64
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://keycloak:8080"
HUMAN_ROLES = ["baikor_viewer", "baikor_editor", "baikor_approver", "baikor_admin"]


def request(path, method="GET", body=None, token=None, form=False):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
        body = (urllib.parse.urlencode(body) if form else json.dumps(body)).encode()
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    content = response.read()
    if response.status not in (200, 201, 204):
        raise RuntimeError(f"Disposable Keycloak request failed: {method} HTTP {response.status}")
    return json.loads(content) if content else None


def identity_tasks():
    tasks = []
    for task in yaml.safe_load((ROOT / "tasks/baikor_r/keycloak.yml").read_text()):
        if any(key.startswith("kubernetes.") for key in task):
            continue
        if "ansible.builtin.include_tasks" in task:
            for child in yaml.safe_load((ROOT / "tasks/baikor_r/import_client.yml").read_text()):
                if any(key.startswith("kubernetes.") for key in child):
                    continue
                child = copy.deepcopy(child)
                conditions = child.get("when", [])
                if isinstance(conditions, str):
                    conditions = [conditions]
                child["when"] = [task["when"], *conditions]
                tasks.append(child)
        else:
            tasks.append(task)
    return tasks


def main():
    deadline = time.monotonic() + 180
    while True:
        try:
            request("/realms/master/.well-known/openid-configuration")
            break
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Disposable Keycloak did not become ready")
            time.sleep(2)
    username, password = os.environ["BAIKOR_TEST_ADMIN_USERNAME"], os.environ["BAIKOR_TEST_ADMIN_PASSWORD"]
    def login():
        return request("/realms/master/protocol/openid-connect/token", "POST", {
            "grant_type": "password", "client_id": "admin-cli", "username": username, "password": password,
        }, form=True)["access_token"]

    realm = "baikor-reconciliation-" + secrets.token_hex(6)
    admin = "/admin/realms/" + realm
    variables = {
        "addon_dir": ROOT.as_posix() + "/", "DOMAIN": "fixture.test",
        "inv_addons": {"baikor_r": {"authentication": {"assign_platform_admin_roles": False},
            "imports": {"service_account": {"enable": False, "client_id": "baikor-r-import"}}}},
        "inv_access": {"platform": {"hostname": BASE}, "tenant": {"realm_name": realm}},
        "inv_k8s": {"ingress": {"ca_path": ""}},
        "baikor_keycloak_admin_credentials": {"resources": [{"data": {
            "MASTER_USERNAME": base64.b64encode(username.encode()).decode(),
            "MASTER_PASSWORD": base64.b64encode(password.encode()).decode(),
        }}]},
    }
    browser_identity = human_role_ids = importer_identity = None
    request("/admin/realms", "POST", {"realm": realm, "enabled": True}, login())
    try:
        for phase, imports_enabled in (("fresh browser install", False),
                                       ("enable imports", True), ("repeat deployment", True)):
            variables["inv_addons"]["baikor_r"]["imports"]["service_account"]["enable"] = imports_enabled
            with tempfile.TemporaryDirectory(prefix="baikor-ansible-test-") as directory:
                playbook = Path(directory) / "identity.yml"
                playbook.write_text(yaml.safe_dump([{
                    "hosts": "localhost", "connection": "local", "gather_facts": False,
                    "vars": variables, "tasks": identity_tasks(),
                }]), encoding="utf-8")
                result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(playbook)],
                                        capture_output=True, text=True)
                if result.returncode:
                    # no_log on the actual tasks prevents secret output; keep diagnostics minimal.
                    failed_task = next((line for line in reversed(result.stdout.splitlines())
                                        if line.startswith("TASK [")), "unknown task")
                    raise RuntimeError(f"Ansible {phase} failed at {failed_task}")
            # The master realm's short administrator token may expire while
            # Ansible runs. Refresh our separate inspection credentials.
            token = login()
            browsers = request(admin + "/clients?clientId=baikor-r", token=token)
            assert len(browsers) == 1, "Expected exactly one browser client"
            browser = browsers[0]
            assert browser["fullScopeAllowed"] is False
            assert browser["standardFlowEnabled"] is True
            assert browser["serviceAccountsEnabled"] is False
            browser_secret = request(admin + f"/clients/{browser['id']}/client-secret", token=token)["value"]
            observed_browser_identity = (browser["id"], browser_secret)
            if browser_identity is None:
                browser_identity = observed_browser_identity
            else:
                assert observed_browser_identity == browser_identity, "Browser identity or secret changed"
            roles = request(admin + f"/clients/{browser['id']}/roles", token=token)
            expected_roles = set(HUMAN_ROLES) | ({"baikor_importer"} if imports_enabled else set())
            assert {role["name"] for role in roles} == expected_roles
            observed_human_role_ids = {role["name"]: role["id"] for role in roles if role["name"] in HUMAN_ROLES}
            if human_role_ids is None:
                human_role_ids = observed_human_role_ids
            else:
                assert observed_human_role_ids == human_role_ids, "Human roles were replaced"
            scopes = request(admin + f"/clients/{browser['id']}/scope-mappings/clients/{browser['id']}", token=token)
            assert {role["name"] for role in scopes} == set(HUMAN_ROLES)

            importers = request(admin + "/clients?clientId=baikor-r-import", token=token)
            if not imports_enabled:
                assert importers == [], "Disabled imports created a machine client"
                print(f"PASS actual Ansible {phase}: exact human roles/scopes; no importer client or role", flush=True)
                continue
            assert len(importers) == 1, "Expected exactly one importer client"
            importer = importers[0]
            assert importer["fullScopeAllowed"] is False
            assert importer["serviceAccountsEnabled"] is True
            assert importer["standardFlowEnabled"] is False
            assert importer["directAccessGrantsEnabled"] is False
            user = request(admin + f"/clients/{importer['id']}/service-account-user", token=token)
            for path in (f"/users/{user['id']}/role-mappings/clients/{browser['id']}",
                         f"/clients/{importer['id']}/scope-mappings/clients/{browser['id']}"):
                assigned_roles = request(admin + path, token=token)
                assert [role["name"] for role in assigned_roles] == ["baikor_importer"]
            secret = request(admin + f"/clients/{importer['id']}/client-secret", token=token)["value"]
            observed_importer_identity = (importer["id"], user["id"], secret)
            if importer_identity is None:
                importer_identity = observed_importer_identity
            else:
                assert observed_importer_identity == importer_identity, "Importer identity or secret changed"
            access_token = request(f"/realms/{realm}/protocol/openid-connect/token", "POST", {
                "grant_type": "client_credentials", "client_id": "baikor-r-import", "client_secret": secret,
            }, form=True)["access_token"]
            claims = json.loads(base64.urlsafe_b64decode(access_token.split(".")[1] + "=="))
            assert claims["roles"] == ["baikor_importer"]
            assert claims["azp"] == "baikor-r-import"
            audience = claims["aud"]
            assert "baikor-r" in ([audience] if isinstance(audience, str) else audience)
            print(f"PASS actual Ansible {phase}: human roles/scopes preserved; importer-only token and stable credentials", flush=True)
    finally:
        request(admin, "DELETE", token=login())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
