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
        cls.polling_budget = task["retries"] * task["delay"]
        rendered_job = environment.from_string(
            (ROOT / "templates/database_bootstrap_job.yml.j2").read_text()).render(
                baikor_registry_plan={"bootstrap": {"image": "postgres", "tag": "fixture", "secret": ""}},
                inv_addons={"baikor_r": {
                    "database": {"host": "database.example", "port": 5432, "name": "baikor_test",
                                 "ssl_mode": "VerifyFull", "ca_secret": "", "migration_secret": "owner",
                                 "application_secret": "writer", "publication_secret": "publisher",
                                 "bootstrap": {"admin_secret": "admin", "maintenance_database": "postgres"}},
                    "publication": {"enable": False},
                }})
        cls.job_deadline = yaml.safe_load(rendered_job)["spec"]["activeDeadlineSeconds"]

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

    def test_cold_image_pull_leaves_time_to_bootstrap_within_bounded_deadline(self):
        # The first Core installation needed 226.581 seconds just to pull the image.
        # Leave another minute for PostgreSQL setup while keeping a ten-minute cap.
        self.assertGreaterEqual(self.job_deadline, 227 + 60)
        self.assertLessEqual(self.job_deadline, 600)

    def test_controller_wait_covers_job_deadline_and_terminal_condition_delay(self):
        self.assertGreaterEqual(self.polling_budget, self.job_deadline + 60)
        self.assertLessEqual(self.polling_budget, 660)

    def test_failed_condition_stops_polling_without_a_failed_pod_count(self):
        for condition_type in ("Failed", "FailureTarget"):
            for pod_counts in ({}, {"active": 1, "failed": 0}):
                with self.subTest(condition=condition_type, pod_counts=pod_counts):
                    self.assertEqual(self.outcome({**pod_counts, "conditions": [{
                        "type": condition_type, "status": "True", "reason": "DeadlineExceeded",
                    }]}), (True, True))

    def test_false_failure_conditions_keep_polling(self):
        self.assertEqual(self.outcome({"conditions": [
            {"type": "Failed", "status": "False"},
            {"type": "FailureTarget", "status": "False"},
            {"type": "Complete", "status": "False"},
        ]}), (False, False))


if __name__ == "__main__":
    unittest.main()
