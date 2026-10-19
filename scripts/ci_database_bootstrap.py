"""Run the existing bootstrap Job test in an isolated namespace on a test cluster.

Requires kubectl, PowerShell 7, Jinja2 and PyYAML. The selected cluster must be
disposable. Credentials, TLS files and database storage exist only in a unique
temporary namespace, which this runner removes in its finally block.
"""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import uuid

from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--image", default="postgis/postgis:16-3.4")
    args = parser.parse_args()
    namespace = "baikor-bootstrap-ci-" + uuid.uuid4().hex[:12]
    kubectl = ["kubectl", "--kubeconfig", str(args.kubeconfig), "--context", args.context]
    created = False

    def run(*command, **kwargs):
        return subprocess.run([*kubectl, *command], check=True, text=True,
                              capture_output=True, timeout=240, **kwargs)

    def apply(resource):
        run("-n", namespace, "apply", "-f", "-", input=yaml.safe_dump(resource))

    try:
        run("create", "namespace", namespace)
        created = True
        for name, username in (("admin", "postgres"), ("owner", "baikor_owner"),
                               ("writer", "baikor_writer"), ("publisher", "baikor_publisher")):
            apply(dict(apiVersion="v1", kind="Secret", metadata={"name": name},
                       stringData={"username": username, "password": secrets.token_urlsafe(32)}))
        apply(dict(apiVersion="v1", kind="ConfigMap", metadata={"name": "baikor-r-database-bootstrap"},
                   data={"bootstrap.sql": (ROOT / "templates/database_bootstrap.sql").read_text()}))
        # The same cached PostGIS image generates a short-lived self-signed server
        # certificate. Require TLS remains enabled in the actual bootstrap template.
        apply(dict(apiVersion="v1", kind="Pod", metadata={"name": "database", "labels": {"app": "database"}},
                   spec=dict(
                       securityContext={"runAsUser": 999, "runAsGroup": 999, "fsGroup": 999},
                       initContainers=[dict(
                           name="tls", image=args.image, imagePullPolicy="IfNotPresent",
                           command=["sh", "-ec", "openssl req -x509 -newkey rsa:2048 -nodes "
                                    "-keyout /tls/server.key -out /tls/server.crt "
                                    "-subj /CN=database -days 1 >/dev/null 2>&1; chmod 600 /tls/server.key"],
                           volumeMounts=[{"name": "tls", "mountPath": "/tls"}],
                       )],
                       containers=[dict(
                           name="postgres", image=args.image, imagePullPolicy="IfNotPresent",
                           args=["postgres", "-c", "ssl=on", "-c", "ssl_cert_file=/tls/server.crt",
                                 "-c", "ssl_key_file=/tls/server.key"],
                           env=[{"name": "POSTGRES_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "admin", "key": "password"}}},
                                {"name": "PGDATA", "value": "/var/lib/postgresql/data/pgdata"}],
                           readinessProbe={"exec": {"command": ["pg_isready", "-h", "127.0.0.1"]},
                                           "periodSeconds": 2, "failureThreshold": 60},
                           volumeMounts=[{"name": "data", "mountPath": "/var/lib/postgresql/data"},
                                         {"name": "tls", "mountPath": "/tls", "readOnly": True}],
                       )],
                       volumes=[{"name": "data", "emptyDir": {}}, {"name": "tls", "emptyDir": {}}],
                   )))
        apply(dict(apiVersion="v1", kind="Service", metadata={"name": "database"},
                   spec={"selector": {"app": "database"}, "ports": [{"port": 5432}]}))
        run("-n", namespace, "wait", "--for=condition=Ready", "pod/database", "--timeout=180s")

        repository, tag = args.image.rsplit(":", 1)
        addon = dict(database=dict(
            host="database", port=5432, name="baikor_ci", ssl_mode="Require", ca_secret="",
            migration_secret="owner", application_secret="writer", publication_secret="publisher",
            bootstrap={"maintenance_database": "postgres", "admin_secret": "admin"},
        ), publication={"enable": True})
        job = Environment(undefined=StrictUndefined).from_string(
            (ROOT / "templates/database_bootstrap_job.yml.j2").read_text()).render(
                inv_addons={"baikor_r": addon},
                baikor_registry_plan={"bootstrap": {"image": repository, "tag": tag, "secret": ""}})
        apply(yaml.safe_load(job))
        run("-n", namespace, "wait", "--for=condition=complete", "job/baikor-r-database-bootstrap", "--timeout=180s")
        with tempfile.TemporaryDirectory(prefix="baikor-ci-kubeconfig-") as directory:
            # Give the existing PowerShell test only the explicitly selected
            # context, without changing the caller's kubeconfig or current context.
            config = Path(directory) / "config"
            config.write_text(run("config", "view", "--minify", "--flatten", "--raw").stdout)
            config.chmod(0o600)
            environment = dict(os.environ, KUBECONFIG=str(config))
            subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "scripts/test_database_bootstrap.ps1"),
                            "-Namespace", namespace, "-DatabasePod", "database"],
                           env=environment, check=True, timeout=360)
    except subprocess.CalledProcessError as error:
        # Diagnostics concern only this synthetic fixture, never an operator's inventory.
        if error.stderr:
            print(error.stderr)
        if created:
            for target in ("pod/database", "job/baikor-r-database-bootstrap"):
                logs = subprocess.run([*kubectl, "-n", namespace, "logs", target, "--all-containers"],
                                      text=True, capture_output=True, timeout=30)
                print(logs.stdout)
        raise
    finally:
        if created:
            run("delete", "namespace", namespace, "--wait=true", "--timeout=120s")


if __name__ == "__main__":
    main()
