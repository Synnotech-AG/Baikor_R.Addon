# Core 1.6.0 deployment review

**Follow-up, 2026-10-20:** Both source repositories and the 1.7.7 image/chart
packages are now public; anonymous Docker and Helm downloads were verified.
MDH remains on Core 1.6 with `enable_gateway: false`. The requested local
compatibility test is complete, with the platform deviations below retained as
its evidence boundary. See the [current review status](REVIEW_STATUS.md) for
release completion and later acceptance tests. The dated findings below describe
their original test state and are not the current release checklist.

**Follow-up, 2026-10-19:** The October 16 baseline evidence and findings below are
historical. The application source is now public under EUPL-1.2. Current source
configures GHCR for application/chart publication and includes the C3 CI test
coverage in the application and addon workflows. Actual hosted publication is
still pending; these source changes do not establish a successful hosted release
or alter the recorded local runtime evidence.
The [current review status](REVIEW_STATUS.md) tracks the subsequent 1.7.7 fixes
and remaining operator decisions separately from this baseline.

Review date: 2026-10-16. **Status: local runtime validation passed for first
installation, owner transition and repeat deployment. The 77 end-to-end checks
passed after initial installation and again after the repeat.**
This document records the deployment design, current test boundaries and proposed
improvements. The runtime evidence is for the patched local Core 1.6.0 setup below;
it does not establish unmodified Core 1.6.0 or exact MDH environment compatibility.
Access to the configured public Baikor chart and image **failed** and remains a
distribution blocker for deployment through those default sources.

This review records the baseline before enabling Geoportal publication. The
subsequent [construction-site and Geoportal test](core-1.6.0-geoportal-test.md)
documents the locally enabled publication, additional operator configuration,
test records and findings from the complete publication path.

## Test environment and limits

| Area | Current scope and limitation |
| --- | --- |
| Core | Based on the exact `v1.6.0` release. The fresh installation required the narrow upstream Keycloak fix from `8b6d335fb881b323c79b7c5bdec2cde2b1c78c0c`; the resulting test is a **patched Core 1.6.0 test**. |
| Keycloak deviation | The patch removes 60 lines that delete piveau-hub-repo default resources, policies and permissions. It changes `core_platform/tasks/access/keycloak/idm-config/keycloak_5_clients.yml`. The incomplete realm in the new test environment was reset before retrying. This is the only Core source patch; image selection changes use configuration overrides. The rest of that later Core commit history was not adopted. |
| Kubernetes | Local Kubernetes `1.35.4`. The MDH Kubernetes version and admission configuration have not been established; this is not an exact MDH cluster replica. |
| Controller toolchain | ansible-core `2.18.6`, Python `3.12.3`, Jinja `3.1.6`, Helm `/usr/local/bin/helm` `3.20.0`. The helper explicitly sets `ANSIBLE_CONFIG`, collection paths and executable path. `/root/.cache/baikor-core160-collections` has first priority and supplies `kubernetes.core 5.2.0`; a venv installation of `5.3.0` has lower priority. Ansible `2.20` encountered Core 1.6 templating incompatibility during initial setup. |
| Routing | `enable_gateway: false`; ingress-nginx chart `4.15.1` with controller `1.15.1` is used, not Traefik. Gateway API resources are absent in the test cluster. |
| Certificates | cert-manager `1.14.4`. |
| Core image paths | Original GitLab image paths returned `403`. Local inventory overrides select the official moved project prefix `civitas-connect/civitas-core/civitas-core-v1/` instead of the original `civitas-connect/civitas-core/` prefix. This is another deployment deviation from unmodified Core 1.6.0 defaults. |
| Portal image versions | Geoportal and its backend retain `v1.6.0`. The service portal is pinned through software overrides to official `2.0.0@sha256:9253514e3849c34b342887087911719ecde9b7a6378fc49cebd2f39ce33fb95d`; the Deployment uses that image. It was built on `2026-04-20`, after Core 1.6.0, and therefore is not an exact historical image replica. |
| Baikor packages | Clean local chart at application repository commit `4ef23165e847c67ddc2a3f6a8ca84940c179ee23`; chart/appVersion `1.7.5`. Local image `baikor-r:account-tests-20261008-fixed`, built `2026-10-08T11:24:59.355202146Z`, manifest digest `sha256:1eefb667943c8261990296702bfb4371519d640ae2b3993e185dcf61359cd7fe`, config/runtime image ID `sha256:f6733a1188d589650b96e99060024a33cea35e8d620b780d82e37004b4a07855`. The image has no source-revision label; its correspondence to the current source commit cannot be proven. Anonymous access to the configured published artifacts failed. |
| MDH database simulation | Operator-side preparation created restricted namespace `mdh-baikor-access` for the bootstrap administrator Secret and CA. The existing PostgreSQL server was configured with `central-db-tls`; both database Pods rolled and became ready. `baikor_r` did not exist immediately before the addon bootstrap (matching database count: `0`). |
| Local DNS | The WSL controller has `127.0.0.1 api-dashboard.civitas.test` in `/etc/hosts`. Adding that Windows hosts entry requires administrator access and was not performed. Baikor and the other required hosts were already mapped; Core controller tests run from WSL. |
| Previous environment | The previous local cluster is retained and stopped: `0/1` server and `0/2` agents running. The new cluster has `1/1` server and `2/2` agents running; current context is `k3d-civitas-local-160`. The previous cluster's data is not the fresh Core 1.6 test dataset. |
| Current runtime verdict | Selected patched Core platform, first Baikor installation, bootstrap-admin to owner transition and identical owner-mode repeat passed. First-install recap: `ok=90 changed=14 unreachable=0 failed=0 skipped=23`; each owner run: `ok=87 changed=5 unreachable=0 failed=0 skipped=24`. All 77 end-to-end checks passed after first installation and after the repeat, with zero failures and disposable-account cleanup. Data, credentials and persistent keys survived both owner upgrades. Publication and Masterportal export are disabled in this test profile. |

