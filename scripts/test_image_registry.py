"""Regression tests for image/credential resolution and actual chart/Job rendering."""
import base64
import copy
import json
from pathlib import Path
import sys
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/deployment"))
from registry import plan, resolve
from preflight import inspect

SOFTWARE = yaml.safe_load((ROOT / "vars/software_references.yml").read_text())["software"]["addon_baikor_r"]
DEFAULTS = yaml.safe_load((ROOT / "default_inventory.yml").read_text())["all"]["children"]["controller"]["vars"]["inv_addons"]["baikor_r"]


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.core = dict(enable=True, registry_full_url="mirror.example:5000/project",
                         registry_url="mirror.example:5000", registry_username="mirror", registry_password="secret")
        self.package = dict(username="gitlab", password="token")
        self.args = dict(namespace="app", secret_name="pull", private_source=True)

    def image(self, config=None, core=None):
        return resolve(config or {}, SOFTWARE["baikor_r"], core or {}, self.package, **self.args)

    def test_default_gitlab(self):
        self.assertEqual(self.image()["host"], SOFTWARE["baikor_r"]["registry"])
        self.assertEqual(self.image()["username"], "gitlab")

    def test_inherit_enabled_core_with_path(self):
        result = self.image(core=self.core)
        self.assertEqual(result["image"], "mirror.example:5000/project/" + SOFTWARE["baikor_r"]["repository"])
        self.assertEqual(result["username"], "mirror")

    def test_disabled_core_is_ignored(self):
        self.assertEqual(self.image(core=dict(self.core, enable=False))["username"], "gitlab")

    def test_opt_out(self):
        self.assertEqual(self.image({"inherit_core": False}, self.core)["username"], "gitlab")

    def test_explicit_wins(self):
        result = self.image(dict(registry="another.example", repository="app", username="u", password="p"), self.core)
        self.assertEqual(result["image"], "another.example/app")
        self.assertEqual(result["username"], "u")

    def test_existing_secret(self):
        result = self.image(dict(registry="another.example", existing_pull_secret="operator"))
        self.assertTrue(result["existing"])
        self.assertEqual(result["secret"], "operator")
        self.assertEqual(result["password"], "")

    def test_rejections(self):
        for config in [
            dict(registry="mirror.example"), dict(repository="app"), dict(username="u"),
            dict(registry="https://mirror.example", username="u", password="p"),
            dict(registry="mirror.example", repository="app:tag", username="u", password="p"),
            dict(registry="mirror.example", username="u"),
            dict(registry="mirror.example", existing_pull_secret="operator", username="u", password="p"),
        ]:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    self.image(config)

    def test_core_credentials_never_use_helm_fallback(self):
        with self.assertRaises(ValueError):
            self.image(core=dict(self.core, registry_password=""))

    def test_all_image_plan_and_job(self):
        addon = copy.deepcopy(DEFAULTS)
        addon.update(ns_name="app", subdomain="baikor-r")
        addon["image_registry"].update(username="", password="")
        addon["database"].update(namespace="db", host="db.example")
        data = dict(addon=addon, software=SOFTWARE, core_registry=self.core, package=self.package)
        result = plan(data)
        self.assertFalse(result["errors"])
        self.assertEqual(result["images"]["bootstrap"]["namespace"], "db")
        self.assertEqual(result["images"]["bootstrap"]["username"], "mirror")
        environment = Environment(undefined=StrictUndefined)
        environment.filters["to_json"] = json.dumps
        environment.filters["bool"] = bool
        values = dict(inv_addons={"baikor_r": addon}, software={"addon_baikor_r": SOFTWARE},
                      baikor_registry_plan=result["images"], DOMAIN="example",
                      inv_access={"platform": {"hostname": "https://idm.example"}, "tenant": {"realm_name": "test"}},
                      inv_k8s={"ingress": {"ca_path": ""}, "ingress_class": "nginx"})
        for publication in [False, True]:
            addon["publication"]["enable"] = publication
            job = yaml.safe_load(environment.from_string((ROOT / "templates/database_bootstrap_job.yml.j2").read_text()).render(values))
            pod = job["spec"]["template"]["spec"]
            self.assertEqual(pod["imagePullSecrets"], [{"name": result["images"]["bootstrap"]["secret"]}])
            self.assertTrue(pod["containers"][0]["image"].startswith("mirror.example:5000/project/"))
            publisher = next(x for x in pod["containers"][0]["env"] if x["name"] == "BAIKOR_PUBLISHER")
            self.assertEqual("valueFrom" in publisher, publication)
        chart = yaml.safe_load(environment.from_string((ROOT / "templates/baikor_r_values.yml").read_text()).render(values))
        self.assertEqual(chart["image"]["repository"], result["images"]["application"]["image"])
        self.assertEqual(chart["imagePullSecrets"], [{"name": result["images"]["application"]["secret"]}])

    def test_public_bootstrap_needs_no_credentials(self):
        result = resolve({}, SOFTWARE["postgres_client"], {}, {}, namespace="db", secret_name="boot")
        self.assertEqual(result["secret"], "")


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.addon = copy.deepcopy(DEFAULTS)
        self.addon["ns_name"] = "app"
        self.addon["database"].update(host="db.example", namespace="db", ca_secret="")
        self.addon["database"]["bootstrap"].update(admin_secret="admin", generate_credentials=True)
        self.data = dict(addon=self.addon, package={"username": "u", "password": "secret"},
                         access={"namespace": "access", "secret": "idm"},
                         geoserver_enabled=True, geodata_namespace="geo", images={}, registry_errors=[])

    def test_config_valid_and_no_publisher(self):
        result = inspect(self.data)
        self.assertEqual(result["errors"], [])
        self.assertNotIn("Database publisher", [r["purpose"] for r in result["requests"]])

    def test_collect_all_errors(self):
        self.addon["database"].update(host="", ssl_mode="wrong")
        self.data["package"] = {}
        self.assertEqual(len(inspect(self.data)["errors"]), 3)

    def test_generation_only_when_bootstrap_enabled(self):
        self.addon["database"]["bootstrap"]["enable"] = False
        result = inspect(self.data)
        self.assertFalse(next(r for r in result["requests"] if r["purpose"] == "Database writer")["optional"])

    def test_secret_failure_messages_do_not_leak(self):
        request = inspect(self.data)["requests"][0]
        self.data["observed"] = [{"item": request, "resources": [{"data": {"username": "super-secret"}}]}]
        result = inspect(self.data)
        self.assertTrue(result["errors"])
        self.assertNotIn("super-secret", json.dumps(result))

    def test_missing_required_secrets(self):
        self.data["observed"] = [{"item": r, "resources": []} for r in inspect(self.data)["requests"]]
        self.assertEqual(len(inspect(self.data)["errors"]), 2)  # admin and Keycloak, generated writer/owner optional

    def test_custom_ansible_loop_variable_is_supported(self):
        self.data["observed"] = [
            {"baikor_preflight_request": request, "resources": []}
            for request in inspect(self.data)["requests"]
        ]
        self.assertEqual(len(inspect(self.data)["errors"]), 2)

    def test_duplicate_role_names(self):
        requests = inspect(self.data)["requests"][:2]
        secret = {"data": {k: base64.b64encode(v.encode()).decode() for k, v in {"username": "same", "password": "pw"}.items()}}
        self.data["observed"] = [{"item": r, "resources": [secret]} for r in requests]
        self.assertIn("must not share a username", inspect(self.data)["errors"][0])

    def test_publication_and_export_prerequisites(self):
        self.addon["publication"]["masterportal"]["enable"] = True
        self.assertEqual(len(inspect(self.data)["errors"]), 2)

    def test_wrong_registry_secret(self):
        self.data["images"] = {"application": dict(existing=True, secret="pull", namespace="app", host="expected")}
        request = inspect(self.data)["requests"][-1]
        payload = base64.b64encode(json.dumps({"auths": {"other": {}}}).encode()).decode()
        self.data["observed"] = [{"item": request, "resources": [{"type": "kubernetes.io/dockerconfigjson", "data": {".dockerconfigjson": payload}}]}]
        self.assertTrue(inspect(self.data)["errors"])


if __name__ == "__main__":
    unittest.main()
