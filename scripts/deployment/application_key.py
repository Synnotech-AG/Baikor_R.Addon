"""Provision a retained application key and verify the release using safe metadata only."""
import argparse
import base64
import hashlib
import json
import re
import secrets
import sys
import time

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


DEFAULT = ("baikor-r-encryption", "key")
LEGACY = ("baikor-r-mail-encryption", "key")
KEY_ENV = "Encryption__Key"
OLD_ENV = "MailImports__EncryptionKey"
DIGEST_ENV = "Encryption__ExpectedKeySha256"
LEGACY_ANNOTATION = "baikor-r.civitasconnect.digital/legacy-encryption-secret"


class KeyErrorMessage(Exception):
    """Operator-facing text. Never include a value returned by the Secret API."""


def reference(name, field="key"):
    if not name:
        return None
    if not isinstance(name, str) or len(name) > 253 or not all(
        re.fullmatch(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?", part) and len(part) <= 63 for part in name.split(".")
    ):
        raise KeyErrorMessage("Invalid Kubernetes encryption Secret name.")
    if not isinstance(field, str) or not re.fullmatch(r"[a-zA-Z0-9._-]{1,253}", field):
        raise KeyErrorMessage("Invalid Kubernetes encryption Secret field.")
    return name, field


def key_bytes(core, namespace, ref):
    name, field = ref
    try:
        secret = core.read_namespaced_secret(name, namespace)
    except ApiException as error:
        if error.status == 404:
            return None
        raise
    try:
        encoded = base64.b64decode((secret.data or {})[field], validate=True)
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) != 32:
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise KeyErrorMessage(f"Invalid encryption Secret {namespace}/{name}, field {field}. Restore its original 32-byte key.") from None
    return raw


def ensure_secret(core, namespace, ref, expected):
    existing = key_bytes(core, namespace, ref)
    created = False
    if existing is None:
        raw = expected if expected is not None else secrets.token_bytes(32)
        body = client.V1Secret(metadata=client.V1ObjectMeta(name=ref[0]), type="Opaque",
                               string_data={ref[1]: base64.b64encode(raw).decode("ascii")})
        try:
            core.create_namespaced_secret(namespace, body)
            created = True
        except ApiException as error:
            if error.status != 409:
                raise KeyErrorMessage(f"Kubernetes returned HTTP {error.status} creating encryption Secret "
                                      f"{namespace}/{ref[0]} (field {ref[1]}). Ask a platform administrator to provision "
                                      "the required reference, then rerun the addon. See 'Platform-managed encryption Secret' "
                                      "in the addon README for first keys and recovery of existing key bytes.") from None
        existing = key_bytes(core, namespace, ref)
        if existing is None:
            raise KeyErrorMessage("The encryption Secret disappeared during provisioning. Retry the deployment.")
    if expected is not None and existing != expected:
        raise KeyErrorMessage("The encryption Secret changed during provisioning. Validate the original key before retrying.")
    return existing, created


def deployments(apps, namespace, release):
    items = apps.list_namespaced_deployment(namespace, label_selector="app.kubernetes.io/instance=" + release).items
    return [apps.api_client.sanitize_for_serialization(item) for item in items
            if (item.metadata.annotations or {}).get("meta.helm.sh/release-name") == release]


def app_container(spec):
    return next((c for c in spec["containers"] if c["name"] == "baikor-r"), {})


def binding(container):
    refs = {}
    digest = None
    for env in container.get("env", []):
        if env["name"] in (KEY_ENV, OLD_ENV):
            spec = env.get("valueFrom", {}).get("secretKeyRef", {})
            ref = reference(spec.get("name"), spec.get("key"))
            if not ref:
                raise KeyErrorMessage("An installed encryption key has no Kubernetes Secret reference. Preserve its original bytes in a Secret before upgrading.")
            if env["name"] in refs and ref != refs[env["name"]]:
                raise KeyErrorMessage("The Deployment has conflicting encryption Secret references.")
            refs[env["name"]] = ref
        if env["name"] == DIGEST_ENV and env.get("value"):
            digest = env["value"]
            if not re.fullmatch("[0-9a-fA-F]{64}", digest):
                raise KeyErrorMessage("Invalid encryption fingerprint in the existing Deployment.")
    return refs, digest.lower() if digest else None


