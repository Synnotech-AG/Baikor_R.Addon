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
    def render(self, core_environment=None):
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
        values = yaml.safe_load(renderer.from_string((ROOT / "templates/baikor_r_values.yml").read_text()).render(context))
        return values["aspnetCore"]["environment"]

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
