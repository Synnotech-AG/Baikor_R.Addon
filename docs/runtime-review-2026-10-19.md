# Runtime review — 2026-10-19

The matching 1.7.7 application/addon sources have been exercised on the existing
patched Core 1.6.0 test deployment, including repeat owner deployment,
`Production` and enabled application NetworkPolicy. This is a local runtime
acceptance report, not a claim of exact MDH or unmodified Core compatibility.
The [review status](REVIEW_STATUS.md) maps these results to findings A1–C8.

Local and published-package deployment/repeat/cold-restart phases are complete.
Each full auth/import run passed **77 + 70 checks** after the ingress correction.
The published packages were downloaded in authenticated GitHub Actions, verified
locally and deployed under Production with NetworkPolicy enabled. This is indirect
registry verification; direct local GHCR access remains unverified.

The normal local helper restored `baikor-r:review-1.7.7-6afbbae`, Staging and
disabled optional NetworkPolicy without command-line overrides. All three nodes
and 36 active Pods are ready. Original data, credentials, PVCs, browser-session
access and publication behavior are preserved; the final baseline, six traffic
probes and 41 runtime/profile/readiness assertions pass. The restart helper waited
through the recurring worker-IP race described below; it did not eliminate it.
Public package availability and a completed GitHub release remain open under
organization policy.

## Scope and preservation

- Context: `k3d-civitas-local-160`; application origin is the existing HTTPS
  ingress. Initial acceptance image: `baikor-r:review-1.7.7-dacaee4`; restart
  image: `baikor-r:review-1.7.7-6afbbae`, with matching local chart and addon
  changes. The ingress-nginx path is tested; Gateway API is absent.
- Full selected addon deployments completed with `ok=115`, `changed=5`,
  `failed=0`, including repeat deployment with NetworkPolicy already present.
- A PostgreSQL dump was encrypted with Windows DPAPI before the upgrade; decrypt
  round-trip and `pg_restore --list` were checked without persisting plaintext.
- Five table hashes, three original site row hashes, role/object/default grants
  and PVC identities remained unchanged through the upgrade and publication
  lifecycle. Exactly three original sites remained after fixture cleanup.
- Test users and import/publication fixtures are synthetic. Cleanup selects only
  owned users/record identifiers or an exact owned import marker and batch.
  Credentials and access tokens stay in memory and are absent from evidence.
- Application follow-up source commit: `6afbbaed75f4c201c584d88eaee1e196b15a2720`.
  All five jobs in hosted CI run `39239035662` passed. Addon waiter fix source:
  `16b6cc4`. Evidence-report edits are separate from those code revisions.
- Addon CI cache correction: `b6ae466`; all four hosted jobs in run
  `39240852888` passed. Earlier run `39239299468` failed fetching an Ansible
  collection dependency. Adding `--no-cache` to that download corrected the
  CI failure; this was not an application runtime defect. The pinned local
  validator also passed with explicit Core Ansible configuration: zero failures
  or warnings across 46 linted files.

## GitHub package publication

Release workflow run `39239993018` passed its CI jobs and published the 1.7.7
artifacts from application source `6afbbaed75f4c201c584d88eaee1e196b15a2720`:

| Artifact | Published digest |
| --- | --- |
| Application image | `sha256:6e9f2824b4774496783b96d6e8ef5ccfb00006c8afaa71280d2d8b3079d1a0be` |
| Helm chart | `sha256:f1ffdc39cec1ea63e6d6d2fb680a180fd3acf7b5646ba7d2147701ad5b73f691` |

The anonymous-download gate then failed with HTTP 401, so this run did not
complete a GitHub release. A local authenticated manifest request returned 403:
the credential available through Git Credential Manager had repository/workflow
scopes but no `read:packages` scope. Successful registry login and token exchange
alone did not prove artifact access. Temporary registry credentials were removed.
The operator selected an authenticated Actions test bundle. The read-only job
`39241636968` succeeded using workflow commit `eaa042b05a14968a64b4e7a104eeb5a4f81305b9`.
It downloaded both published digests with its runner token and exported an image
archive, original chart archive, `bundle.json` and `SHA256SUMS`. The local download
verified those checksums, exact source/revision/version metadata, chart metadata,
image configuration and chart layer:

- Image configuration: `sha256:13be8b200c9cb9a64594e4e2873d334655972e53428d8dadcb493e633c95c662`.
- Chart content layer: `sha256:c5eff82e139ba92e4ad916b181bc174238fd2d59a04c4b4f6517129ec3b4324f`.