def legacy_alias(template):
    value = template.get("metadata", {}).get("annotations", {}).get(LEGACY_ANNOTATION)
    if not value:
        return None
    parts = value.split("/")
    if len(parts) != 2 or not parts[0]:
        raise KeyErrorMessage("Invalid legacy encryption Secret reference in the Deployed pod template.")
    return reference(*parts)


def provision(core, apps, namespace, release, names, check=False):
    old_inventory = reference(names.get("oldInventory"))
    old_helm = None
    if names["oldHelm"]:
        old_helm = reference(names["oldHelm"].get("name", (old_inventory or LEGACY)[0]), names["oldHelm"].get("key", "key"))
    generic = reference(names.get("inventory"))
    if names["helm"]:
        generic = reference(names["helm"].get("name", (generic or DEFAULT)[0]), names["helm"].get("key", "key")) or generic
    previous = deployments(apps, namespace, release)
    if len(previous) > 1:
        raise KeyErrorMessage("Multiple managed Deployments match the Helm release. Check its labels before upgrading.")
    template = previous[0]["spec"]["template"] if previous else {}
    active, digest = binding(app_container(template["spec"])) if template else ({}, None)
    alias = active.get(OLD_ENV) or legacy_alias(template)

    # Prefer an explicitly named new destination. Keep custom legacy destinations stable.
    custom = next((ref for ref in (old_helm, alias, old_inventory) if ref and ref not in (DEFAULT, LEGACY)), None)
    target = generic or active.get(KEY_ENV) or custom or DEFAULT
    if not generic and not active.get(KEY_ENV) and target == alias and key_bytes(core, namespace, alias) is None:
        target = DEFAULT
    related = [target, *active.values(), alias, old_helm]
    # The old inventory default could provision an unused Secret even when a Helm
    # override used a different one. A key-only Helm override refines that field.
    if old_inventory and old_inventory != LEGACY and (not old_helm or old_helm[0] != old_inventory[0]):
        related.append(old_inventory)
    related = list(dict.fromkeys(ref for ref in related if ref))
    fallbacks = [ref for ref in (DEFAULT, LEGACY) if all(other[0] != ref[0] for other in related)]
    values = {raw for ref in related if (raw := key_bytes(core, namespace, ref)) is not None}
    if not active or not values:
        values.update(raw for ref in fallbacks if (raw := key_bytes(core, namespace, ref)) is not None)
    if len(values) > 1:
        raise KeyErrorMessage("Existing application and legacy encryption keys disagree. Restore matching original keys before upgrading.")
    selected = next(iter(values), None)
    if digest and (selected is None or hashlib.sha256(selected).hexdigest() != digest):
        raise KeyErrorMessage("The installed application key has changed or is missing. Restore the key matching the previous Deployment. "
                              "If the first cutover failed readiness, follow the failed-upgrade recovery steps in the addon README.")

    alias = alias if alias != target else None
    if check:
        existing = key_bytes(core, namespace, target)
        changed = existing is None or (alias is not None and key_bytes(core, namespace, alias) is None)
    else:
        existing, changed = ensure_secret(core, namespace, target, selected)
    return {"name": target[0], "key": target[1], "changed": changed,
            "legacyAlias": "/".join(alias) if alias else "", "digest": hashlib.sha256(existing).hexdigest() if existing else ""}


def verify_container(spec, ref, digest, image):
    c = app_container(spec)
    env = {v["name"]: v for v in c.get("env", [])}
    source = env.get(KEY_ENV, {}).get("valueFrom", {}).get("secretKeyRef", {})
    if (source.get("name"), source.get("key")) != ref or source.get("optional", False):
        raise KeyErrorMessage("Baikor does not reference the expected required application encryption Secret. Check the deployed chart, image and Helm overrides.")
    if (env.get("Encryption__Required", {}).get("value", "").lower() != "true"
            or env.get(DIGEST_ENV, {}).get("value") != digest
            or c.get("readinessProbe", {}).get("httpGet", {}).get("path") != "/health/ready/encryption.v1"):
        raise KeyErrorMessage("The application encryption readiness check is missing or was overridden. Check the deployed chart and Helm overrides.")
    if c.get("image") != image:
        raise KeyErrorMessage("The deployed Baikor image differs from the intended release image.")


