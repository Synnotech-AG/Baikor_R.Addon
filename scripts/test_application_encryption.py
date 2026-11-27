"""Verify key adoption, rollout checks and actual Ansible tasks in a disposable namespace."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import tempfile
import threading
from unittest.mock import Mock
import uuid

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import yaml

from deployment.application_key import DEFAULT, LEGACY, LEGACY_ANNOTATION, KeyErrorMessage, provision, verify, verify_container


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "baikor-r"


def denied(action, reason=None):
    try:
        action()
    except KeyErrorMessage as error:
        if reason and reason not in str(error):
            raise AssertionError(f"Unexpected failure: {error}") from error
        return
    raise AssertionError("Key operation should have failed.")


def add_key(core, ns, name, raw, column="key"):
    field = base64.b64encode(raw).decode("ascii")
    return core.create_namespaced_secret(ns, client.V1Secret(metadata=client.V1ObjectMeta(name=name),
                                         string_data={column: field}, type="Opaque"))


def key_options(generic="", legacy="", old_chart=None):
    return {"inventory": generic, "helm": {}, "oldInventory": legacy, "oldHelm": old_chart or {}}


def previous_deployment(env):
    apps = Mock()
    deployment = Mock()
    deployment.metadata.annotations = {"meta.helm.sh/release-name": RELEASE}
    apps.list_namespaced_deployment.return_value.items = [deployment]
    apps.api_client.sanitize_for_serialization.return_value = {
        "spec": {"template": {"spec": {"containers": [{"name": "baikor-r", "env": env}]}}}}
    return apps


def check_concurrent_creation(core, apps, ns):
    name = "concurrent-key"
    barrier = threading.Barrier(2, timeout=15)
    first_read = threading.local()

    class ConcurrentApi:
        create_namespaced_secret = core.create_namespaced_secret

        def read_namespaced_secret(self, candidate, namespace):
            try:
                return core.read_namespaced_secret(candidate, namespace)
            except ApiException as error:
                if error.status == 404 and candidate == name and not getattr(first_read, "done", False):
                    first_read.done = True
                    barrier.wait()
                raise

    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = [executor.submit(provision, ConcurrentApi(), apps, ns, RELEASE, key_options(name)) for _ in range(2)]
        outcomes = [job.result() for job in jobs]
    assert sorted(row["changed"] for row in outcomes) == [False, True]
    assert outcomes[0]["digest"] == outcomes[1]["digest"]


def check_missing_legacy(core, ns):
    # 0.4.1 accepted a missing optional Secret. Stage only the new key while its
    # ability to read the database is unknown, then repair the old binding.
    legacy_env = [{"name": "MailImports__EncryptionKey", "valueFrom": {"secretKeyRef":
                  {"name": LEGACY[0], "key": LEGACY[1], "optional": True}}}]
    old = previous_deployment(legacy_env)
    candidate = provision(core, old, ns, RELEASE, key_options())
    annotation = {LEGACY_ANNOTATION: candidate["legacyAlias"]}
    assert candidate["legacyAlias"] == "/".join(LEGACY)
    assert candidate["name"] == DEFAULT[0] and candidate["changed"]
    assert not core.list_namespaced_secret(ns, field_selector=f"metadata.name={LEGACY[0]}").items
    image = "example/baikor-r:candidate"
    container = {"name": "baikor-r", "image": image, "readinessProbe": {"httpGet": {"path": "/health/ready/encryption.v1"}},
                 "env": [{"name": "Encryption__Key", "valueFrom": {"secretKeyRef": {"name": DEFAULT[0], "key": DEFAULT[1]}}},
                         {"name": "Encryption__ExpectedKeySha256", "value": candidate["digest"]},
                         {"name": "Encryption__Required", "value": "true"}]}
    spec = {"containers": [container]}
    trial = previous_deployment(container["env"])
    dep = trial.api_client.sanitize_for_serialization.return_value
    dep["metadata"] = {"uid": "deployment", "generation": 1}
    dep["spec"].update(template={"spec": spec, "metadata": {"annotations": annotation}},
                       replicas=1, selector={"matchLabels": {"release": RELEASE}})
    dep["status"] = {"observedGeneration": 1, "replicas": 1, "updatedReplicas": 1}
    check = provision(core, trial, ns, RELEASE, key_options(), check=True)
    assert check["changed"] and check["legacyAlias"] == candidate["legacyAlias"]
    denied(lambda: verify(core, trial, ns, RELEASE, DEFAULT, candidate["digest"], image, 0))
    assert not core.list_namespaced_secret(ns, field_selector=f"metadata.name={LEGACY[0]}").items

    rs, pod = Mock(), Mock()
    rs.metadata.uid = "rs"
    rs.metadata.owner_references = [client.V1OwnerReference(api_version="apps/v1", kind="Deployment", name=RELEASE, uid="deployment", controller=True)]
    pod.metadata.owner_references = [client.V1OwnerReference(api_version="apps/v1", kind="ReplicaSet", name=RELEASE, uid="rs", controller=True)]
    pod.metadata.deletion_timestamp = None
    pod.status.conditions = [client.V1PodCondition(type="Ready", status="True")]
    trial.list_namespaced_replica_set.return_value.items = [rs]
    dep["status"].update(readyReplicas=1, availableReplicas=1)
    api = Mock()
    api.read_namespaced_secret.side_effect = core.read_namespaced_secret
    api.list_namespaced_pod.return_value.items = [pod]
    api.api_client.sanitize_for_serialization.return_value = spec
    # Another release may create the missing legacy Secret concurrently. A different
    # elected legacy value must stop setup and remain untouched.
    original_create = core.create_namespaced_secret

    def competing_create(namespace, body):
        add_key(core, namespace, body.metadata.name, secrets.token_bytes(32))
        return original_create(namespace, body)

    api.create_namespaced_secret.side_effect = competing_create
    denied(lambda: verify(api, trial, ns, RELEASE, DEFAULT, candidate["digest"], image, 0), "changed during provisioning")
    canonical = core.read_namespaced_secret(DEFAULT[0], ns).data
    assert core.read_namespaced_secret(LEGACY[0], ns).data != canonical
    core.delete_namespaced_secret(LEGACY[0], ns)
    api.create_namespaced_secret.side_effect = original_create
    assert verify(api, trial, ns, RELEASE, DEFAULT, candidate["digest"], image, 0)
    assert not verify(api, trial, ns, RELEASE, DEFAULT, candidate["digest"], image, 0)
    assert core.read_namespaced_secret(LEGACY[0], ns).data == canonical
    assert not provision(core, trial, ns, RELEASE, key_options(), check=True)["changed"]
    for name in (DEFAULT[0], LEGACY[0]):
        core.delete_namespaced_secret(name, ns)


def check_runtime_contract():
    ref = ("expected-secret", "key")
    digest = "a" * 64
    image = "example/baikor-r:test"
    container = {"name": "baikor-r", "image": image,
                 "readinessProbe": {"httpGet": {"path": "/health/ready/encryption.v1"}},
                 "env": [{"name": "Encryption__Key", "valueFrom": {"secretKeyRef": {"name": ref[0], "key": ref[1]}}},
                         {"name": "Encryption__Required", "value": "true"},
                         {"name": "Encryption__ExpectedKeySha256", "value": digest}]}
    verify_container({"containers": [container]}, ref, digest, image)
    for mode in ("missing", "wrong-secret", "optional", "wrong-field", "wrong-digest", "old-health", "old-image", "disabled"):
        bad = deepcopy(container)
        if mode == "missing":
            del bad["env"][0]
        elif mode == "wrong-secret":
            bad["env"][0]["valueFrom"]["secretKeyRef"]["name"] = "different-secret"
        elif mode == "optional":
            bad["env"][0]["valueFrom"]["secretKeyRef"]["optional"] = True
        elif mode == "wrong-field":
            bad["env"][0]["valueFrom"]["secretKeyRef"]["key"] = "other"
        elif mode == "wrong-digest":
            bad["env"][2]["value"] = "b" * 64
        elif mode == "old-health":
            bad["readinessProbe"]["httpGet"]["path"] = "/health/ready"
        elif mode == "old-image":
            bad["image"] = "example/baikor-r:old"
        else:
            bad["env"][1]["value"] = "false"
        denied(lambda: verify_container({"containers": [bad]}, ref, digest, image))

    # A matching but stale Deployment must not pass, even when all old pods are healthy.
    dep = {"metadata": {"generation": 7}, "spec": {"template": {"spec": {"containers": [container]}}, "replicas": 2},
           "status": {"observedGeneration": 6, "replicas": 2, "updatedReplicas": 2, "availableReplicas": 2, "readyReplicas": 2}}
    apps = Mock()
    old = Mock()
    old.metadata.annotations = {"meta.helm.sh/release-name": RELEASE}
    apps.list_namespaced_deployment.return_value.items = [old]
    apps.api_client.sanitize_for_serialization.return_value = dep
    denied(lambda: verify(Mock(), apps, "test", RELEASE, ref, digest, image, 0))


def check_operator_fallback(core, apps, ns, args):
    blocked = Mock()
    blocked.read_namespaced_secret.side_effect = core.read_namespaced_secret
    blocked.create_namespaced_secret.side_effect = ApiException(status=403, reason="access denied")
    denied(lambda: provision(blocked, apps, ns, RELEASE, key_options()),
           f"HTTP 403 creating encryption Secret {ns}/{DEFAULT[0]} (field {DEFAULT[1]})")

    section = (ROOT / "README.md").read_text().split("#### Platform-managed encryption Secret", 1)[1]
    snippet = section.split("```bash\n", 1)[1].split("\n```", 1)[0]
    snippet = snippet.replace("'YOUR-CORE-CONTEXT'", shlex.quote(args.context)).replace("'YOUR-BAIKOR-NAMESPACE'", shlex.quote(ns))
    env = {**os.environ, "KUBECONFIG": str(args.kubeconfig.resolve())}
    subprocess.run(["bash", "-c", snippet], check=True, capture_output=True, env=env, timeout=30)
    first = core.read_namespaced_secret(DEFAULT[0], ns)
    text_key = base64.b64decode(first.data[DEFAULT[1]], validate=True)
    raw = base64.b64decode(text_key, validate=True)
    assert len(raw) == 32 and base64.b64encode(raw) == text_key
    assert provision(blocked, apps, ns, RELEASE, key_options())["digest"] == hashlib.sha256(raw).hexdigest()
    second = subprocess.run(["bash", "-c", snippet], capture_output=True, env=env, timeout=30)
    assert second.returncode and b"alreadyexists" in second.stderr.lower().replace(b" ", b"")
    assert core.read_namespaced_secret(DEFAULT[0], ns).metadata.resource_version == first.metadata.resource_version
    core.delete_namespaced_secret(DEFAULT[0], ns)


def setup_checks(core, apps, ns, args):
    with tempfile.TemporaryDirectory(prefix="baikor-key-test-") as directory:
        playbook = Path(directory) / "playbook.yml"
        playbook.write_text(yaml.safe_dump([dict(
            hosts="localhost", connection="local", gather_facts=False,
            vars=dict(k8s_config=str(args.kubeconfig.resolve()), k8s_context=args.context, k8s_namespace=ns,
                      ansible_python_interpreter=sys.executable, addon_dir=os.path.relpath(ROOT, directory) + "/",
                      inv_addons={"baikor_r": {}}, software={"addon_baikor_r": {"baikor_r": {"helm_release_name": RELEASE}}}),
            tasks=[{"ansible.builtin.import_tasks": str(ROOT / "tasks/baikor_r/encryption.yml")}],
        )]))

        def deploy(check=False, should_fail=False):
            command = [args.ansible_playbook, "-i", "localhost,", str(playbook)]
            if check:
                command.append("--check")
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=120)
            if (result.returncode == 0) == should_fail:
                raise AssertionError("Unexpected Ansible result:\n" + result.stdout + result.stderr)
            return result.stdout

        deploy(check=True)
        assert not core.list_namespaced_secret(ns, field_selector=f"metadata.name={DEFAULT[0]}").items
        original = secrets.token_bytes(32)
        add_key(core, ns, LEGACY[0], original)
        deploy()
        first = core.read_namespaced_secret(DEFAULT[0], ns)
        assert base64.b64decode(base64.b64decode(first.data["key"])) == original
        deploy()
        assert core.read_namespaced_secret(DEFAULT[0], ns).metadata.resource_version == first.metadata.resource_version
        assert core.read_namespaced_secret(LEGACY[0], ns).data == first.data
        assert provision(core, apps, ns, RELEASE, key_options())["digest"] == hashlib.sha256(original).hexdigest()

        custom = "already-operator-owned"
        add_key(core, ns, custom, original, "customKey")
        selected = provision(core, apps, ns, RELEASE, key_options(old_chart={"name": custom, "key": "customKey"}))
        assert (selected["name"], selected["key"], selected["changed"]) == (custom, "customKey", False)
        partial = provision(core, apps, ns, RELEASE, key_options(legacy=custom, old_chart={"key": "customKey"}))
        assert partial == selected

        # Only the previous Deployment remembers this operator-owned custom reference.
        previous = previous_deployment([{"name": "MailImports__EncryptionKey",
                                         "valueFrom": {"secretKeyRef": {"name": custom, "key": "customKey"}}}])
        assert provision(core, previous, ns, RELEASE, key_options()) == selected
        destination = provision(core, previous, ns, RELEASE, key_options("new-destination"))
        assert destination["changed"] and destination["digest"] == selected["digest"]

        conflict = add_key(core, ns, "conflicting", secrets.token_bytes(32))
        denied(lambda: provision(core, apps, ns, RELEASE, key_options("conflicting")))
        assert core.read_namespaced_secret("conflicting", ns).data == conflict.data
        # Both explicitly supplied source refs count, even with a valid live binding.
        denied(lambda: provision(core, previous, ns, RELEASE, key_options("new-destination", old_chart={"name": "conflicting"})))
        denied(lambda: provision(core, previous, ns, RELEASE, key_options("new-destination", legacy="conflicting")))
        core.patch_namespaced_secret(custom, ns, {"data": {"other": conflict.data["key"]}})
        denied(lambda: provision(core, previous, ns, RELEASE, key_options("new-destination", old_chart={"name": custom, "key": "other"})))

        # If the original 0.4.2 key disappeared, only its original bytes are acceptable.
        # The remaining legacy key has a different fingerprint from the previous deployment.
        lost = previous_deployment([
            {"name": "Encryption__Key", "valueFrom": {"secretKeyRef": {"name": "lost", "key": "key"}}},
            {"name": "Encryption__ExpectedKeySha256", "value": hashlib.sha256(b"previously configured").hexdigest()}])
        denied(lambda: provision(core, lost, ns, RELEASE, key_options("lost")))
        assert not core.list_namespaced_secret(ns, field_selector="metadata.name=lost").items

        # After uninstalling the release, the retained canonical Secret is still
        # authoritative when inventory names a previously unprovisioned target.
        core.delete_namespaced_secret(LEGACY[0], ns)
        renamed = provision(core, apps, ns, RELEASE, key_options("renamed-without-deployment"))
        assert renamed["changed"] and renamed["digest"] == hashlib.sha256(original).hexdigest()
        denied(lambda: provision(core, apps, ns, RELEASE, key_options("conflicting")))

        core.patch_namespaced_secret(DEFAULT[0], ns, {"data": {"key": base64.b64encode(b"invalid").decode()}})
        assert "Restore its original" in deploy(should_fail=True)
        assert core.read_namespaced_secret(DEFAULT[0], ns).data["key"] == base64.b64encode(b"invalid").decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--ansible-playbook", default="ansible-playbook")
    args = parser.parse_args()
    check_runtime_contract()
    config.load_kube_config(config_file=str(args.kubeconfig), context=args.context)
    core, apps = client.CoreV1Api(), client.AppsV1Api()
    namespace = "baikor-encryption-test-" + uuid.uuid4().hex[:12]
    core.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
    try:
        check_operator_fallback(core, apps, namespace, args)
        check_concurrent_creation(core, apps, namespace)
        check_missing_legacy(core, namespace)
        setup_checks(core, apps, namespace, args)
        print("Application encryption: rollout checks, concurrent creation, check mode, migration, custom references and safe failures passed.")
    finally:
        core.delete_namespace(namespace)


if __name__ == "__main__":
    main()
