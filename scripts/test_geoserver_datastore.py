"""Render real datastore requests; validate the optional operator-owned JNDI path."""
import base64
import copy
from pathlib import Path
import sys
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/deployment"))
from preflight import inspect

DEFAULTS = yaml.safe_load((ROOT / "default_inventory.yml").read_text())["all"]["children"]["controller"]["vars"]["inv_addons"]["baikor_r"]
TASKS = yaml.safe_load((ROOT / "tasks/baikor_r/geoserver.yml").read_text())


class GeoServerDatastoreTests(unittest.TestCase):
    def setUp(self):
        self.addon = copy.deepcopy(DEFAULTS)
        self.addon["database"].update(host="postgres.example", port=5432, name="baikor_test", namespace="db")
        self.addon["database"]["bootstrap"]["admin_secret"] = "bootstrap-admin"
        self.addon["publication"].update(enable=True, workspace="public_data", datastore="baikor-r")
        self.context = {
            "inv_addons": {"baikor_r": self.addon},
            "inv_gd": {"domain": "example"},
            "baikor_database_publication_credentials": {"resources": [{"data": {
                "username": base64.b64encode(b"publisher").decode(),
                "password": base64.b64encode(b"publisher-password").decode(),
            }}]},
        }
        self.environment = Environment(undefined=StrictUndefined)
        self.environment.filters["b64decode"] = lambda value: base64.b64decode(value).decode()

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

    def requests(self, status):
        self.context["baikor_geoserver_datastore"] = {"status": status}
        requests = []
        for task in TASKS:
            conditions = task.get("when", [])
            if isinstance(conditions, str):
                conditions = [conditions]
            if "ansible.builtin.set_fact" in task:
                if all(self.environment.compile_expression(condition)(self.context) for condition in conditions):
                    self.context.update(self.render(task["ansible.builtin.set_fact"]))
            uri = task.get("ansible.builtin.uri", {})
            if "dataStore" not in uri.get("body", {}):
                continue
            if all(self.environment.compile_expression(condition)(self.context) for condition in conditions):
                requests.append((uri["method"], self.render(uri["body"])))
        return requests

    def test_direct_create_and_update_use_geotools_ssl_enum_and_publisher_login(self):
        for mode, expected in (("VerifyFull", "VERIFY_FULL"), ("VerifyCA", "VERIFY_CA"), ("Require", "REQUIRE")):
            self.addon["database"]["ssl_mode"] = mode
            for status, method in ((404, "POST"), (200, "PUT")):
                with self.subTest(mode=mode, status=status):
                    requests = self.requests(status)
                    self.assertEqual(len(requests), 1)
                    self.assertEqual(requests[0][0], method)
                    store = requests[0][1]["dataStore"]
                    self.assertEqual(store["name"], "baikor-r")
                    self.assertEqual(store.get("type"), "PostGIS")
                    parameters = {entry["@key"]: entry["$"] for entry in store["connectionParameters"]["entry"]}
                    self.assertEqual(parameters, {
                        "host": "postgres.example", "port": "5432", "database": "baikor_test",
                        "schema": "baikor", "user": "publisher", "passwd": "publisher-password",
                        "dbtype": "postgis", "SSL mode": expected,
                    })

    def test_jndi_create_and_update_omit_inline_connection_and_credentials(self):
        self.addon["publication"]["jndi_reference"] = "java:comp/env/jdbc/baikor"
        for status, method in ((404, "POST"), (200, "PUT")):
            with self.subTest(status=status):
                requests = self.requests(status)
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0][0], method)
                self.assertEqual(requests[0][1]["dataStore"].get("type"), "PostGIS (JNDI)")
                entries = requests[0][1]["dataStore"]["connectionParameters"]["entry"]
                self.assertEqual({entry["@key"]: entry["$"] for entry in entries}, {
                    "dbtype": "postgis", "jndiReferenceName": "java:comp/env/jdbc/baikor", "schema": "baikor",
                })

    def preflight(self):
        return inspect(dict(addon=self.addon, access={"namespace": "access", "secret": "idm"},
                            geoserver_enabled=True, geodata_namespace="geo"))

    def test_switching_connection_mode_replaces_factory_and_connection_parameters(self):
        for reference, expected_type, expected_keys in (
                ("", "PostGIS", {"host", "port", "database", "schema", "user", "passwd", "dbtype", "SSL mode"}),
                ("java:comp/env/jdbc/baikor", "PostGIS (JNDI)", {"dbtype", "jndiReferenceName", "schema"}),
                ("", "PostGIS", {"host", "port", "database", "schema", "user", "passwd", "dbtype", "SSL mode"})):
            with self.subTest(reference=reference):
                self.addon["publication"]["jndi_reference"] = reference
                method, body = self.requests(200)[0]
                self.assertEqual(method, "PUT")
                self.assertEqual(body["dataStore"]["type"], expected_type)
                self.assertEqual({entry["@key"] for entry in body["dataStore"]["connectionParameters"]["entry"]},
                                 expected_keys)

    def test_jndi_validation_accepts_empty_or_local_jdbc_reference(self):
        for reference in ("", "java:comp/env/jdbc/baikor", "java:comp/env/jdbc/customer/baikor-reader"):
            with self.subTest(reference=reference):
                self.addon["publication"]["jndi_reference"] = reference
                self.assertEqual(self.preflight()["errors"], [])

    def test_jndi_validation_rejects_malformed_references(self):
        for reference in (None, True, 42, " ", "jdbc/baikor", "ldap://example/baikor",
                          "java:comp/env/jdbc/", "java:comp/env/jdbc/with space", "java:comp/env/jdbc/baikor\n"):
            with self.subTest(reference=reference):
                self.addon["publication"]["jndi_reference"] = reference
                self.assertTrue(any("publication.jndi_reference" in error for error in self.preflight()["errors"]))

    def test_jndi_still_requires_publisher_secret_for_grant_reconciliation(self):
        self.addon["publication"]["jndi_reference"] = "java:comp/env/jdbc/baikor"
        self.assertIn("Database publisher", [request["purpose"] for request in self.preflight()["requests"]])


if __name__ == "__main__":
    unittest.main()
