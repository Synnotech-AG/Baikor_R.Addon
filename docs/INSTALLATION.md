# Manual Secret Creation Fallback

> This is not the production installation guide. Start with the
> [README](../README.md). Production installations should create Secrets through
> the customer's existing Ansible, secret manager or GitOps workflow.

This fallback is intended only for development or a controlled test environment
which has no established Secret provisioning process. It uses `kubectl` to create
the two operator-owned database prerequisites. `kubectl` and Ansible use the same
kubeconfig and Kubernetes API; this is not a second platform integration.

Prepare protected files outside Git. Each username/password file must contain only
its value without a trailing newline. The CA file must contain the trusted public
PEM certificate chain and no private key.

```shell
kubectl --context CONTEXT -n DB_NAMESPACE create secret generic baikor-bootstrap \
  --from-file=username=/secure/baikor/admin.username \
  --from-file=password=/secure/baikor/admin.password

kubectl --context CONTEXT -n DB_NAMESPACE create secret generic baikor-database-ca \
  --from-file=ca.crt=/secure/baikor/database-ca-bundle.pem
```

The commands deliberately create rather than overwrite Secrets. If a Secret
already exists, stop and inspect its ownership instead of deleting or replacing it.
Do not print Secret contents or attach their YAML representation to logs or support
tickets.

Confirm only that the names exist:

```shell
kubectl --context CONTEXT -n DB_NAMESPACE get secret \
  baikor-bootstrap baikor-database-ca
```

Then return to [Configuration](../README.md#configuration) in the production guide.
The inventory names must match the created Secrets. If the database CA is already
trusted by the system, omit `baikor-database-ca` and leave `ca_secret` empty.
