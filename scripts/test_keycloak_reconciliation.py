"""Execute the real addon Keycloak URI tasks against a disposable Keycloak.

Run with keycloak-tests.compose.yaml. Only the uniquely named fixture realms are
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

from jinja2 import Environment
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

    for legacy in (False, True):
        token = login()
        realm = "baikor-reconciliation-" + secrets.token_hex(6)
        admin = "/admin/realms/" + realm
        variables = {
            "addon_dir": ROOT.as_posix() + "/", "DOMAIN": "fixture.test",
            "inv_addons": {"baikor_r": {"authentication": {"assign_platform_admin_roles": False},
                "imports": {"service_account": {"enable": True, "client_id": "baikor-r-import"}}}},
            "inv_access": {"platform": {"hostname": BASE}, "tenant": {"realm_name": realm}},
            "inv_k8s": {"ingress": {"ca_path": ""}},
            "baikor_keycloak_admin_credentials": {"resources": [{"data": {
                "MASTER_USERNAME": base64.b64encode(username.encode()).decode(),
                "MASTER_PASSWORD": base64.b64encode(password.encode()).decode(),
            }}]},
        }
        request("/admin/realms", "POST", {"realm": realm, "enabled": True}, token)
        try:
            if legacy:
                environment = Environment()
                environment.filters["to_json"] = json.dumps
                for template in ("keycloak_client.json.j2", "keycloak_import_client.json.j2"):
                    client = json.loads(environment.from_string((ROOT / "templates" / template).read_text()).render(variables))
                    if client["clientId"] == "baikor-r":
                        client["fullScopeAllowed"] = True
                    request(admin + "/clients", "POST", client, token)
                browser = request(admin + "/clients?clientId=baikor-r", token=token)[0]
                importer = request(admin + "/clients?clientId=baikor-r-import", token=token)[0]
                for role in HUMAN_ROLES:
                    request(admin + f"/clients/{browser['id']}/roles", "POST", {"name": role}, token)
                editor = request(admin + f"/clients/{browser['id']}/roles/baikor_editor", token=token)
                user = request(admin + f"/clients/{importer['id']}/service-account-user", token=token)
                request(admin + f"/users/{user['id']}/role-mappings/clients/{browser['id']}", "POST", [editor], token)
                request(admin + f"/clients/{importer['id']}/scope-mappings/clients/{browser['id']}", "POST", [editor], token)
                for path in (f"/users/{user['id']}/role-mappings/clients/{browser['id']}",
                             f"/clients/{importer['id']}/scope-mappings/clients/{browser['id']}"):
                    assert [role["name"] for role in request(admin + path, token=token)] == ["baikor_editor"]
            for iteration in (1, 2):
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
                        raise RuntimeError(f"Ansible reconciliation failed at {failed_task}")
                # The master realm's short administrator token may expire while
                # Ansible runs. Refresh our separate inspection credentials.
                token = login()
                browser = request(admin + "/clients?clientId=baikor-r", token=token)[0]
                importer = request(admin + "/clients?clientId=baikor-r-import", token=token)[0]
                assert browser["fullScopeAllowed"] is False
                scopes = request(admin + f"/clients/{browser['id']}/scope-mappings/clients/{browser['id']}", token=token)
                assert {role["name"] for role in scopes} == set(HUMAN_ROLES)
                assert importer["fullScopeAllowed"] is False
                user = request(admin + f"/clients/{importer['id']}/service-account-user", token=token)
                for path in (f"/users/{user['id']}/role-mappings/clients/{browser['id']}",
                             f"/clients/{importer['id']}/scope-mappings/clients/{browser['id']}"):
                    roles = request(admin + path, token=token)
                    assert [role["name"] for role in roles] == ["baikor_importer"]
                secret = request(admin + f"/clients/{importer['id']}/client-secret", token=token)["value"]
                access_token = request(f"/realms/{realm}/protocol/openid-connect/token", "POST", {
                    "grant_type": "client_credentials", "client_id": "baikor-r-import", "client_secret": secret,
                }, form=True)["access_token"]
                claims = json.loads(base64.urlsafe_b64decode(access_token.split(".")[1] + "=="))
                assert claims["roles"] == ["baikor_importer"]
                audience = claims["aud"]
                assert "baikor-r" in ([audience] if isinstance(audience, str) else audience)
                print(f"PASS actual Ansible {'legacy editor upgrade' if legacy else 'fresh install'} run {iteration}: explicit browser scopes; importer-only token", flush=True)
        finally:
            request(admin, "DELETE", token=login())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