All five CI jobs for the bundle implementation passed in run `39241616264`;
14 release checks and actionlint pass. The bundle exports existing artifacts;
it does not build/push packages or bypass the normal anonymous-release gate.

The actual selected Core deployment completed `ok=115`, `changed=5`, `failed=0`.
All eight installed chart templates matched the downloaded chart archive.
The deployed published image passed 77 human and 70 importer checks through the
real HTTPS ingress, with owned fixtures removed. The existing browser cookie
remained usable without a login. Runtime security checks passed 34/34, the six
network probes passed, and CNI rejection counters increased from 3 to 6. PSA
and real filesystem checks passed again with temporary writes removed.
The full publication lifecycle also passed **211/211** again on the published
bundle. Its fixture, attachment and temporary human editor were removed. Fresh
role/TLS/writer-identity checks passed, and the original three sites, five table
hashes, grants, roles, migrations, PVCs and credential data remained unchanged.

All three nodes' image configurations match the published image configuration;
all eleven exported layer hashes match its `diff_ids` and local manifest layer
descriptors. Docker archive import produced a different local manifest digest,
so package identity is established by verified configuration and layers, not a
claim that the local manifest digest equals the registry manifest digest.
This is indirect registry evidence: GHCR was authenticated in Actions and the
checked Actions artifact was authenticated locally. It does not prove direct
local GHCR authentication or anonymous availability.

The repeat published-package deployment also completed `ok=115`, `changed=5`,
`failed=0`. Ten runtime assertions confirm its new migration succeeded with the
same pre-existing policy and exact published configuration. The subsequent
cold restart reached three ready nodes and 36 ready Pods in 219 seconds without
operator intervention. The Docker worker-IP swap recurred and each worker
restarted eight times before Node metadata caught up. The helper waited through
infrastructure recovery; it does not eliminate that underlying race.
After restart, the full **77 + 70** auth/import suite passed with fixtures cleaned,
all six network probes passed, and 18 runtime/policy assertions confirmed the
published configuration, policy identity and security/resource settings persisted.
Original data/grants/migrations, PVCs and credential data remained unchanged;
actual owner/writer/publisher TLS and anonymous WFS/WMS checks passed again.
The existing browser session and real Geoportal search/polygon/GetFeatureInfo
also survived this published-package restart.

## Final local restoration

The normal local helper completed with `ok=115`, `changed=5`, `failed=0`, using
its durably updated defaults and no command-line overrides. Helm release 17 uses
the local chart and image `baikor-r:review-1.7.7-6afbbae`; the actual app/migration
configuration matches that image. Staging is restored, authentication and TLS
validation remain enabled, and the optional NetworkPolicy is absent. Temporary
GHCR credentials and the temporary pull Secret are absent.

The final access baseline returns 200 for existing-operator login and `/api/me`,
retains four explicit human scopes, and confirms importer-only assignments,
scope and fresh token. It is a baseline check, not another full 77 + 70 run.
The retained browser session shows the three original sites and creation access.
All five original table hashes, three site rows, roles/grants/migrations, PVCs and
credential data remain unchanged. Real TLS/role and WFS/WMS checks pass. The six
network probes and 41 runtime/profile/readiness assertions pass; both paths denied
under policy are reachable again. All three nodes and 36 active Pods are ready.

## Runtime results

