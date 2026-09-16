# Baikor_R.Addon

This addon deploys the Baikor_R construction-site management application into an
existing CIVITAS/CORE 1.7.x platform. It uses the platform's existing Keycloak
realm, routing and service portal. Application source code and the Helm chart are
maintained in a separate Baikor_R application repository.

## Features

- Authenticated construction-site management with maps and attachments
- PostgreSQL/PostGIS persistence
- Ingress or Gateway API routing and a CIVITAS/CORE overview card
- Optional GeoServer/Masterportal publication and OAuth-protected import API

## Installation

### Requirements

- Working CIVITAS/CORE 1.7.x Ansible environment and Kubernetes access
- Existing Keycloak tenant realm, DNS and HTTPS configuration
- Operator-managed PostgreSQL server with PostGIS, TLS and persistent storage
- Read access to the registries hosting the Baikor_R
  container image and Helm chart

The addon creates its own database and roles on the supplied PostgreSQL server; it
does not install a database server in production. The tested release combination
is addon **1.7.5** with application/chart **1.7.4** on CIVITAS/CORE **1.7.x**.

### Add the addon to CIVITAS/CORE

Run from the CIVITAS/CORE repository root:

```shell
git submodule add https://github.com/Synnotech-AG/Baikor_R.Addon.git core_platform/addons/baikor_r_addon
```

Commit the submodule pointer in the operator's CIVITAS/CORE repository. For an
existing submodule run:

```shell
git submodule update --init core_platform/addons/baikor_r_addon
```

## Configuration

Add Baikor_R to the existing CIVITAS/CORE inventory without removing other addons:

```yaml
all:
    children:
        controller:
            vars:
                inv_addons:
                    import: true
                    addons:
                        - addons/baikor_r_addon/tasks.yml
                    baikor_r:
                        enable: true
                        subdomain: baikor-r
                        database:
                            namespace: tenant-database-stack
                            host: postgres.tenant-database-stack.svc.cluster.local
                            name: baikor_r
                            ca_secret: baikor-database-ca
                            bootstrap:
                                enable: true
                                admin_secret: baikor-bootstrap
                                generate_credentials: true
                            local_provision:
                                enable: false
```

Replace `namespace` and `host` with real values. The database host name must
match its TLS certificate. All defaults and optional settings are documented in
[`default_inventory.yml`](default_inventory.yml); a complete example is available
in [`examples/customer-inventory.yml`](examples/customer-inventory.yml).

### Required database Secrets

Create these Secrets in `database.namespace` through the existing
Ansible, secret-manager or GitOps workflow:

| Secret               | Keys                   | Purpose                                                                                    |
| -------------------- | ---------------------- | ------------------------------------------------------------------------------------------ |
| `baikor-bootstrap`   | `username`, `password` | PostgreSQL administrator used to create the Baikor_R database, roles and PostGIS extension |
| `baikor-database-ca` | `ca.crt`               | PostgreSQL CA bundle; not required when the CA is already system-trusted                   |

With `generate_credentials: true`, the addon generates missing application and
migration credentials once. It does not rotate existing credentials. Set
`bootstrap.enable: false` only when the customer has already created the database,
PostGIS extension, roles and grants.

Keep database certificate validation enabled. Secret values must not be committed
to this repository or stored in plain inventory. The development-only manual
Secret fallback is described in [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

### Ingress or Gateway API

Ingress is enabled by default. To use Gateway API instead:

```yaml
inv_addons:
    baikor_r:
        enable_ingress: false
        enable_gateway: true
```

### Registries

The application image and Helm chart are pinned in
[`vars/software_references.yml`](vars/software_references.yml) and pulled from
their configured registries. CIVITAS/CORE image mirrors can be inherited; the Helm
chart continues to use its configured package registry. Explicit image mirrors are
configured through `image_registry` and `bootstrap_image_registry` in
`default_inventory.yml`.

## Deploy

Provide the package-registry credentials only to the Ansible process and run the
normal CIVITAS/CORE addon deployment:

```shell
set +x
read -r -p 'Package-registry username: ' BAIKOR_R_PACKAGE_REGISTRY_USERNAME
read -r -s -p 'Package-registry password: ' BAIKOR_R_PACKAGE_REGISTRY_PASSWORD
printf '\n'
export BAIKOR_R_PACKAGE_REGISTRY_USERNAME BAIKOR_R_PACKAGE_REGISTRY_PASSWORD

ansible-playbook -i inventory.yml core_platform/playbook.yml --tags addons

unset BAIKOR_R_PACKAGE_REGISTRY_USERNAME BAIKOR_R_PACKAGE_REGISTRY_PASSWORD
```

The application is available at `https://baikor-r.YOUR_DOMAIN/` and through the
**Baustellenmanagement** card in the CIVITAS/CORE overview.

The addon creates the `baikor-r` client and these roles in the existing tenant
realm; access to the platform can be granted by assigning those roles to users

| Role              | Access                                             |
| ----------------- | -------------------------------------------------- |
| `baikor_viewer`   | Read construction sites                            |
| `baikor_editor`   | Create, edit, import and delete construction sites |
| `baikor_approver` | Approve construction sites                         |
| `baikor_admin`    | Full application access                            |

Assign roles to the intended customer users or groups. Keep
`authentication.assign_platform_admin_roles: false` in production.

## Optional Geoportal Publication

Publication is disabled by default. When enabled, sanitized database views expose
only **Approved** and **Active** construction sites. Contacts, attachments and
metadata remain private; diversion and communication text become public.

GeoServer must be able to reach the Baikor_R database and trust its PostgreSQL CA.
The operator must also approve the public workspace and WMS/WFS access rules.

```yaml
inv_addons:
    baikor_r:
        publication:
            enable: true
            workspace: ds_open_data
            datastore: baikor-r
            masterportal:
                enable: true
                export_directory: /secure/operator/baikor-portal-export
```

The addon creates its GeoServer datastore, feature types and style. It exports a
Masterportal merge tool but does not overwrite the customer's shared portal:

```shell
node /secure/operator/baikor-portal-export/configure-masterportal.cjs \
  /operator/portal/config.json /operator/portal/services.json
```

Review and deploy the resulting portal changes through the customer's existing
portal workflow.

## Optional Import API

The addon exposes an import API but does not install or modify customer-owned
Node-RED flows. Enable an addon-managed machine client only when required:

```yaml
inv_addons:
    baikor_r:
        imports:
            service_account:
                enable: true
                client_id: baikor-r-import
```

Its credentials are stored in the `baikor-r-import-client` Secret in the application
namespace. The client has editor privileges and must be treated accordingly.

After obtaining a client-credentials access token from the existing Keycloak realm,
upload an R-KOM trench export:

```shell
curl --fail-with-body \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --form "file=@/path/to/trenches.zip;type=application/zip" \
  "https://baikor-r.YOUR_DOMAIN/api/construction-sites/imports/trenches"
```

The endpoint accepts an R-KOM SHP/DBF/PRJ ZIP in WGS 84 up to 25 MiB. House
connections are skipped, and duplicate files are rejected while their imported
records still exist.

## Update

Back up the database, pin the new addon commit or release and run the same Ansible
deployment:

```shell
git -C core_platform/addons/baikor_r_addon fetch origin
git -C core_platform/addons/baikor_r_addon checkout NEW_REF
ansible-playbook -i inventory.yml core_platform/playbook.yml --tags addons
```

Breaking inventory changes are documented in the release README. Database backups,
monitoring and credential rotation remain operator responsibilities.

## License

[EUPL-1.2](LICENSE)
