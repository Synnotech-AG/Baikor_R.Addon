"""Render provisioning requests and check role grants, upgrade revocation and scopes.

Uses only synthetic representations; never contacts Keycloak or Kubernetes.
"""
import base64
import copy
import json
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
HUMAN_ROLES = ["baikor_viewer", "baikor_editor", "baikor_approver", "baikor_admin"]
ROLES = [{"id": name + "-id", "name": name, "clientRole": True}
         for name in [*HUMAN_ROLES, "baikor_importer"]]


class KeycloakPermissionsTests(unittest.TestCase):
    def setUp(self):
        self.environment = Environment(undefined=StrictUndefined)
        self.environment.filters.update(to_json=json.dumps, bool=bool,
                                        b64decode=lambda value: base64.b64decode(value).decode())
        self.context = {
            "addon_dir": ROOT.as_posix() + "/", "DOMAIN": "example.test",
            "inv_addons": {"baikor_r": {
                "authentication": {"assign_platform_admin_roles": False},
                "imports": {"service_account": {"enable": True, "client_id": "baikor-r-import"}},
            }},
            "inv_k8s": {"ingress": {"ca_path": "fixture.crt"}},
            "inv_access": {"platform": {"hostname": "https://identity.example.test"},
                           "tenant": {"realm_name": "fixture"}},
            "baikor_keycloak_client_uuid": "browser-uuid",
            "baikor_import_keycloak_client_uuid": "import-uuid",
            "baikor_keycloak_login": {"json": {"access_token": "synthetic-token"}},
            "baikor_keycloak_admin_credentials": {"resources": [{"data": {
                "MASTER_USERNAME": base64.b64encode(b"synthetic-user").decode(),
                "MASTER_PASSWORD": base64.b64encode(b"synthetic-password").decode(),
            }}]},
            "baikor_keycloak_clients": {"json": [{"id": "browser-uuid"}]},
            "baikor_import_keycloak_clients": {"json": [{"id": "import-uuid"}]},
            "baikor_import_service_account": {"json": {"id": "service-user"}},
            "baikor_keycloak_admin_users": {"json": [{"id": "platform-admin"}]},
            "baikor_keycloak_roles": {"json": copy.deepcopy(ROLES)},
            "baikor_keycloak_editor_role": {"json": copy.deepcopy(ROLES[1])},
            "baikor_keycloak_importer_role": {"json": copy.deepcopy(ROLES[-1])},
        }
        self.environment.globals["lookup"] = self.lookup

    def lookup(self, kind, path):
        self.assertEqual(kind, "template")
        return self.environment.from_string(Path(path).read_text()).render(self.context)

    def render(self, value):
        if isinstance(value, dict):
            return {key: self.render(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.render(item) for item in value]
        if isinstance(value, str):
            if value.startswith("{{") and value.endswith("}}") and value.count("{{") == 1:
                return self.environment.compile_expression(value[2:-2], undefined_to_none=False)(self.context)
            return self.environment.from_string(value).render(self.context)
        return value

    def requests(self, path="tasks/baikor_r/keycloak.yml"):
        requests = []
        for task in yaml.safe_load((ROOT / path).read_text()):
            conditions = task.get("when", [])
            if isinstance(conditions, str):
                conditions = [conditions]
            if not all(self.environment.compile_expression(condition)(self.context) for condition in conditions):
                continue
            if "ansible.builtin.include_tasks" in task:
                included = Path(self.render(task["ansible.builtin.include_tasks"])).relative_to(ROOT)
                requests.extend(self.requests(included))
            if "ansible.builtin.set_fact" in task:
                self.context.update(self.render(task["ansible.builtin.set_fact"]))
            if "ansible.builtin.uri" not in task:
                continue
            for item in self.render(task.get("loop", [None])):
                self.context[task.get("loop_control", {}).get("loop_var", "item")] = item
                request = self.render(task["ansible.builtin.uri"])
                if isinstance(request.get("body"), str) and request.get("body_format") == "json":
                    request["body"] = json.loads(request["body"])
                requests.append(request)
        return requests

    def test_browser_provisioning_disables_full_scope_and_grants_all_human_roles(self):
        requests = self.requests()
        browser_writes = [r for r in requests if r["method"] in ("POST", "PUT")
                          and isinstance(r.get("body"), dict) and r["body"].get("clientId") == "baikor-r"]
        self.assertEqual(len(browser_writes), 2)
        for request in browser_writes:
            self.assertFalse(request["body"]["fullScopeAllowed"])
            self.assertTrue(request["body"]["standardFlowEnabled"])
            self.assertFalse(request["body"]["serviceAccountsEnabled"])
        scope = [r for r in requests if r["method"] == "POST"
                 and r["url"].endswith("/clients/browser-uuid/scope-mappings/clients/browser-uuid")]
        self.assertEqual(len(scope), 1)
        self.assertEqual({role["name"] for role in scope[0]["body"]}, set(HUMAN_ROLES))

    def test_importer_upgrade_revokes_editor_assignment_and_scope_before_granting_importer(self):
        requests = self.requests("tasks/baikor_r/import_client.yml")
        for suffix in ("/users/service-user/role-mappings/clients/browser-uuid",
                       "/clients/import-uuid/scope-mappings/clients/browser-uuid"):
            writes = [r for r in requests if r["url"].endswith(suffix)]
            self.assertEqual([r["method"] for r in writes], ["DELETE", "POST"])
            self.assertEqual([role["name"] for role in writes[0]["body"]], ["baikor_editor"])
            self.assertEqual([role["name"] for role in writes[1]["body"]], ["baikor_importer"])
        client = next(r["body"] for r in requests if r["method"] == "PUT")
        self.assertFalse(client["fullScopeAllowed"])
        self.assertTrue(client["serviceAccountsEnabled"])
        self.assertFalse(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        audience = next(m for m in client["protocolMappers"] if m["protocolMapper"] == "oidc-audience-mapper")
        self.assertEqual(audience["config"]["included.client.audience"], "baikor-r")

    def test_importer_role_is_created_only_when_machine_integration_is_enabled(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.context["inv_addons"]["baikor_r"]["imports"]["service_account"]["enable"] = enabled
                requests = self.requests()
                created_roles = [r["body"]["name"] for r in requests if r["method"] == "POST"
                                 and r["url"].endswith("/clients/browser-uuid/roles")]
                self.assertEqual(set(created_roles), set(HUMAN_ROLES + (["baikor_importer"] if enabled else [])))
                if not enabled:
                    self.assertFalse(any("import-uuid" in r["url"] or "service-user" in r["url"] for r in requests))

    def test_platform_admin_opt_in_assigns_human_roles_only(self):
        self.context["inv_addons"]["baikor_r"]["authentication"]["assign_platform_admin_roles"] = True
        assignment = next(r for r in self.requests()
                          if r["url"].endswith("/users/platform-admin/role-mappings/clients/browser-uuid"))
        self.assertEqual({role["name"] for role in assignment["body"]}, set(HUMAN_ROLES))


if __name__ == "__main__":
    unittest.main()
