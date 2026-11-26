"""Verify Core environment names produce canonical ASP.NET environments."""
import copy
import json
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = yaml.safe_load((ROOT / "default_inventory.yml").read_text())["all"]["children"]["controller"]["vars"]["inv_addons"]["baikor_r"]


class HelmEnvironmentTests(unittest.TestCase):
    def render_values(self, core_environment=None, overrides=None):
        renderer = Environment(undefined=StrictUndefined)
        renderer.filters.update(to_json=json.dumps, bool=bool)
        context = dict(
            inv_addons={"baikor_r": copy.deepcopy(DEFAULTS)},
            software={"addon_baikor_r": {"baikor_r": {"tag": "test"}}},
            baikor_registry_plan={"application": {"image": "registry.example/baikor-r", "secret": ""}},
            DOMAIN="example",
            inv_access={"platform": {"hostname": "https://idm.example"}, "tenant": {"realm_name": "test"}},
            inv_k8s={"ingress": {"ca_path": ""}, "ingress_class": "nginx"},
        )
        if core_environment is not None:
            context["ENVIRONMENT"] = core_environment
        context["inv_addons"]["baikor_r"].update(overrides or {})
        values = yaml.safe_load(renderer.from_string((ROOT / "templates/baikor_r_values.yml").read_text()).render(context))
        return values

    def render(self, core_environment=None):
        return self.render_values(core_environment)["aspnetCore"]["environment"]

    def test_native_mail_uses_persistent_dedicated_key_without_import_account(self):
        values = self.render_values()
        self.assertEqual(values.get("mailImports"), {
            "workerEnabled": True,
            "encryption": {"existingSecret": {"name": "baikor-r-mail-encryption", "key": "key"}}})
        self.assertFalse(DEFAULTS["imports"]["service_account"]["enable"])

    def test_operator_mail_key_reference_and_worker_switch_are_preserved(self):
        values = self.render_values(overrides={"mail_imports": {
            "worker_enabled": False, "encryption_secret": "operator-mail-key"}})
        self.assertEqual(values.get("mailImports"), {
            "workerEnabled": False,
            "encryption": {"existingSecret": {"name": "operator-mail-key", "key": "key"}}})

    def test_development_names(self):
        for name in ("dev", "development", "local", " DEV ", "Development"):
            with self.subTest(name=name):
                self.assertEqual(self.render(name), "Development")

    def test_test_and_staging_names(self):
        for name in ("tst", "test", "testing", "stg", "stage", "staging", "qa", "Staging"):
            with self.subTest(name=name):
                self.assertEqual(self.render(name), "Staging")

    def test_production_and_unknown_names_fail_safe_to_production(self):
        for name in (None, "", "prd", "prod", "production", "Production", "customer-name"):
            with self.subTest(name=name):
                self.assertEqual(self.render(name), "Production")


if __name__ == "__main__":
    unittest.main()
