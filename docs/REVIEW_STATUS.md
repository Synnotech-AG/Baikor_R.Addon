# Review findings status

Status: **2026-10-20**. Both source repositories and both GHCR packages are
public. Anonymous Docker and Helm downloads of application/chart **1.7.7**
succeeded using empty credential configurations. The original application
release workflow completed on its second attempt without rebuilding the
published packages; [GitHub release 1.7.7](https://github.com/Synnotech-AG/Baikor_R/releases/tag/1.7.7)
contains the chart, checksums and source-revision metadata.

The compatible addon release being prepared is **1.7.8**; it retains the
application/chart **1.7.7** pins. The historical addon `1.7.7` tag identifies
older code and will not be moved. The new reset and direct public-release
deployment test is pending; the earlier bundle test is not substituted for it.

MDH remains on **Core 1.6**, with `enable_gateway: false`. The requested local
compatibility test is complete. Its [documented platform deviations](core-1.6.0-deployment-review.md)
remain part of the evidence; no exact MDH or untouched Core 1.6 result is claimed.
Actual MDH database connection details are deployment inputs, not an outstanding
addon implementation finding.

The [October 19 runtime review](runtime-review-2026-10-19.md) records the completed
local and authenticated-bundle tests, fixes and preservation checks. Those
phases include repeat deployment, Production/NetworkPolicy, cold restart,
**77 human + 70 import checks** per full run and restoration of the local-image
profile. The recurring local k3d worker-IP race remains an infrastructure
follow-up; successful recovery does not establish a fix for that race.

## Findings

| Finding | Status and evidence | Remaining step |
| --- | --- | --- |
| A1 — Non-root operation and namespace PSA | Actual app/migration/bootstrap runtime credentials, capability masks, seccomp, read-only root filesystem and cgroup limits verified. PSA rejects root and privileged Pods; permitted temporary/PVC writes succeed and are cleaned. | Operator must keep Core PSA enabled. |
| A2 — MDH database and owner operation | Complete on the addon side. Shared owner upgrades preserve data, grants, roles and PVCs. Fresh bootstrap, two owner-only repeats, wrong-CA/privileged-publisher rejection and recovery passed using actual addon tasks. Bootstrap privileges, owner-login operation and freely selectable credential namespace are documented. | MDH supplies its PostgreSQL address, CA and initial provisioning credentials as deployment inputs. No change to automatic database creation is required. |
| B1 — Public source and license | Both source repositories are public under EUPL-1.2. Image and chart 1.7.7 can be downloaded anonymously. | None. |
| B2 — Core 1.6 compatibility | Complete for the requested local test: Core 1.6.0 with `enable_gateway: false` passed deployment and Geoportal tests. MDH remains on 1.6. The report retains the local Keycloak/image adjustments and test boundaries. | No 1.7.2 upgrade or separate 1.6 branch is required for this review decision. |
| B3 — Resources and NetworkPolicy | Actual cgroup limits verified. Six functional probes passed with policy off, on, after repeat deployment and after restoration to off; real forbidden traffic is rejected and CNI counters increment. Migration succeeds with the existing policy present. | Operator chooses resource sizing and network rules. Migration hooks need an operator policy if they must also be isolated. |
| C1 — Releases/changelog | Both repositories have changelogs and corrected release links. Application run `39239993018`, attempt 2, passed anonymous verification and created GitHub release 1.7.7 with the original source/digests. | Publish addon 1.7.8 after its documentation commit and CI; repeat runtime acceptance through the direct public download path. |
| C2 — Import OpenAPI | Actual imports match success, validation and duplicate examples. Real file/buffer boundaries and cookie CSRF checked. Found and fixed the ingress size mismatch; guide now distinguishes importer 400, host form-binding 400 and proxy 413. | Operators using other ingress controllers must configure equivalent request limits. |
| C3 — Tests in CI | Latest isolated Keycloak/PostGIS/Kestrel run passed 77 human and 24 machine checks. New tests cover exact 25 MiB, 25 MiB plus one byte and the complete-request cap. Addon waiter regressions pass in 44 selected unit checks. | One initial isolated startup timeout is retained as an unconfirmed, unreproduced failure; see runtime report. Inspect hosted workflow results for the selected revision. |
| C4 — Browser scopes | Actual upgrade changed browser full scope from true to false and added exactly four explicit human-role scopes. All 77 real OIDC/session/API checks pass; existing operator access remains 200. | None in the tested local configuration. |
| C5 — ASP.NET environment | Core names map to Development, Staging or Production; unknown values default to Production. Actual repeat deployment reports Production with authentication enabled and invalid-certificate bypass disabled. | Explicit Helm overrides remain the operator's responsibility. |
| C6 — Import-only role | Existing machine account had an editor assignment, scope and token before upgrade. All three now contain only `baikor_importer`; valid imports work and nine general API operations return 403. | Deploy addon 1.7.8 with application/chart 1.7.7 and obtain a fresh token. Existing tokens keep their old privileges until expiry. |
| C7 — Publication approval | README and inventory explicitly require recorded business approval and privacy review of public free text before enabling publication. | Actual approvals belong to the responsible data owner/operator and are not supplied by technical tests. |
| C8 — Task/update/CI details | Actual addon deployment restores deliberate managed FeatureType title/abstract drift; live publication lifecycle passed 211 checks. Datastore task and Core CI path corrections remain covered. | GeoServer may normalize previously absent flags; byte-identical FeatureType JSON is not promised. |

## Public distribution verification — 2026-10-20

- [Application source](https://github.com/Synnotech-AG/Baikor_R) and
  [addon source](https://github.com/Synnotech-AG/Baikor_R.Addon) are public.
- Anonymous Docker pull of `ghcr.io/synnotech-ag/baikor-r:1.7.7` and Helm download
  of `oci://ghcr.io/synnotech-ag/baikor-r-chart`, version `1.7.7`, succeeded with
  empty credential configurations.
- Immutable image digest:
  `sha256:6e9f2824b4774496783b96d6e8ef5ccfb00006c8afaa71280d2d8b3079d1a0be`.
- Immutable chart manifest digest:
  `sha256:f1ffdc39cec1ea63e6d6d2fb680a180fd3acf7b5646ba7d2147701ad5b73f691`.
- Application [release run 39239993018](https://github.com/Synnotech-AG/Baikor_R/actions/runs/39239993018),
  attempt 2, completed from source `6afbbaed75f4c201c584d88eaee1e196b15a2720`.
  Anonymous release-asset checks matched `SHA256SUMS`; chart archive SHA256 is
  `c5eff82e139ba92e4ad916b181bc174238fd2d59a04c4b4f6517129ec3b4324f`.

## Earlier runtime verification — 2026-10-19

- Shared Core, policy off: **77 human checks**, then **70 import/auth checks
  after the ingress fix**, zero failures. Policy on with Production: **77 + 70**,
  zero failures. After the cold restart: **77 + 70**, zero failures.
- Published 1.7.7 packages via the verified Actions bundle, Production and
  NetworkPolicy on: **77 + 70**, zero failures, repeated **77 + 70** after its
  cold restart; the existing browser session survives rollouts and cold restarts.
  Final restoration uses an access/scope baseline, with no additional full-suite
  count claimed.
- Isolated real Keycloak/PostGIS/Kestrel fixture: **77 + 24**, zero failures;
  earlier failed attempts and the precise client-side correction are retained.
- Publication lifecycle: **211/211** on local sources and **211/211** on the
  published bundle, using actual PostgreSQL, anonymous WFS/WMS and owned
  synthetic records; original records remain unchanged.
- Actual network probes: **6/6** off, **6/6** on, **6/6** after repeat, **6/6**
  after restoring the original off/Staging profile, **6/6** after cold restart,
  **6/6** in each published initial/repeat/cold restart phase, and **6/6** after
  final local restoration: **54 total** across nine distinct phases.
  Published runtime security: **34/34**, plus **18/18** after restart; final
  local runtime/profile/readiness assertions: **41/41**.
- Upload chart regression: failed against the old default, **9/9** checks after
  setting the ingress-nginx complete-body limit to `26m`.
- Fresh database failure handling: four new regressions; **44/44** selected addon
  unit checks. Actual wrong-CA and privileged-publisher failures now return within
  about three seconds after terminal Job failure.
- OpenAPI lint passes. The prior source baseline also recorded 105 backend tests,
  release-contract/workflow validation and disposable Kubernetes checks; these
  are separate from the new shared-cluster evidence above.
- Bundle implementation commit `eaa042b` passes all five hosted CI jobs in
  run `39241616264`; all **14 release checks** and actionlint pass. The successful
  bundle run proves authenticated registry retrieval in Actions.
- Addon commit `b6ae466` passes all four hosted jobs in run `39240852888`.
  It corrects the earlier CI dependency-fetch failure with `--no-cache`; that
  failure is recorded separately from application runtime findings.

The application and addon workflows repeat the relevant automated checks on
GitHub. CI, builds and local deployments do not require public GHCR packages.
The release workflow separately verifies anonymous downloads before creating a
GitHub release.

The [historical Core deployment evidence](core-1.6.0-deployment-review.md) and
[Geoportal test](core-1.6.0-geoportal-test.md) describe the October 16 baseline.
Use the [October 19 runtime report](runtime-review-2026-10-19.md) for the upgraded
image, authorization, database, ingress and network checks in that test phase.

GitNexus impact/change analysis was used alongside direct source review. The
available indices are stale and do not resolve several newer Python/report
paths. Unresolved graph coverage was checked against source and targeted tests
rather than treated as proof that no callers exist.

## Related documentation

- [Application changelog](https://github.com/Synnotech-AG/Baikor_R/blob/main/CHANGELOG.md)
- [Addon changelog](../CHANGELOG.md)
- [Import API contract](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/openapi/README.md)
- [Helm security and network configuration](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/HELM_SECURITY.md)
- [Release workflow and recovery](https://github.com/Synnotech-AG/Baikor_R/blob/main/docs/RELEASING.md)