| Area | Actual observation | Result |
| --- | --- | --- |
| Human identity and sessions | Real Keycloak authorization-code/form-post login, application cookies, role matrix, CSRF, concurrent edit, attachments, logout/SSO and account switching. These are HTTP/cookie-jar checks, not browser rendering automation. | 77/77 in each local off, local on/Production, local cold restart, published bundle and published cold restart phase. |
| Browser and importer upgrade | Browser full scope true → false with four explicit human scopes. Existing import account's editor assignment, scope and fresh token become importer-only. Existing operator login and `/api/me` remain 200 with four human roles. | Verified before/after against the actual realm. |
| Import/OpenAPI | Real two-feature shapefile, public feature persistence, house connection skipping, exact documented success/400/409 fields, duplicate detection, malformed ZIP/multiple SHPs, buffer bounds 0.1–20, cookie CSRF and authentication challenge. Nine general importer API operations return 403. | 70/70 through HTTPS ingress in each post-fix local off, local on/Production, local cold restart, published bundle and published cold restart phase. |
| Isolated CI | Fresh Keycloak/PostGIS/application containers; real TLS Kestrel receives 25 MiB and 25 MiB+1 uploads and rejects an oversized declared request. | Latest run 77 human + 24 machine checks, zero failures. Earlier failures retained below. |
| Runtime security/resources | Containerd runtime specifications, `/proc` and cgroups confirm non-root users, no capabilities, `noNewPrivileges`, read-only root, seccomp and CPU/memory limits. PSA rejects root and privileged Pods; temporary/PVC writes succeed and are cleaned. | App/migration UID/GID 1654; bootstrap UID/GID 999. Both namespaces enforce restricted PSA. |
| NetworkPolicy | Ingress health and OIDC challenge, actual app→OIDC discovery and Prometheus→metrics succeed. Actual app→unlisted service and GeoServer→app change from allowed to denied. CNI rejection counter increases during denied probes. | 6/6 in nine phases: local off/on/repeat/restored/cold restart, published initial/repeat/cold restart and final local restoration; 54 checks total. |
| Production and migration | Production-phase runtime has authentication enabled and invalid-certificate bypass disabled. An existing policy predates the successful repeat migration Job. The original Staging profile is subsequently restored. | Runtime and Job timestamps verified. Policy selects the app; it does not isolate migration hooks. |
| PostgreSQL/GeoServer | Real owner/writer/publisher TLS sessions use `verify-full`; wrong hostname/CA rejected. Unprivileged roles have no role memberships; publisher private-table SELECT fails with SQLSTATE 42501. Actual GeoServer JNDI uses publisher identity and operator CA without inline credentials. | Shared owner-mode operation and retention verified. |
| Publication lifecycle | Draft→Approved→Active→Planned→Approved→Draft→Approved→delete, using a disposable human editor. Per-state checks query publisher DB, anonymous WFS, XML title lookup, WMS alpha and GetFeatureInfo; private sentinels stay absent. | 211/211 on local sources and 211/211 on the published bundle; current title and 6400 m² geometry observed; owned fixtures removed. |
| FeatureType reconciliation | Deliberate managed title/abstract drift is restored by actual addon deployment. GeoServer also adds two previously absent false flags. | Managed behavior verified; no byte-identical JSON claim. |
| Fresh database setup | Actual addon tasks perform first bootstrap, two owner repeats after temporary admin Secret removal, wrong-CA and privileged-publisher rejection, then recovery. | All six phases repeated after the waiter fix; credentials/data preserved. |
| Browser UI | Real Geoportal search returns a published site; selection shows its polygon, and GetFeatureInfo shows the expected public title/status/area/messages. Draft search returns no result. The existing application browser session still shows the original sites and enables creation after the rollouts and cold restart without a new login. | Rendered browser checks complement the HTTP/cookie-jar suites; cold-restart session survival verified. |

The tested app/migration requests are 50m CPU/128 MiB, with 500m CPU/512 MiB
limits; runtime quota is 50000/100000 and memory limit 536870912 bytes. Bootstrap
requests are 10m/32 MiB with 250m/128 MiB limits; runtime quota is 25000/100000 and
memory limit 134217728 bytes. The tested namespaces have no ResourceQuota or
LimitRange. Operators must size their own installation and any hook isolation.

## Runtime findings and fixes

**Ingress upload limit.** Before the correction, a valid exact 25 MiB archive
received 413 HTML at HTTPS ingress but 200 JSON through a loopback-only service
tunnel. The direct application returned importer 400/`fileTooLarge` at 25 MiB+1.
This proved a proxy limit, rather than an importer/parser failure. The chart now
defaults `nginx.ingress.kubernetes.io/proxy-body-size` to `26m`; operator override
and removal remain supported. A new rendering regression failed before the fix;
all nine chart checks pass after it. The real ingress rerun returns 200 at exactly
25 MiB, 400/`fileTooLarge` at one byte above, and proxy 413 above the 26 MiB complete
request limit. Other ingress controllers need an equivalent limit.

**Complete-request response.** Direct Kestrel returns form-binding 400 Problem
Details above 26 MiB, reporting the 27262976-byte maximum under `errors[""]`,
without importer `errorKey`/`errorKeys`. The OpenAPI guide/spec now distinguish
this from importer validation and proxy 413. Over TLS, urllib can receive a
connection reset while continuing to send a body after this early rejection.
The isolated regression therefore uses `Expect: 100-continue` for the oversized
declared multipart request and reads the real 400 without sending the rejected
body. The exact 25 MiB and 25 MiB+1 cases transmit complete valid ZIP archives.

