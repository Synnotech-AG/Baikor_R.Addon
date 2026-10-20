# Baikor_R.Addon

This addon deploys the Baikor_R construction-site management application into an
existing CIVITAS/CORE platform. It uses the platform's existing Keycloak
realm and routing. Application source code and the Helm chart are maintained in a
separate [Baikor_R application repository](https://github.com/Synnotech-AG/Baikor_R).

The [review status](docs/REVIEW_STATUS.md) records implemented findings, verification
and the remaining operator/publication decisions.

## Features

- Authenticated construction-site management with maps and attachments
- PostgreSQL/PostGIS persistence
- Ingress or Gateway API routing
- Optional GeoServer/Masterportal publication and OAuth-protected import API

## Installation

### Requirements

- Working CIVITAS/CORE 1.6.0 or 1.7.x Ansible environment and Kubernetes access;
  Core 1.6.0 requires `enable_gateway: false`
- Existing Keycloak tenant realm, DNS and HTTPS configuration
- Operator-managed PostgreSQL server with PostGIS, TLS and persistent storage
- Access to the configured container-image and OCI Helm-chart sources; verify
  artifact availability as described under [Registries](#registries)

The addon creates its own database and roles on the supplied PostgreSQL server; it
does not install a database server in production. This addon revision pins
application/chart **1.7.7** on GHCR. Application versions and Core versions are
independent. Core 1.6.0 deployment evidence is recorded in the
[deployment review](docs/core-1.6.0-deployment-review.md).
MDH remains on Core 1.6 with `enable_gateway: false`; the requested local
compatibility test is complete. The report records the local platform adjustments
and test boundaries; a separate 1.6 branch is not required.

**Release pairing:** Addon **1.7.8** uses application/chart **1.7.7**. Both source
repositories and both GHCR packages are public. Anonymous Docker and Helm
downloads were verified on **2026-10-20**. Do not deploy this revision with the
older 1.7.6 application image or confuse it with the historical addon `1.7.7` tag.
The [review status](docs/REVIEW_STATUS.md) records GitHub release completion and
runtime acceptance. The [October 20 runtime review](docs/runtime-review-2026-10-20.md)
records the direct public-release deployment, cold resets and final local-profile
restoration. The [October 19 runtime review](docs/runtime-review-2026-10-19.md)
preserves the earlier authenticated-bundle deployment and cold-restart evidence.

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
                inv_k8s:
                    podSecurityAdmission:
                        enable: true
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

`database.namespace` is freely selectable: choose an existing namespace for the
database credential/CA Secrets and bootstrap jobs. It does not have to contain
the PostgreSQL server or equal the application namespace. `database.host` can
point to the MDH-managed PostgreSQL service in another namespace or to an external
server; it must be reachable from the application and bootstrap jobs and match
its TLS certificate. All defaults and optional settings are documented in
[`default_inventory.yml`](default_inventory.yml); a complete example is available
in [`examples/customer-inventory.yml`](examples/customer-inventory.yml).

### Namespace security

The addon creates or updates its application namespace through Core's
`tasks/templates/k8s-namespace.yml`. With `ns_create: true`, it requires
`inv_k8s.podSecurityAdmission.enable: true` and verifies that the namespace has
`pod-security.kubernetes.io/enforce: restricted` before deploying workloads.
This is a Core-wide inventory setting; other Core namespace tasks also use it.

With `ns_create: false`, the operator must provide an existing namespace with
that label. The addon verifies it without modifying the namespace. During
Ansible check mode, managed namespace changes are only simulated; the observed
label is verified on the actual deployment. Database bootstrap jobs run in
`database.namespace`, whose security policy remains operator-managed.

### Required database Secrets

Create these Secrets in `database.namespace` through the existing
Ansible, secret-manager or GitOps workflow:

| Secret               | Keys                   | Purpose                                                                                    |
| -------------------- | ---------------------- | ------------------------------------------------------------------------------------------ |
| `baikor-bootstrap`   | `username`, `password` | PostgreSQL administrator used to create the Baikor_R database, roles and PostGIS extension |
| `baikor-database-ca` | `ca.crt`               | PostgreSQL CA bundle; not required when the CA is already system-trusted                   |

With `generate_credentials: true`, the addon generates missing application and
migration credentials once. It does not rotate existing credentials. MDH supplies
the PostgreSQL server; the first addon deployment creates the dedicated database,
PostGIS extension, schema, logins and grants on that server.

Keep database certificate validation enabled. Secret values must not be committed
to this repository or stored in plain inventory. The development-only manual
Secret fallback is described in [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

### First deployment: bootstrap administrator

For the operations in `templates/database_bootstrap.sql`, the initial login needs:

- `LOGIN` and permission to connect to `bootstrap.maintenance_database`
  (normally `postgres`) and the new Baikor_R database over the configured TLS path.
- `CREATEROLE` to create missing owner, writer and optional publisher logins.
- `CREATEDB` and permission to assign the new database to the owner role.
- Permission to install PostGIS and to create the `baikor` schema for its owner,
  grant access, and alter that owner's default privileges.

On standard PostgreSQL/PostGIS, this complete first bootstrap requires a temporary
superuser login because enabling PostGIS requires elevated extension privileges;
`CREATEDB` and `CREATEROLE` alone are insufficient. Assigning ownership to another
role also requires the appropriate membership/`SET ROLE` authority. See the
[PostGIS setup guide](https://postgis.net/documentation/getting_started/) and
[PostgreSQL ownership requirements](https://www.postgresql.org/docs/15/sql-createdatabase.html).

MDH may instead provide a supported extension-installation capability or a
default database template (`template1`) that already contains PostGIS, with the
remaining creation and owner-role permissions. Agree that provisioning model with the database operator;
the addon does not grant server-level privileges to its owner or runtime logins.

### After first deployment: owner login for normal operation

After a successful initial deployment, keep the existing database and credential
Secrets and switch the bootstrap connection to the same login used for migrations:

```yaml
inv_addons:
    baikor_r:
        database:
            application_secret: baikor-writer
            migration_secret: baikor-owner
            bootstrap:
                enable: true
                admin_secret: baikor-owner
                maintenance_database: baikor_r # must match database.name
                generate_credentials: false
```

`admin_secret` is the existing configuration key for the bootstrap connection; in
this mode it references the owner Secret. A separate Secret containing that same
owner login is also supported. Subsequent deployments no longer read or use the
initial administrator Secret. Retire any dedicated temporary administrator login
and Secret through MDH's credential-management process.

The owner needs `LOGIN`, database connection access, and ownership of the Baikor_R
database, `baikor` schema and migration-created objects. It needs no `SUPERUSER`,
`CREATEDB`, `CREATEROLE` or `BYPASSRLS`. Keep the writer and optional publication
login separate: the application continues to use its writer credential, and only
deployment/migration jobs use the owner.

Keep `bootstrap.enable: true` so owner jobs reconcile grants before and after
migrations, including publication views recreated by an upgrade. Existing roles
and passwords remain unchanged. New roles (for example when enabling publication
later), a missing database or a missing PostGIS extension still require operator
provisioning or a deliberate first-bootstrap run with suitable credentials.

`bootstrap.enable: false` is reserved for fully operator-managed database objects
and grants; the operator must then also reconcile grants after migrations.

### Ingress or Gateway API

Ingress is enabled by default. To use Gateway API instead:

```yaml
inv_addons:
    baikor_r:
        enable_ingress: false
        enable_gateway: true
```

### Application environment and Helm overrides

The addon maps the Core `ENVIRONMENT` value to ASP.NET's canonical names:

| Core value (case-insensitive) | ASP.NET environment |
| --- | --- |
| `dev`, `development`, `local` | `Development` |
| `tst`, `test`, `testing`, `stg`, `stage`, `staging`, `qa` | `Staging` |
| Production names, empty values and unrecognized values | `Production` |

Authentication remains explicitly enabled by the addon in every environment.
Use `inv_addons.baikor_r.helm_values` for deliberate chart overrides, for example:

```yaml
inv_addons:
    baikor_r:
        helm_values:
            aspnetCore:
                environment: Staging
            migrations:
                resources:
                    requests:
                        cpu: 100m
                        memory: 256Mi
                    limits:
                        cpu: 1000m
                        memory: 512Mi
```

The chart sets requests and limits separately for the application and migration
Job. An optional `networkPolicy` restricts application traffic when explicitly
enabled; configure its rules for the operator's ingress, DNS, database and
Keycloak paths. See the application's
[Helm security guide](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/HELM_SECURITY.md)
for defaults, examples and migration-Job coverage.

### Registries

The application image and Helm chart are pinned in
[`vars/software_references.yml`](vars/software_references.yml):

- Image: `ghcr.io/synnotech-ag/baikor-r:1.7.7`.
- Chart: `oci://ghcr.io/synnotech-ag/baikor-r-chart`, version `1.7.7`.

Both Baikor packages are published through the application's
[Release workflow](https://github.com/Synnotech-AG/Baikor_R/actions/workflows/release.yml).
The existing packages are public, including future versions published under
these package names; no registry login is required to download them.
The workflow verifies downloads without registry credentials before creating
the release. Operators must permit GHCR downloads or mirror the artifacts.
The PostgreSQL bootstrap client remains a separately pinned Docker Hub image.
CIVITAS/CORE image mirrors can still be inherited. Explicit image mirrors are configured through
`image_registry` and `bootstrap_image_registry` in `default_inventory.yml`.

When adopting a new application release, update `helm_chart_version` and the
application `tag` together in `vars/software_references.yml`, run addon CI, and
publish the addon revision. Operators explicitly update their addon revision;
an application release never silently upgrades a customer installation.

## Deploy

Before deployment, verify that the selected chart and application image can be
retrieved through the operator's configured artifact sources. The local-chart and
local-image test does not verify those distribution paths. Once access is
confirmed, run the normal CIVITAS/CORE addon deployment:

```shell
ansible-playbook -i inventory.yml core_platform/playbook.yml --tags addons
```

The application is available at `https://baikor-r.YOUR_DOMAIN/`.

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
The browser client uses `fullScopeAllowed: false` and explicit scopes for these
four human roles, so unrelated realm roles are not automatically included.

## Optional Geoportal Publication

Publication is disabled by default. When enabled, sanitized database views expose
only **Approved** and **Active** construction sites. Contacts, attachments and
metadata remain private; diversion and communication text become public.

Before setting `publication.enable: true`, the operator must obtain and record
both **business approval** from the responsible data owner and a **privacy review
of the published free-text fields**. Review representative titles, area names,
diversion and communication text for personal data, internal information and
content that is not approved for unrestricted public access. Removing structured
contact fields does not anonymize text entered by users. Record the approver,
date, reviewed scope and any required editorial rules; repeat the review when
public fields or their intended use change. A successful technical test does
not constitute either approval. Keep publication disabled until both are complete.

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

### Existing JDBC datasource (JNDI)

Set `publication.jndi_reference: java:comp/env/jdbc/baikor` to use an existing
operator-managed GeoServer datasource. The default is empty (direct PostGIS).
The addon then sends only `dbtype: postgis`, `jndiReferenceName` and `schema: baikor`
as connection parameters for both datastore creation and updates. It still reads
the publisher Secret and reconciles its restricted database grants.

Core 1.6.0's GeoServer 2.28.0 / GeoTools 34.0 has
[GEOT-7625](https://github.com/geotools/geotools/commit/5ed80fe90ae1995cf04b14048fbb9ae5c35f926a):
the direct datastore passes the SSL enum name incorrectly to PostgreSQL JDBC.
JNDI avoids that URL construction without changing the shared GeoServer image.
Before enabling this mode, the operator must provision the datasource through
Core's GeoServer JNDI configuration, using the Baikor database and publisher login.
Its JDBC URL must include `sslmode=verify-full`, a certificate-matching hostname,
and `sslrootcert` pointing to a readable mounted PostgreSQL CA bundle (or an
equivalent verified CA setup). The addon does not install the datasource or CA,
and `database.ca_secret` does not automatically mount that CA into GeoServer.
The preflight validates the reference's format; datasource availability and TLS
are verified when GeoServer opens the published feature types.

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
namespace. The client receives only `baikor_importer`: it may import construction
sites, but cannot read the workspace or edit, approve or delete records. On an
upgrade, the addon removes its former editor role and editor token scope before
granting the importer role. Keep this addon revision paired with application
1.7.7 or later; older application images do not recognize the importer role.
Already-issued editor tokens retain their privileges until their existing expiry;
obtain a fresh client-credentials token after the upgrade. The addon removes its
known legacy editor grant, while other manually configured roles remain the
operator's responsibility.

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

See the [OpenAPI contract and integration guide](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/openapi/README.md)
for request fields, responses, examples and authentication details.

## Update

Back up the database, pin the new addon commit or release and run the same Ansible
deployment:

```shell
git -C core_platform/addons/baikor_r_addon fetch origin
git -C core_platform/addons/baikor_r_addon checkout NEW_REF
ansible-playbook -i inventory.yml core_platform/playbook.yml --tags addons
```

Changes awaiting publication are recorded in [CHANGELOG.md](CHANGELOG.md).
Released changes are documented in the
[GitHub release notes](https://github.com/Synnotech-AG/Baikor_R.Addon/releases). Database backups,
monitoring and credential rotation remain operator responsibilities.

## Automated validation

The [Validate workflow](.github/workflows/validate.yml) runs on pushes and pull
requests. It covers Ansible lint, registry and preflight unit tests, GeoServer
templates, operator ownership, Node-RED examples, Npgsql connection strings,
database-owner privileges, namespace Pod Security Admission, the real database
bootstrap Job and actual Keycloak provisioning/legacy importer upgrades.

The database and Kubernetes checks create disposable PostGIS containers and a
dedicated k3d cluster with synthetic credentials. They do not need an operator's
inventory, cluster credentials or existing database. The cluster is removed
after the job, including when a test fails. The application repository separately
tests real Keycloak logins, role permissions and persistence in its own isolated
environment before an application release can be published.

## License

[EUPL-1.2](LICENSE)
