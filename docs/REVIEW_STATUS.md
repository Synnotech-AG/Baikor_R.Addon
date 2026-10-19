# Review findings status

Status: 2026-10-19. The latest application and addon changes target **1.7.7**.
This version is not published yet. Use the matching local chart and a locally
built image for testing; the older private 1.7.6 packages do not contain these
fixes. Public package visibility and release publication are deliberately deferred.

## Findings

| Finding | Status and evidence | Remaining step |
| --- | --- | --- |
| A1 — Non-root operation and namespace PSA | Explicit Pod/container security contexts; namespace uses the Core template. Restricted admission and bootstrap Jobs are tested in disposable Kubernetes CI. | Operator must keep Core PSA enabled. |
| A2 — MDH database and owner operation | README documents first-bootstrap permissions, normal owner-login operation and freely selectable `database.namespace`. Initial and repeat owner deployments passed in the local MDH simulation. | Operator supplies the actual PostgreSQL server, CA and credentials. |
| B1 — Public source and license | Application source is public on GitHub under EUPL-1.2. | Public image/chart access remains pending GitHub organization package policy. |
| B2 — Core 1.6 compatibility | Local patched Core 1.6.0 with `enable_gateway: false` passed deployment and Geoportal tests; deviations are recorded in the deployment review. | Agree with MDH whether its existing 1.6 setup is sufficient or update to 1.7.2. Exact MDH/unmodified 1.6 compatibility is not established. No separate 1.6 branch. |
| B3 — Resources and NetworkPolicy | App and migration Job have independently configurable requests/limits. Optional app NetworkPolicy is rendered and tested, including real allow/deny traffic. | Operator chooses resource sizing and network rules. Migration hooks need an operator policy if they must also be isolated. |
| C1 — Releases/changelog | Both repositories have changelogs; README release links are corrected. Application release workflow is implemented and validated. | Publish the next version after public package access is enabled. No completed 1.7.6 or 1.7.7 GitHub release is claimed. |
| C2 — Import OpenAPI | Versioned OpenAPI contract, integration guide and eight HTTP contract tests added to the application; schema lint runs in CI. | None in the requested documentation scope. |
| C3 — Tests in CI | Application CI runs backend/frontend/Helm/release and real Keycloak/PostGIS checks. Addon CI runs lint, template/operator/database/Kubernetes tests and real Keycloak reconciliation. | None in the CI integration scope; inspect each workflow result for the selected revision. |
| C4 — Browser scopes | `fullScopeAllowed: false`; explicit viewer/editor/approver/admin scopes preserve browser access. | Normal addon deployment applies the change. |
| C5 — ASP.NET environment | Core names map to Development, Staging or Production. Unknown values default to Production; explicit Helm overrides remain available. | None. |
| C6 — Import-only role | Optional machine client uses `baikor_importer`; API permits import but denies general reading/editing/approval/deletion. Upgrade removes the generated legacy editor assignment and scope. | Deploy matching app/addon 1.7.7+ together and obtain a fresh token. Existing tokens keep their old privileges until expiry. |
| C7 — Publication approval | README and inventory explicitly require recorded business approval and privacy review of public free text before enabling publication. | Actual approvals belong to the responsible data owner/operator and are not supplied by technical tests. |
| C8 — Task/update/CI details | Datastore-read task name corrected; existing addon FeatureTypes receive PUT updates; CI uses the correct Core addon path. | New FeatureType update behavior has rendered-task regression coverage; it has not yet been rerun against the shared local GeoServer. |

## Verification of the new source

- 105 backend tests passed, including real HTTP authorization and OpenAPI contracts.
- 77 isolated platform checks passed with real Keycloak and PostGIS, followed by
  14 machine-client checks: valid import creates a site; disallowed routes return 403.
- Seven Helm rendering tests passed; Kubernetes server validation and ten real
  NetworkPolicy traffic checks passed in a disposable cluster.
- 40 addon unit tests passed, including environment mapping, FeatureType updates
  and Keycloak reconciliation configuration; operator-ownership and Node-RED
  example checks passed.
- OpenAPI lint, release-contract tests and workflow syntax validation passed.
- Actual addon Ansible tasks passed against disposable Keycloak for fresh
  installation and legacy editor-role upgrade, each repeated successfully;
  newly issued tokens contained only the importer role and the expected audience.

The application and addon workflows repeat the relevant automated checks on
GitHub. CI, builds and local deployments do not require public GHCR packages.
The release workflow separately verifies anonymous downloads before creating a
GitHub release.

The existing shared Core test deployment was not upgraded by these source changes.
These fresh checks use isolated services and test credentials. See the
[historical Core deployment evidence](core-1.6.0-deployment-review.md) and
[Geoportal test](core-1.6.0-geoportal-test.md) for the earlier cluster results;
they must not be read as validation of the new image.

GitNexus impact/change analysis was used alongside direct source review. Its
application index predates the repository migration and its addon index is one
commit behind the baseline; index refresh did not complete. Unresolved graph
coverage was checked against source and targeted tests rather than treated as
proof that no callers exist.

## Related documentation

- [Application changelog](https://github.com/Synnotech-AG/Baikor_R/blob/main/CHANGELOG.md)
- [Addon changelog](../CHANGELOG.md)
- [Import API contract](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/openapi/README.md)
- [Helm security and network configuration](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/HELM_SECURITY.md)
- [Release workflow and recovery](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/RELEASING.md)
