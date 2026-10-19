"""Evaluate the actual bootstrap wait conditions against Kubernetes Job states."""
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]


class BootstrapWaitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tasks = yaml.safe_load((ROOT / "tasks/baikor_r/database_bootstrap.yml").read_text())
        task = next(task for task in tasks if task.get("register") == "baikor_database_bootstrap_job")
        environment = Environment(undefined=StrictUndefined)
        cls.until = staticmethod(environment.compile_expression(task["until"]))
        cls.failed_when = staticmethod(environment.compile_expression(task["failed_when"]))

    def outcome(self, status):
        variables = {"baikor_database_bootstrap_job": {"resources": [{"status": status}]}}
        return bool(self.until(**variables)), bool(self.failed_when(**variables))

    def test_pending_job_keeps_polling(self):
        for status in ({}, {"active": 1}, {"succeeded": 0, "failed": 0}):
            with self.subTest(status=status):
                self.assertEqual(self.outcome(status), (False, False))

    def test_successful_job_stops_without_error(self):
        self.assertEqual(self.outcome({"succeeded": 1}), (True, False))

    def test_failed_job_stops_polling_and_reports_failure(self):
        self.assertEqual(self.outcome({"failed": 1}), (True, True))

    def test_success_count_does_not_hide_failure(self):
        self.assertEqual(self.outcome({"succeeded": 1, "failed": 1}), (True, True))


if __name__ == "__main__":
    unittest.main()