The upstream patch can be inspected in [Core commit 8b6d335f](https://gitlab.com/civitas-connect/civitas-core/civitas-core/-/commit/8b6d335fb881b323c79b7c5bdec2cde2b1c78c0c).
The first-install failure is a Core provisioning finding. It does not by itself
show that the Baikor addon cannot run against an already provisioned MDH Core 1.6.
After the backport, the Keycloak configuration was checked for `Catalogue Resource`,
`Operator Policy`, `Operator Permissions` and six authorization scopes; no
`Default Resource` remained. This verifies the affected Core authorization
configuration; the separate Baikor end-to-end results are recorded below.

The original mutable service-portal `latest` tag exposed a concrete compatibility
regression: its current image, built on `2026-10-07`, belongs to the 3.0 generation
and listens on port `8080`. Core 1.6 expects port `80`, producing HTTP `502` even
while the Pod reports ready. The selected official `2.0.0` image listens on port
`80`, verified in its Docker configuration, nginx configuration and source. No
Core container/service port patch was applied. The
[official source comparison](https://gitlab.com/civitas-connect/civitas-core/civitas-core-v1/civitas-core-portal/-/compare/08ed93ababc30472793b9c9366b45d767caddf27...2.0.0)
shows only CI and package-file differences from the reference source revision,
with no application, Docker or nginx changes. That supports the selected image's
compatibility without establishing byte-for-byte historical parity. Both the
temporary deployment configuration and durable software overrides carry the pin.

The full base-platform run completed with Ansible recap `ok=493`, `changed=42`,
`failed=0`, `unreachable=0`, `skipped=326`, including a second successful Keycloak
configuration pass. All selected Core components were ready: PostgreSQL 15,
Keycloak `26.5.6`, service portal `2.0.0`, Prometheus/Grafana/Loki/Alloy, APISIX
`3.13`, GeoServer `2.28.0`, portal backend and Masterportal `v1.6.0`, and pgAdmin
`9.13`. This describes the selected local platform profile, not every optional
Core component.

pgAdmin's first cold start exceeded its 180-second startup-probe allowance and
restarted once. There was no OOM event; it subsequently became ready and returned
HTTP `200`. The sudo/Postfix warning was nonfatal, and no fix was applied. A future
operator configuration could allow up to 600 seconds for slow cold starts; this
is a platform test-environment improvement, not a Baikor addon issue.

## Deployment responsibilities

The operator inventory selects the namespace, database access, image sources and
optional integrations. The addon converts those choices into platform resources
and [Helm values](../templates/baikor_r_values.yml#L1). The application chart owns
the workload definitions. These layers have different responsibilities; keeping
the chart is useful even when the Core addon supplies most values.

The current [deployment sequence](../tasks/baikor_r.yml#L8) is:

1. Resolve image sources and run the read-only configuration/Secret preflight.
2. Create or verify the application namespace through the Core template and
   require `pod-security.kubernetes.io/enforce=restricted`.
3. Optionally provision a local development database, prepare image access and
   generate missing database credentials when explicitly configured.
4. Bootstrap the database and grants; create application/migration connection
   Secrets and configure Keycloak, certificates and routing.
5. Invoke the Core Helm wrapper. The chart's pre-install/pre-upgrade Job runs
   migrations; Helm applies the application workload and persistent key volume.
6. Run database bootstrap again to reconcile publication grants, then configure
   optional GeoServer publication and export the operator's Masterportal helper.

The explicit [addon security contexts](../templates/baikor_r_values.yml#L46) and
the chart's defaults should remain. They express the Core integration requirement
and safe defaults for independent chart users. The namespace assertion provides
a separate enforcement check. Likewise, keep the preflight separate from writes
and keep the owner, runtime writer and publication accounts separate.

## Prioritized improvements

### 1. Use one deterministic Helm installation path

**Evidence:** The [OCI path](../tasks/baikor_r.yml#L48) and
[local-chart path](../tasks/baikor_r.yml#L65) duplicate the wrapper invocation.
The former supplies the database revision; the latter supplies
[`local-rollout: now(...)`](../tasks/baikor_r.yml#L73), forcing a new migration and
workload rollout on every execution, even when configuration is unchanged.

**Proposal:** Resolve chart location/version once and share the values, revision
annotations and wrapper invocation. Use an explicit development rollout token or
a stable chart-content revision when local changes need a forced upgrade. Preserve
version pinning for OCI packages. Verify that a second identical deployment keeps
the Deployment generation and application Pod UID unchanged.

**Benefit/tradeoff:** Fewer branches and representative local tests; developers
must deliberately request a rollout when changing mutable local image content.
This is an optional addon improvement, not yet a proven Core 1.6 compatibility fix.

### 2. Make workload readiness part of deployment success

**Evidence:** The [original Core 1.6 Helm wrapper](https://gitlab.com/civitas-connect/civitas-core/civitas-core/-/blob/v1.6.0/core_platform/tasks/templates/k8s-helm.yml#L56)
does not configure `wait`. The addon moves directly from Helm to
[grant reconciliation](../tasks/baikor_r.yml#L80). The chart has a readiness probe
at `baikor_r/deploy/helm/baikor-r/templates/deployment.yaml:94`, but no addon task
waits for the new Deployment generation to become available.

**Proposal:** After Helm, wait for the observed Deployment generation and expected
available replicas; report useful workload failure conditions. For the integration
test, also verify the external HTTPS readiness endpoint. Use bounded timeouts.

**Benefit/tradeoff:** Image pull, PSA, volume and runtime configuration failures
cannot be mistaken for deployment success. A failed rollout takes longer to report
than a manifest submission, so timeout and diagnostic messages need to be explicit.

### 3. Separate initial database setup from recurring grant reconciliation

**Evidence:** The same [bootstrap tasks](../tasks/baikor_r/database_bootstrap.yml#L54)
delete and recreate a Job both [before Helm](../tasks/baikor_r.yml#L30) and
[after Helm](../tasks/baikor_r.yml#L80). The second run also occurs when publication
is disabled. Writer permissions for future owner-created tables and sequences are
already covered by [default privileges](../templates/database_bootstrap.sql#L43).
Publication grants must be restored when migrations recreate the public views.

**Proposal:** At minimum, skip the second run when publication is disabled.
Longer term, distinguish initial role/database/extension creation from targeted
owner grant reconciliation after migrations. Keep the latter when publication
is enabled and preserve the fail-closed publication checks.

**Current A2 changes:** [Owner operation](../README.md#after-first-deployment-owner-login-for-normal-operation)
is now documented, and [preflight](../scripts/deployment/preflight.py#L28) permits
the bootstrap connection to reuse the owner login without permitting shared
writer/publisher logins. That addresses the account transition; it does not yet
remove the duplicated Job runs.

**Benefit/tradeoff:** Less work per deployment and less need for administrator
credentials. Missing roles, database or PostGIS still require initial provisioning;
the owner mode must not silently acquire server-level privileges.

### 4. Reconcile secret rotation with one configuration revision

**Evidence:** [Database Secret resource versions](../tasks/baikor_r/database.yml#L137)
trigger OCI-path rollouts. The [Keycloak client Secret](../tasks/baikor_r/keycloak.yml#L120)
is also updated, but its version does not participate in that annotation. A rotated
client secret can therefore leave existing Pods with the previous environment value.

**Proposal:** Share a configuration revision between chart paths that includes the
database and Keycloak Secret revisions, and relevant CA configuration where a restart
is required. Do not expose credentials in annotations or logs. Test rotation with
an existing installation as well as the unchanged repeat-deployment case.

**Benefit/tradeoff:** Rotation takes effect predictably. Resource-version changes
caused solely by metadata may produce unnecessary rollouts; choose the revision
inputs deliberately rather than using a timestamp.

### 5. Resolve the chart before making platform changes

**Evidence:** [Preflight](../tasks/baikor_r/preflight.yml#L1) validates configuration
and referenced Secrets. The actual chart access occurs much later at
[Helm installation](../tasks/baikor_r.yml#L48), after database and Keycloak writes.
The earlier local deployment encountered an OCI `401 Unauthorized`; the local-chart
fallback leaves the public package path unverified.

**Proposal:** Read/resolve the selected chart and version with the deployment's
actual Helm authentication before the first write. Keep chart authentication on
the controller distinct from image-pull authentication in Kubernetes. Report the
resolved chart and application version in deployment evidence.

**Benefit/tradeoff:** Package-access failures occur early. This adds one registry
interaction, which can be satisfied by an explicit local artifact in offline tests.

### 6. Make reset and multiple-instance operation explicit

Two smaller changes would simplify operations:

- The chart's `baikor_r/deploy/helm/baikor-r/templates/data-protection-pvc.yaml:4`
  offers neither an existing-claim option nor a retention option. Add an intentional
  storage lifecycle and document how an installation reuses the preserved key
  volume. Verify reset without losing the Data Protection keys. A retention
  annotation alone does not define how a later release adopts the volume.
- [Bootstrap Job and ConfigMap names](../tasks/baikor_r/database_bootstrap.yml#L50)
  are fixed to `baikor-r-database-bootstrap`. Two installations using different
  databases in the same freely selected database namespace would share and delete
  the same Job. Derive these names from an instance identifier or database name,
  with Kubernetes name-length handling, if that deployment model is supported.

## Core 1.6 wrapper boundaries

The original Core 1.6 namespace template already implements `restricted`; no
addon-specific substitute namespace template is needed.

The original Helm wrapper does not consume `helm_timeout`, `helm_post_renderer` or
`helm_environment`. In particular, the addon's
[`helm_timeout: 10m`](../tasks/baikor_r.yml#L75) is ineffective on that version.
Do not treat these settings as tested capabilities of Core 1.6.

The [local-chart task](https://gitlab.com/civitas-connect/civitas-core/civitas-core/-/blob/v1.6.0/core_platform/tasks/templates/k8s-helm.yml#L95)
uses `check_mode: no` and lacks the other branches' `not ansible_check_mode`
condition. Running the entire addon with `--check` therefore does not guarantee a
write-free operation. Prefer a dedicated read-only preflight for this purpose.

## Operate or repeat the prepared local profile

The active test cluster is `civitas-local-160` with context
`k3d-civitas-local-160`. The earlier `civitas-local` cluster remains stopped and
retained. The durable entrypoint is
`C:/Dev/Projects/baikor_r/civitas-core-1.6.0/local_deployment/deploy-baikor-core160.sh`.
Its default selects owner mode and only the addon tasks:

```powershell
wsl -d Ubuntu -- bash /mnt/c/Dev/Projects/baikor_r/civitas-core-1.6.0/local_deployment/deploy-baikor-core160.sh
```

The helper loads `inventory-core160-software.yml` and the pinned controller
toolchain. Its selected inventory fixes the Kubernetes context, so it does not
depend on the shell's current kubectl context. The local modes are:

| Mode | `BAIKOR_CORE160_INVENTORY` | `BAIKOR_CORE160_TAGS` | Additional arguments / prerequisites |
| --- | --- | --- | --- |
| Normal owner operation | `inventory-core160-owner.yml` (default) | `addons` (default) | Existing Baikor database and owner/writer credentials. |
| Full selected Core platform | `inventory-core160-base.yml` | `all` | **`--skip-tags addons` is required**; the base inventory also enables addon import. |
| First Baikor bootstrap | `inventory-core160-bootstrap.yml` | `addons` | Fresh provisioning only, after provider-side database preparation and availability of the temporary `mdh-bootstrap-admin` Secret. That Secret has been deleted from the current tested installation. |

For example, the full Core stage is invoked as:

```powershell
wsl -d Ubuntu -- env BAIKOR_CORE160_INVENTORY=inventory-core160-base.yml BAIKOR_CORE160_TAGS=all bash /mnt/c/Dev/Projects/baikor_r/civitas-core-1.6.0/local_deployment/deploy-baikor-core160.sh --skip-tags addons
```

Select bootstrap mode through the same helper with
`BAIKOR_CORE160_INVENTORY=inventory-core160-bootstrap.yml`; normal updates use
the owner default. The helper is the playbook entrypoint for this **prepared local
profile**, not a complete from-scratch cluster installer. Core checkout/patch,
image pins, local ingress/DNS and controller dependencies must already exist.
After initial Core server creation, provider-side TLS, the separate credential
namespace, CA Secret and initial bootstrap Secret are separate preparation steps;
the full Core helper mode does not perform them.

## Runtime evidence and limits

The local evidence snapshot is stored outside the repository at
`C:/Users/KevinBindig/AppData/Local/Temp/baikor-core160-20261016/`. It includes
`core-complete.log`, `addon-bootstrap.log`, `addon-owner.log`,
`addon-owner-repeat.log`, `app-e2e-bootstrap.log`, `app-e2e-owner-repeat.log`,
`app-image-proof.json`, `app-runtime-bootstrap-proof.json`,
`app-runtime-owner-proof.json`, `app-runtime-owner-repeat-proof.json`,
`database-bootstrap-proof.json`, `database-owner-proof.json`,
`database-owner-repeat-proof.json`, `database-final-proof.json`,
`retention-probe-state.json`, `final-cluster-proof.json`, `namespace-tests.log` and
`public-artifacts-check.txt`. These are local test results, not CI-run status.
The temporary directory is not a durable repository artifact; this document
preserves the relevant results and identifiers.

| Check | Evidence at this review snapshot |
| --- | --- |
| Configuration and registry tests | 23 tests passed independently during the A2 review. This is source-level validation, not a Core 1.6 runtime result. |
| Owner bootstrap SQL | The A2 implementer reported a successful isolated PostgreSQL/PostGIS Docker test covering owner reconciliation, retained data, publication isolation and denied server privileges. That test was reviewed but not independently rerun for this document. |
| Previous Core 1.7.2-based deployment | Earlier evidence recorded 77 end-to-end checks and PSA rejection of a privileged Pod. These results must not be reused as the Core 1.6 verdict. |
| Fresh patched Core 1.6 platform | **Passed:** `core-complete.log` exit `0`; Ansible recap `ok=493 changed=42 failed=0 unreachable=0 skipped=326`. All selected Core components are ready, including a second successful Keycloak configuration pass. Local Keycloak backport, moved image-path overrides and the service-portal image pin are required test deviations. |
| Core Keycloak configuration after backport | Verified `Catalogue Resource`, `Operator Policy`, `Operator Permissions` and six scopes; `Default Resource` is absent. The second Core configuration pass succeeded. |
| Service-portal image compatibility | Reproduced HTTP `502` with the current mutable `latest` image despite Pod readiness: image port `8080` conflicts with Core 1.6 port `80`. Official `2.0.0` digest selected and applied; port `80` verified from image configuration/source, component ready in the successful full base-platform run. |
| pgAdmin cold start | One startup-probe restart after 180 seconds, no OOM; subsequently ready with HTTP `200`. Nonfatal sudo/Postfix warning left unchanged. |
| Core 1.6 namespace integration | Passed with the exact Core 1.6 namespace template and test toolchain: Core-managed namespace creation and idempotence, acceptance of a compliant Pod, rejection of a privileged Pod by `restricted`, and missing/unrestricted/operator-owned namespace guards without modifying operator-owned namespaces. These checks use isolated test namespaces. |
| Ingress and certificates | ingress-nginx chart `4.15.1` / controller `1.15.1` and cert-manager `1.14.4` identified; Gateway API absence confirmed. Baikor HTTPS `/health/live` and `/health/ready` return `200`. |
| MDH-style database prerequisites | Restricted `mdh-baikor-access` namespace, bootstrap administrator Secret and CA prepared; PostgreSQL TLS configured and both database Pods ready. Database `baikor_r` absent immediately before bootstrap. |
| Core 1.6 Baikor first install, migrations and HTTPS health | **Passed:** `addon-bootstrap.log` recap `ok=90 changed=14 unreachable=0 failed=0 skipped=23`; migration succeeded, application ready and both health endpoints return `200`. |
| Core 1.6 Baikor namespace policy and process security | **Passed:** actual application namespace enforces `restricted`; privileged server dry-run rejected with `403`. Application and migration security configurations verified. Running application UID `1654`, `/proc` values `NoNewPrivs=1`, `CapEff=0000000000000000`, `Seccomp=2`. Migration completed successfully; the live-process inspection applies to the application. |
| Database ownership, grants and TLS | **Passed:** PostgreSQL `15.6`, PostGIS `3.4.2`, TLS `1.3` with configured `VerifyFull`. Database, schema and all checked application objects owned by the owner; zero missing writer table/default grants. Writer and owner have no superuser, CREATEDB, CREATEROLE, replication or BYPASSRLS attributes and no role memberships. Writer cannot create schema objects; owner can. |
| Core 1.6 authentication, authorization, attachments and logout | **Passed twice:** `app-e2e-bootstrap.log` and `app-e2e-owner-repeat.log` each record 77 checks with zero failures, including removal of disposable test accounts. The second run exited `0` after the identical owner-mode deployment repeat. |
| Bootstrap-admin to owner transition on the new installation | **Passed:** `addon-owner.log` exit `0`, recap `ok=87 changed=5 unreachable=0 failed=0 skipped=24`. The completed bootstrap Job uses `baikor-owner` and maintenance database `baikor_r`; database TLS, ownership and privilege checks passed again. Temporary `mdh-bootstrap-admin` Secret was deleted before the run; the provider-owned PostgreSQL credential Secret and role remain untouched. |
| Owner-transition retention | **Passed:** probe row retained, same PVC UID, identical Data Protection key checksums and unchanged writer/owner Secret data. Application Pod changed and Deployment generation increased from `1` to `2`; this is a successful preserving redeployment, not a no-change workload result. |
| Identical owner-mode repeat | **Passed:** `addon-owner-repeat.log` exit `0`, recap `ok=87 changed=5 unreachable=0 failed=0 skipped=24`. Owner Job uses `baikor-owner`/`baikor_r`; database privilege and TLS checks pass again. PVC UID, key bytes and writer/owner Secret data match the first-install baseline. Deployment generation is now `3` and the application Pod changed again. The local timestamp therefore still prevents a no-change workload result. |
| Retention-probe cleanup | **Passed:** the probe row survived both owner upgrades. Guarded cleanup completed; `retention-probe-state.json` has status `cleaned` and `last_proof.table_removed: true`. `database-final-proof.json` passes ownership, grants and TLS checks after cleanup, with five application tables remaining. |
| Final cluster and credential state | `final-cluster-proof.json` records 38 Pods: 36 ready, two completed and none unready. The temporary bootstrap administrator copy Secret is absent; `mdh-baikor-access` retains the owner, writer and CA Secrets. The provider-owned PostgreSQL administrator Secret and role remain untouched. The new cluster is active and the previous cluster retained/stopped. |
| Public OCI chart and published application image | **Failed:** anonymous access to both configured `1.7.5` manifests returns `401`; repository metadata returns `404`. A public PostgreSQL control artifact returns `200`. See the exact scope below. |
| MDH-equivalent Kubernetes version and policies | Unknown; requires operator environment information. |

No simplification above has been implemented by this review. The deployment
findings, proposed changes and completed local verification are recorded
separately; the public distribution failure and environment limits remain open.

## Public artifact access

On 2026-10-16, anonymous checks of the configured
`oci://registry-1.docker.io/synnotech-ag/baikor-r-chart:1.7.5` chart and
`docker.io/synnotech-ag/baikor-r:1.7.5` image failed: token responses granted no
repository actions, manifest requests returned `401 Unauthorized`, and public
repository metadata returned `404`. Anonymous `helm show chart` also returned
`401`. The control image `docker.io/library/postgres:15.18-bookworm` returned
`200`, ruling out a general Docker Hub/network outage for these checks.

These responses cannot distinguish a private repository from a missing repository
or incorrect namespace, and do not prove that only a version tag is missing. No
published Baikor digest could be obtained. The successful local chart/image test
therefore does not establish that the default distribution path works. Operators
must verify access to the selected artifacts before deployment. The checked-in
application release pipeline contains anonymous retrieval checks, but its source
does not prove that a publication run completed successfully.

## Remaining review findings at 2026-10-16 (historical)

This is a source inspection of the working trees on October 16, not evidence of a
successful CI run or a completed organizational approval. Application paths below
refer to the sibling `baikor_r` repository.

| Finding | Current evidence and next step |
| --- | --- |
| B1: application source and license | Addon [EUPL-1.2 license](../LICENSE#L4) is present. No tracked application LICENSE or application README license statement found; application-repository public visibility was not checked. Establish the application license and verify public source access. |
| B3: requests, limits and NetworkPolicy | Partly complete: application chart `deploy/helm/baikor-r/values.yaml:95` and `templates/deployment.yaml:100` set resources; [bootstrap resources](../templates/database_bootstrap_job.yml.j2#L32) exist. The chart's `templates/migration-job.yaml:26` has no resources, and no NetworkPolicy template exists. Add migration limits/requests and an optional policy. |
| C1: releases and changelog | Neither repository had a tracked CHANGELOG. The addon README referenced an unspecified "release README" in its Update section. The former application CI defined release creation; addon GitHub releases were not inspected remotely. Verify release availability, add the changelog and correct that reference. |
| C2: OpenAPI import documentation | No OpenAPI/Swagger specification or registration found. Document `src/BaikorR.Host/Controllers/Api/ConstructionSites/Imports/Trenches/ImportTrenchesController.cs:11`, including its multipart input and authentication contract. |
| C3: existing tests in CI | Partly complete at the review date: the former application CI ran backend tests, with frontend lint/build and Helm lint also configured. Addon CI ran registry and Node-RED tests. Operator-ownership, DB/connection-string and the new namespace/owner integration tests were not all included. |
| C4: browser-client scope | [Browser client](../templates/keycloak_client.json.j2#L26) still sets `fullScopeAllowed: true`; the [import client](../templates/keycloak_import_client.json.j2#L13) already sets false. Limit browser scope and verify explicit role mappings and login behavior. |
| C5: ASP.NET environment mapping | [Values generation](../templates/baikor_r_values.yml#L20) passes `ENVIRONMENT` through unchanged; only a missing value defaults to `Production`. Map deployment labels such as `tst` to the intended ASP.NET environment. |
| C6: importer without delete rights | [Import-client configuration](../tasks/baikor_r/import_client.yml#L71) grants `baikor_editor`. Import controller line 12 and delete controller `src/BaikorR.Host/Controllers/Api/ConstructionSites/ById/Delete/DeleteConstructionSiteController.cs:11` share the Editor policy. Add a distinct importer role/policy and verify deletion is forbidden. |
| C7: publication approval | Publication defaults to disabled, and the README explains that diversion/communication text becomes public and requires workspace/access approval. An explicit business approval and privacy review of free text before activation is not yet documented. Actual approval remains an operator decision; configuration alone cannot establish it. |
| C8: GeoServer tasks and CI path | [Task at line 40](../tasks/baikor_r/geoserver.yml#L40) says Create but performs GET. [Feature types](../tasks/baikor_r/geoserver.yml#L202) are created only when absent; existing definitions are not updated. The [CI addon path](../.github/workflows/validate.yml#L27) already correctly uses `core_platform/addons/baikor_r_addon`. |

Source anchors refer to the working-tree snapshot on the review date; application
chart paths are relative to the sibling application repository. Navigation used
GitNexus query/context plus current source inspection. Its addon index was three
commits behind and did not fully resolve Ansible include relationships. Impact
analysis of this new documentation file returned `UNKNOWN`/not indexed; a text
search before its creation found no existing references to the filename. The
README now links to the artifact-access evidence. README impact analysis returned
`LOW` with the manual installation guide as its direct dependent. No runtime files
were changed for this documentation review.