**Terminal database Job polling.** The old waiter used 90 observations and returned
266.203 seconds after a deliberately failing wrong-CA Job reached terminal failure.
Its `until` condition now stops for either success or terminal failure;
the existing failure condition and retry/delay budgets remain. Four new
regression tests pass within 44 selected addon unit checks. Real repeated fault
cases now return after 2.787 seconds (wrong CA) and 2.333 seconds (privileged
publisher), each with three observations; recovery succeeds.

The fresh database test covers the actual credential and bootstrap tasks, not a
complete fresh application/Core installation. Its credential namespaces differ
from the PostgreSQL server namespace. The isolated Job used `postgres:15`; the
normal deployment uses `docker.io/library/postgres:15.18-bookworm`. Both isolated
namespaces/databases and all six synthetic roles were removed. Final preservation
checks still show the original five table hashes, three site rows and existing
roles unchanged, with the bootstrap-administrator Secret absent.

**Local restart recovery.** The first k3d start failed its host-injection step
while both worker containers restarted with exit code 0 and no OOM indication.
Their Docker addresses had swapped, while kube-router still attempted interface
lookup using the old Kubernetes Node IPs. Both agents recovered after eight
restart attempts once Node IP metadata updated; no infrastructure configuration
patch was required. A repeated k3d start completed host/CoreDNS setup. All three
nodes and 36 Pods became ready. The original application browser session and all
77 human plus 70 import/API assertions passed after recovery. This records a
recovered local infrastructure failure, not a clean first-attempt restart.
After fixture cleanup, all five table hashes, three original site rows, PVC IDs
and credential data fingerprints remain unchanged. Actual TLS/role checks still
pass, GeoServer exposes the expected three areas/two points, and anonymous WMS
and GetFeatureInfo work. The surviving browser session supports Data Protection
continuity; no separate key-file hash was captured or is claimed.

A second complete stop/start through the bounded restart helper completed with
exit code 0 in 155.4 seconds, with all three nodes and 36 active Pods ready.
The workers remained running with zero restarts and no OOM indication.
Independent post-helper database/credential/PVC hashes, TLS/role checks and
anonymous WFS/WMS publication checks passed again. This later helper test does
not erase the first raw k3d start failure described above.

## Limits and remaining decisions

- The first isolated CI application process did not open its HTTPS listener
  within 180 seconds. It remained running with sampled near-zero CPU, normal
  binding/Data Protection warnings and no observed startup error. Same-image
  HTTP/HTTPS/CA control starts and two fresh Compose starts worked. The original
  container was cleaned; retained evidence does not identify the blocked startup
  operation. Classification: **unconfirmed one-off failure, root cause unknown**,
  not a demonstrated permanent fix or a guarantee against recurrence.
- K3s implements the tested denied traffic with ICMP port-unreachable rejection,
  so the observed client result is refusal rather than timeout. A later counter
  sample encountered rule-chain regeneration; the initial counter proof and all
  repeat functional allow/deny checks remain valid.
- Publication tests use synthetic data. Actual data-owner business approval and
  privacy review of public free text remain operator responsibilities (C7).
- Fresh importer tokens are restricted. Previously issued editor tokens retain
  their prior privileges until expiry; the tests do not claim retroactive token
  revocation.
- Historical Core patches, moved/pinned image selections, the JNDI workaround,
  local certificate setup and ingress choice remain documented in the
  [October 16 baseline](core-1.6.0-deployment-review.md) and
  [Geoportal report](core-1.6.0-geoportal-test.md). No exact MDH result is claimed.
- Cold whole-cluster restart recovered as described above; application/session,
  database/credential/PVC, publication and six network checks passed. Actual
  process/cgroup restrictions remain unchanged.
  The published 1.7.7 bundle was retrieved and deployed with passing auth/import,
  runtime-security and network checks, repeated after its cold restart.
  The normal local image/profile was restored and verified as described above.
- Public package visibility and completed GitHub release: **open**. Local and
  authenticated-package validation do not establish anonymous availability.

## Evidence locations

Sanitized, ignored local artifacts are under the application checkout's
`artifacts/runtime-review-20261019/`; these paths are local evidence, not public
download links. They contain assertion results/configuration facts, not tokens,
passwords or original private record contents.