def verify(core, apps, namespace, release, ref, digest, image, timeout, expected_alias=None):
    deadline = time.monotonic() + timeout
    while True:
        owned = deployments(apps, namespace, release)
        if len(owned) != 1:
            raise KeyErrorMessage("Could not identify exactly one Baikor Deployment for the Helm release.")
        dep = owned[0]
        alias = legacy_alias(dep["spec"]["template"])
        if expected_alias is not None and ("/".join(alias) if alias else "") != expected_alias:
            raise KeyErrorMessage("The chart did not retain the legacy encryption Secret reference for rollback.")
        verify_container(dep["spec"]["template"]["spec"], ref, digest, image)
        desired = dep["spec"].get("replicas", 1)
        if not desired:
            raise KeyErrorMessage("No Baikor replica is enabled. Application encryption could not be verified.")
        status = dep.get("status", {})
        ready = (status.get("observedGeneration") == dep["metadata"]["generation"]
                 and all(status.get(k) == desired for k in ("replicas", "readyReplicas", "updatedReplicas", "availableReplicas")))
        if ready:
            selector = ",".join(f"{k}={v}" for k, v in dep["spec"]["selector"]["matchLabels"].items())
            replicasets = apps.list_namespaced_replica_set(namespace, label_selector=selector).items
            owner_ids = {rs.metadata.uid for rs in replicasets if any(owner.uid == dep["metadata"]["uid"] and owner.controller
                         for owner in rs.metadata.owner_references or [])}
            pods = [p for p in core.list_namespaced_pod(namespace, label_selector=selector).items
                    if not p.metadata.deletion_timestamp and any(owner.uid in owner_ids and owner.controller for owner in p.metadata.owner_references or [])]
            if len(pods) == desired and all(any(c.type == "Ready" and c.status == "True" for c in p.status.conditions or []) for p in pods):
                for pod in pods:
                    verify_container(core.api_client.sanitize_for_serialization(pod.spec), ref, digest, image)
                stored = key_bytes(core, namespace, ref)
                if stored is None or hashlib.sha256(stored).hexdigest() != digest:
                    raise KeyErrorMessage("The encryption Secret changed or disappeared during rollout. Restore its original value.")
                # Restore a missing 0.4.x binding only after all processes have
                # proved that existing encrypted credentials work with these bytes.
                if alias and alias != ref:
                    _, created = ensure_secret(core, namespace, alias, stored)
                    return created
                return False
        if time.monotonic() >= deadline:
            raise KeyErrorMessage(f"Baikor release {namespace}/{release} did not become ready with application encryption. "
                                  f"Check Deployment events and /health/ready/encryption.v1. If a saved password cannot be decrypted, "
                                  f"follow the failed-upgrade recovery in the addon README to restore its original key in "
                                  f"{namespace}/{ref[0]} (field {ref[1]}).")
        time.sleep(min(3, max(0, deadline - time.monotonic())))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("kubeconfig", "context", "namespace", "release"):
        p.add_argument("--" + arg, required=True)
    p.add_argument("--mode", choices=("apply", "check", "verify"), required=True)
    p.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()
    options = json.load(sys.stdin)
    try:
        with config.new_client_from_config(config_file=args.kubeconfig, context=args.context) as connection:
            core, apps = client.CoreV1Api(connection), client.AppsV1Api(connection)
            if args.mode == "verify":
                if verify(core, apps, args.namespace, args.release, reference(options["name"], options["key"]),
                          options["digest"], options["image"], args.timeout, options.get("legacyAlias")):
                    print("Restored missing legacy encryption Secret.")
                print("Application encryption verified on all ready Baikor replicas.")
            else:
                print(json.dumps(provision(core, apps, args.namespace, args.release, options, args.mode == "check")))
    except KeyErrorMessage as error:
        sys.exit(str(error))
    except ApiException as error:
        sys.exit(f"Kubernetes returned HTTP {error.status} while checking Baikor application encryption.")


if __name__ == "__main__":
    main()
