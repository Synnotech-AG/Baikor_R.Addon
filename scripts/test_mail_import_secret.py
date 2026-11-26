"""Test actual native-mail Ansible tasks in a disposable Kubernetes namespace."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import uuid

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import yaml

from deployment.mail_import_key import ensure_key

ROOT = Path(__file__).resolve().parents[1]


def check_concurrent_first_create(api, namespace):
    # Both real reads must return 404 before either deployment can submit its POST.
    barrier = threading.Barrier(2, timeout=15)

    class ConcurrentApi:
        create_namespaced_secret = api.create_namespaced_secret

        def read_namespaced_secret(self, name, namespace):
            try:
                return api.read_namespaced_secret(name, namespace)
            except ApiException as error:
                if error.status == 404:
                    barrier.wait()
                raise

    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = [executor.submit(ensure_key, ConcurrentApi(), namespace, "concurrent-key")
                    for _ in range(2)]
        assert sorted(job.result() for job in attempts) == [False, True], "Expected exactly one creator"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--ansible-playbook", default="ansible-playbook")
    args = parser.parse_args()
    config.load_kube_config(config_file=str(args.kubeconfig), context=args.context)
    api = client.CoreV1Api()
    namespace = "baikor-mail-key-test-" + uuid.uuid4().hex[:12]
    name = "native-mail-key"
    api.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
    try:
        check_concurrent_first_create(api, namespace)
        with tempfile.TemporaryDirectory(prefix="baikor-mail-key-") as directory:
            playbook = Path(directory) / "playbook.yml"
            playbook.write_text(yaml.safe_dump([dict(
                hosts="localhost", connection="local", gather_facts=False,
                vars=dict(k8s_config=str(args.kubeconfig.resolve()), k8s_context=args.context,
                          k8s_namespace=namespace, ansible_python_interpreter=sys.executable,
                          addon_dir=os.path.relpath(ROOT, directory) + "/",
                          inv_addons={"baikor_r": {"mail_imports": {"encryption_secret": name}}}),
                tasks=[{"ansible.builtin.import_tasks": str(ROOT / "tasks/baikor_r/mail_imports.yml")}],
            )]))

            def deploy(expected=0, check=False):
                command = [args.ansible_playbook, "-i", "localhost,", str(playbook)]
                if check:
                    command.append("--check")
                result = subprocess.run(command,
                                        capture_output=True, text=True, check=False, timeout=120)
                if (result.returncode == 0) != (expected == 0):
                    raise AssertionError("Unexpected Ansible result:\n" + result.stdout + result.stderr)

            deploy(check=True)
            assert not api.list_namespaced_secret(namespace, field_selector=f"metadata.name={name}").items
            deploy()
            first = api.read_namespaced_secret(name, namespace)
            key_text = base64.b64decode(first.data["key"], validate=True)
            assert len(base64.b64decode(key_text, validate=True)) == 32, "Expected a 32-byte AES key"
            deploy()
            second = api.read_namespaced_secret(name, namespace)
            assert first.data == second.data and first.metadata.resource_version == second.metadata.resource_version, (
                "Repeated addon deployment changed the encryption Secret"
            )
            # A damaged existing key must be rejected and left untouched.
            api.patch_namespaced_secret(name, namespace, {"data": {"key": base64.b64encode(b"invalid").decode()}})
            deploy(expected=1)
            damaged = api.read_namespaced_secret(name, namespace)
            assert damaged.data["key"] == base64.b64encode(b"invalid").decode(), "Invalid key was overwritten"
        print("Native mail key: concurrent first create and check mode passed; existing keys preserved and damaged keys rejected.")
    finally:
        api.delete_namespace(namespace)


if __name__ == "__main__":
    main()