| Directory | Principal files |
| --- | --- |
| `auth/` | `before-upgrade.json`, `after-ingress-fix.json`, `human-local.log`, `local-acceptance.json` (initial red), `direct-boundaries.json`, `direct-overlimit.json`, `local-acceptance-green.json`, `policy-on-production-baseline.json`, `human-policy-on-production.log`, `policy-on-production-acceptance.json`, `ci-boundary-green.txt`, `ci-first-startup-failure.txt`, `ci-tls-reset-failure.txt`, `startup-timeout-triage.json` |
| `database-geo/` | `before-upgrade.json`, `upgrade-comparison.json`, `database-after-upgrade.json`, `geoserver-after-upgrade.json`, `lifecycle-results.json`, FeatureType drift evidence, `fresh-bootstrap-results.json`, `fresh-failure-wait-fixed.json`, `final-preservation.json`; pre-fix fresh evidence retained in `fresh-before-fix/` |
| `network/` | `upgraded-runtime.json`, `psa-filesystem-results.json`, `policy-off-before-connectivity.json`, `policy-on-connectivity.json`, `policy-on-repeat-connectivity.json`, `policy-on-repeat-runtime.json`, `policy-on-cni-counter-evidence.json`, `policy-on-cni-rules.txt`, `policy-off-restored-runtime.json`, `policy-off-restored-connectivity.json` |
| Evidence root | `geoportal-live-details.png` and `app-after-local-restart.png` record the rendered Geoportal and surviving application-session checks. |

Post-restart authentication evidence is in `auth/post-restart-baseline.json`,
`auth/human-post-restart.log` and `auth/post-restart-acceptance.json`.
`network/cluster-restart-diagnosis.json` records the worker IP/recovery evidence.
`network/post-restart-runtime.json` and `network/post-restart-connectivity.json`
retain the local-source restart results; `network/acceptance-summary.json`
records all 54 traffic checks across nine phases. Database/GeoServer restart proof is in
`database-geo/postrestart-preservation.json`,
`database-geo/database-after-local-restart.json`,
`database-geo/geoserver-after-local-restart.json` and
`database-geo/postrestart-wms.json`/`.png`.
The second stop/start is captured in `cluster-helper-start.log` and
`database-geo/helper-restart-preservation.json`, with corresponding
`database-after-helper-restart.json`, `geoserver-after-helper-restart.json` and
`helper-restart-wms.json` in that database directory.

Published-bundle evidence includes `github-bundle-verification.json`,
`app-published-bundle-session.png`, `auth/published-bundle-baseline.json`,
`auth/published-bundle-human.log` and `auth/published-bundle-acceptance.json`.
Network files are `package-image-identity.json`, `package-policy-on-runtime.json`,
`package-security-assertions.json`, `package-policy-on-connectivity.json`,
`package-policy-on-cni-counter-evidence.json` and
`package-psa-filesystem-results.json` under `network/`.
Database/Geo files are `ghcr-lifecycle/lifecycle-results.json`,
`published-lifecycle-preservation.json`, `database-published-bundle.json` and
`geoserver-published-bundle.json` under `database-geo/`.
Published-repeat network evidence is in `package-policy-repeat-runtime.json`,
`package-policy-repeat-connectivity.json` and
`package-repeat-preexisting-policy-proof.json`. Its cold restart is captured in
`cluster-bundle-start.log`, `network/package-cold-restart-diagnosis.json`,
`network/package-post-restart-runtime.json`,
`network/package-post-restart-connectivity.json` and
`network/package-post-restart-assertions.json`. Auth evidence is in
`auth/published-bundle-postrestart-baseline.json`,
`auth/published-bundle-postrestart-human.log` and
`auth/published-bundle-postrestart-acceptance.json`.
Its browser proof is `app-published-bundle-postrestart.png` and
`geoportal-published-bundle-postrestart.png`. Database/Geo preservation is in
`database-geo/published-postrestart-preservation.json`, with matching
`published-postrestart-database.json`, `published-postrestart-geoserver.json`
and `published-postrestart-wms.json`/`.png`.

Final restoration evidence is `deploy-final-default-local.log`,
`final-default-local-proof.json`, `app-final-default-local.png` and
`auth/final-local-baseline.json`. Network files are
`final-local-restored-runtime.json`, `final-local-restored-connectivity.json`
and `final-local-restored-assertions.json`. Database/Geo files are
`final-default-local-preservation.json`, `final-default-local-database.json`,
`final-default-local-geoserver.json` and `final-default-local-wms.json`/`.png`
under `database-geo/`.

GitNexus impact lookups for these newer report files returned UNKNOWN because
they are absent from the stale index. Source references were checked separately;
UNKNOWN was not treated as a claim that nothing depends on them. No runtime
claim above relies only on a rendered manifest or unit test.
