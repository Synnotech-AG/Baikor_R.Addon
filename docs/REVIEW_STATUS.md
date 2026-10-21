# Review findings status

## Public 1.7.8 acceptance — 2026-10-21

Application/chart **1.7.8** is public: [Release run 39587862516](https://github.com/Synnotech-AG/Baikor_R/actions/runs/39587862516)
published source `e3695b0`. [Addon **1.7.9**](https://github.com/Synnotech-AG/Baikor_R.Addon/releases/tag/1.7.9)
is published from `1d8f696`;
[Validate run 39588355428](https://github.com/Synnotech-AG/Baikor_R.Addon/actions/runs/39588355428)
passed for that revision before publication. Local anonymous downloads matched
the image digest, chart digest and release checksums.

On the isolated Core **1.6.0** environment, all **13 initial steps** passed: **77 human, 70 importer,
211 lifecycle and 41 runtime checks**. Actual isolated addon bootstrap passed
**six phases**, including two owner-only repeats, wrong-CA/privileged-publisher
rejection and recovery; its database, namespace and three roles were removed.
Owner repetition passed **eight preservation comparisons** and **14 Keycloak
continuity checks**.

Migration under an existing NetworkPolicy and actual CNI denial passed. Cold
restart restored **three nodes / 44 Pods in 143 seconds** without repair;
**77 human + 70 import**, retained session (**14 checks**) and 64 KiB attachment
(**19 checks**, including cleanup) passed afterward. Database, Keycloak and PVC
comparisons passed. These tests use the documented local Core adjustments;
they do not claim an untouched Core install or a Windows host reboot.

Earlier working-tree and October 20 evidence below retain their original scope.

## Earlier working-tree verification — 2026-10-21

The [fresh Core 1.6 installation report](initial-installation-2026-10-21.md)
records direct first setup, the cold-image-pull deadline fix, current source/image
identity, successful owner repetition, actual NetworkPolicy enforcement and cold
restart with retained data and authentication. The original local environment is
restored and its 20 auth/API checks passed. Its existing kubelet certificate IP SAN
mismatch blocks `kubectl exec`; no TLS bypass or repair was performed. Read-only
Docker→CRI SQL matched all six database sections against the historical baseline
from **2026-10-20 08:34:43 UTC**, not a snapshot immediately before this test.
Only the original profile is active. Published versions and historical verification are unchanged.

## Published release verification — 2026-10-20

Status: **2026-10-20**. Both source repositories and both GHCR packages are
public. Anonymous Docker and Helm downloads of application/chart **1.7.7**
succeeded using empty credential configurations. The original application
release workflow completed on its second attempt without rebuilding the
published packages; [GitHub release 1.7.7](https://github.com/Synnotech-AG/Baikor_R/releases/tag/1.7.7)
contains the chart, checksums and source-revision metadata.

The compatible [addon release **1.7.8**](https://github.com/Synnotech-AG/Baikor_R.Addon/releases/tag/1.7.8)
is public and pins application/chart **1.7.7**. Its tag identifies commit
`050ce2ea7c0856395bb02cfed50007ac9cd182d0`; all four addon CI jobs passed for that
revision before publication. The historical addon `1.7.7` tag remains unchanged.
The [new reset and direct public-release deployment test](runtime-review-2026-10-20.md)
has passed its initial phase: **77 human + 70 import + 211 publication checks**,
55 runtime assertions, six network checks and six isolated database phases.
The owner repeat repaired both managed FeatureTypes, and a real Helm upgrade
passed with the existing NetworkPolicy present. The second cold restart passed
the full human/import suites again and preserved original data/credentials.
Test-induced login throttling during cleanup and one transient browser search
timeout remain documented. The normal local-image/profile has been restored:
Helm revision 20, local chart/image, Staging and optional NetworkPolicy off.
Final **40 runtime + six network + seven targeted auth checks** and all ten
preservation comparisons passed. These are new tests of the public release;
the earlier bundle test is not substituted for them.

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
| B1 — Public source and license | Both source repositories are public under EUPL-1.2. Application image and chart 1.7.8 passed the release workflow's anonymous-download gate. | None. |
| B2 — Core 1.6 compatibility | Complete for the requested local test: Core 1.6.0 with `enable_gateway: false` passed deployment and Geoportal tests. MDH remains on 1.6. The report retains the local Keycloak/image adjustments and test boundaries. | No 1.7.2 upgrade or separate 1.6 branch is required for this review decision. |
| B3 — Resources and NetworkPolicy | Actual cgroup limits verified. Six functional probes passed with policy off, on, after repeat deployment and after restoration to off; real forbidden traffic is rejected and CNI counters increment. Migration succeeds with the existing policy present. | Operator chooses resource sizing and network rules. Migration hooks need an operator policy if they must also be isolated. |
| C1 — Releases/changelog | Application/chart 1.7.8 and addon 1.7.9 are public, from `e3695b0` and `1d8f696`. Release run `39587862516` and addon Validate run `39588355428` passed. Anonymous retrieval, local runtime, repeat deployment, network and cold-restart acceptance passed as recorded above. | None. |
| C2 — Import OpenAPI | Actual imports match success, validation and duplicate examples. Real file/buffer boundaries and cookie CSRF checked. Found and fixed the ingress size mismatch; guide now distinguishes importer 400, host form-binding 400 and proxy 413. | Operators using other ingress controllers must configure equivalent request limits. |
| C3 — Tests in CI | The October 21 CI TCP-readiness race is fixed on main at `4f570e2`; [CI run 39589291799](https://github.com/Synnotech-AG/Baikor_R/actions/runs/39589291799) passed. This later fixture fix does not change the released 1.7.8 source. Earlier isolated checks covered 77 human/24 machine checks and exact upload limits; addon deadline/waiter regressions passed 48 unit checks. | The October 19 isolated startup timeout remains unconfirmed and unreproduced; the separate TCP-readiness fix does not establish its cause. |
| C4 — Browser scopes | Actual upgrade changed browser full scope from true to false and added exactly four explicit human-role scopes. All 77 real OIDC/session/API checks pass; existing operator access remains 200. | None in the tested local configuration. |
| C5 — ASP.NET environment | Core names map to Development, Staging or Production; unknown values default to Production. Actual repeat deployment reports Production with authentication enabled and invalid-certificate bypass disabled. | Explicit Helm overrides remain the operator's responsibility. |
| C6 — Import-only role | Fresh setup gives the dedicated machine client only `baikor_importer` in its role assignment, explicit token scope and issued tokens. Tests cover optional activation and repeated provisioning with preserved identity and credentials; valid imports work and general API operations remain forbidden. | Use compatible application/chart/addon versions and a dedicated `baikor-r-*` import client. Operators must review any manually added roles or scopes; do not reuse a client with unrelated grants. |
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
- Addon [release 1.7.8](https://github.com/Synnotech-AG/Baikor_R.Addon/releases/tag/1.7.8)
  and its tag were verified through anonymous GitHub API requests. The tag
  resolves to `050ce2ea7c0856395bb02cfed50007ac9cd182d0`.
- Addon [Validate run 39390324015](https://github.com/Synnotech-AG/Baikor_R.Addon/actions/runs/39390324015)
  passed all four jobs at the released revision. Application documentation
  commit `02ff660` passed all five [CI jobs in run 39390303227](https://github.com/Synnotech-AG/Baikor_R/actions/runs/39390303227);
  it does not change the immutable 1.7.7 package source revision.

## Direct public-release runtime verification — 2026-10-20

The [new runtime report](runtime-review-2026-10-20.md) records the initial cold
reset, successful public OCI/image deployment at Helm revision 18, released
artifact identity checks, real browser/Geoportal behavior and database
preservation. Authentication/import/publication checks passed **77 + 70 + 211**;
all **55 runtime assertions**, **six network probes**, **six isolated bootstrap
phases** and **10 preservation comparisons** passed. Two controller invocation
corrections are documented separately from application behavior. The unchanged
owner repeat passed **55 runtime + six network checks** and repaired deliberate
FeatureType drift; ten preservation comparisons passed again. A separate actual
Helm upgrade to revision 19 passed **55 runtime checks** and all three
existing-policy/migration assertions. An incorrect harness assumption about
unchanged deployments recreating migration Jobs is documented explicitly.
The public cold restart reached readiness in **137.1 seconds**, with no
redeployment or role repair before the checks. **77 human + 70 import checks**,
34 live-runtime assertions, six network probes, 14 operator-session continuity
checks and ten preservation comparisons passed. A retained 65,536-byte
attachment and its session passed 14 checks; its cleanup then failed to decode
one response. A separate cleanup passed all 11 ownership checks. The original
failure is retained; matching Keycloak/ingress evidence supports throttling from
overlapping test-helper logins, with no role or security-policy change. A rendered
Geoportal search timeout followed by a successful retry remains unexplained;
a second known site's controlled search passed on its first attempt.
The normal owner deployment then restored local image
`baikor-r:review-1.7.7-6afbbae`, local chart, Staging and optional NetworkPolicy
off at Helm revision 20. Final **40 runtime**, **six network**, **seven targeted
auth** and **ten preservation** checks passed; all 36 active Pods are Ready.
Original inventories, credentials, data and PVC identities remain unchanged.
The existing browser session still shows the original three sites with Create
enabled. All owned test fixtures were removed. The restart evidence concerns
local k3d cluster stops/starts, not a Windows host reboot.

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
