"""Render the managed feature-type requests for first and repeat deployments."""
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "tasks/baikor_r/geoserver.yml").read_text())


class GeoServerFeatureTypeTests(unittest.TestCase):
    def requests(self, status, name="public_construction_site_areas", title="Changed title"):
        environment = Environment(undefined=StrictUndefined)
        context = {
            "baikor_geoserver_datastore_url": "https://geo.example/geoserver/rest/workspaces/operator/datastores/baikor",
            "feature_type_result": {"status": status, "feature_type": {
                "name": name, "title": title, "abstract": "Updated description",
            }},
        }
        result = []
        for task in TASKS:
            uri = task.get("ansible.builtin.uri", {})
            if "featureType" not in uri.get("body", {}):
                continue
            if not environment.compile_expression(task["when"])(context):
                continue
            body = {key: environment.from_string(value).render(context) if isinstance(value, str) else value
                    for key, value in uri["body"]["featureType"].items()}
            result.append((uri["method"], environment.from_string(uri["url"]).render(context), body, uri["status_code"]))
        return result

    def test_missing_feature_type_is_created_once(self):
        requests = self.requests(404)
        self.assertEqual(len(requests), 1)
        self.assertEqual((requests[0][0], requests[0][3]), ("POST", 201))
        self.assertTrue(requests[0][1].endswith("/featuretypes.json"))

    def test_existing_area_and_search_types_are_updated_in_place(self):
        for name in ("public_construction_site_areas", "public_construction_sites"):
            with self.subTest(name=name):
                requests = self.requests(200, name)
                self.assertEqual(len(requests), 1)
                method, url, body, status = requests[0]
                self.assertEqual((method, status), ("PUT", 200))
                self.assertEqual(url.rsplit("/", 1)[-1], name + ".json")
                self.assertEqual(body, {
                    "name": name, "nativeName": name, "title": "Changed title",
                    "abstract": "Updated description", "srs": "EPSG:25832",
                    "projectionPolicy": "FORCE_DECLARED", "enabled": True, "advertised": True,
                })

    def test_updates_keep_the_same_managed_definition_as_creation(self):
        self.assertEqual(self.requests(404)[0][2], self.requests(200)[0][2])

    def test_unexpected_read_status_does_not_trigger_a_write(self):
        self.assertEqual(self.requests(500), [])


if __name__ == "__main__":
    unittest.main()
