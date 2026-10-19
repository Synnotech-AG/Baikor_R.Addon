"""Integration check using actual Ansible tasks and Kubernetes Pod admission.

Requires ansible-playbook, kubernetes.core, Python kubernetes/PyYAML and a test
cluster. Creates uniquely named temporary namespaces; Pods use server dry-run.
"""
import argparse
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import yaml

ROOT = Path(__file__).resolve().parents[1]
LABEL = "pod-security.kubernetes.io/enforce"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--ansible-playbook", default="ansible-playbook")
    args = parser.parse_args()
    config.load_kube_config(config_file=str(args.kubeconfig), context=args.context)
    api = client.CoreV1Api()
    prefix = "baikor-psa-test-" + uuid.uuid4().hex[:12]
    reserved = []

    def reserve(suffix):
        name = prefix + "-" + suffix
        try:
            api.read_namespace(name)
        except ApiException as error:
            if error.status != 404:
                raise
        else:
            raise AssertionError("Test namespace already exists: " + name)
        reserved.append(name)
        return name

    def absent(name):
        try:
            api.read_namespace(name)
        except ApiException as error:
            assert error.status == 404, error
        else:
            raise AssertionError("Unexpected namespace creation: " + name)

    try:
        with tempfile.TemporaryDirectory(prefix=prefix) as directory:
            folder = Path(directory)
            template = folder / "tasks/templates/k8s-namespace.yml"
            template.parent.mkdir(parents=True)
            shutil.copyfile(args.core_root / "core_platform/tasks/templates/k8s-namespace.yml", template)
            playbook = folder / "playbook.yml"
            playbook.write_text(yaml.safe_dump([dict(
                hosts="localhost", connection="local", gather_facts=False,
                tasks=[{"ansible.builtin.include_tasks": str(ROOT / "tasks/baikor_r/namespace.yml")}],
            )]))

            def run(name, create=True, psa=True, succeeds=True, check=False):
                variables = dict(
                    ansible_python_interpreter=sys.executable,
                    k8s_config=str(args.kubeconfig), k8s_context=args.context, k8s_namespace=name,
                    inv_addons={"baikor_r": {"ns_create": create}},
                    inv_k8s={"podSecurityAdmission": {"enable": psa}},
                )
                extra_vars = folder / "vars.yml"
                extra_vars.write_text(yaml.safe_dump(variables))
                command = [args.ansible_playbook, "-i", "localhost,", str(playbook), "-e", "@" + str(extra_vars)]
                if check:
                    command.append("--check")
                result = subprocess.run(command, capture_output=True, text=True, timeout=90)
                assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
                return result.stdout

            managed = reserve("managed")
            run(managed)
            assert api.read_namespace(managed).metadata.labels.get(LABEL) == "restricted", "Managed namespace does not enforce restricted PSA"
            assert "changed=0" in run(managed), "Second namespace run must be idempotent"
            print("PASS: Core namespace creation enforces restricted and is idempotent", flush=True)

            pod = dict(apiVersion="v1", kind="Pod", metadata={"name": "admission-probe"}, spec=dict(
                restartPolicy="Never", securityContext={"runAsNonRoot": True, "runAsUser": 1654, "seccompProfile": {"type": "RuntimeDefault"}},
                containers=[dict(name="probe", image="registry.k8s.io/pause:3.10", securityContext={"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}})],
            ))
            api.create_namespaced_pod(managed, pod, dry_run="All")
            unsafe = copy.deepcopy(pod)
            unsafe["spec"]["containers"][0]["securityContext"]["privileged"] = True
            unsafe["spec"]["containers"][0]["securityContext"]["allowPrivilegeEscalation"] = True
            try:
                api.create_namespaced_pod(managed, unsafe, dry_run="All")
            except ApiException as error:
                assert error.status == 403 and "violates PodSecurity" in error.body and "restricted" in error.body, error
            else:
                raise AssertionError("PSA accepted a privileged Pod")
            assert not api.list_namespaced_pod(managed).items, "Admission probes must not persist Pods"
            print("PASS: compliant Pod accepted; privileged Pod rejected by restricted PSA", flush=True)

            for check in [False, True]:
                disabled = reserve("disabled-" + str(check).lower())
                run(disabled, psa=False, succeeds=False, check=check)
                absent(disabled)

            predicted = reserve("check")
            run(predicted, check=True)
            absent(predicted)
            print("PASS: disabled Core PSA prevents creation; check mode does not create namespaces", flush=True)

            labels = dict(api.read_namespace(managed).metadata.labels)
            run(managed, create=False, psa=False)
            assert api.read_namespace(managed).metadata.labels == labels
            unmanaged = reserve("unmanaged")
            api.create_namespace(dict(apiVersion="v1", kind="Namespace", metadata={"name": unmanaged, "labels": {"operator": "preserve"}}))
            original = dict(api.read_namespace(unmanaged).metadata.labels)
            for check in [False, True]:
                run(unmanaged, create=False, succeeds=False, check=check)
                assert api.read_namespace(unmanaged).metadata.labels == original
            missing = reserve("missing")
            run(missing, create=False, succeeds=False)
            absent(missing)
            run(unmanaged)
            labels = api.read_namespace(unmanaged).metadata.labels
            assert labels[LABEL] == "restricted" and labels["operator"] == "preserve"
            print("PASS: operator-owned namespaces verified without mutation; managed existing namespace upgraded", flush=True)
    finally:
        for name in reserved:
            assert name.startswith(prefix + "-")
            try:
                api.delete_namespace(name)
            except ApiException as error:
                if error.status != 404:
                    raise


if __name__ == "__main__":
    main()
