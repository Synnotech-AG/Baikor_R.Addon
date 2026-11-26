"""Create or validate the dedicated Baikor mail encryption key without rotating it."""
import argparse
import base64
import secrets

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


def ensure_key(api, namespace, name, check=False):
    created = False
    try:
        secret = api.read_namespaced_secret(name, namespace)
    except ApiException as missing:
        if missing.status != 404:
            raise
        if check:
            return True
        candidate = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name),
            type="Opaque",
            string_data={"key": base64.b64encode(secrets.token_bytes(32)).decode("ascii")},
        )
        try:
            secret = api.create_namespaced_secret(namespace, candidate)
            created = True
        except ApiException as conflict:
            if conflict.status != 409:
                raise
            # Another deployment created it after the initial read. Adopt its key.
            secret = api.read_namespaced_secret(name, namespace)

    try:
        stored = base64.b64decode((secret.data or {})["key"], validate=True)
        key = base64.b64decode(stored, validate=True)
    except (ValueError, KeyError, TypeError):
        raise ValueError("Mail encryption Secret is invalid. Restore its original key.") from None
    if len(key) != 32:
        raise ValueError("Mail encryption Secret must hold a 32-byte key. Restore its original key.")
    return created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--mode", choices=("apply", "check"), required=True)
    args = parser.parse_args()
    with config.new_client_from_config(config_file=args.kubeconfig, context=args.context) as connection:
        created = ensure_key(client.CoreV1Api(connection), args.namespace, args.name, args.mode == "check")
    print("changed" if created else "unchanged")


if __name__ == "__main__":
    main()
