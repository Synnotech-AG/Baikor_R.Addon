# Public-release runtime review — 2026-10-20

Status: **complete**. Public releases, anonymous artifact retrieval, the
initial local cold reset, direct public-release deployment, owner repeat,
actual Helm upgrade and second cold restart have passed.
Initial acceptance passed **77 human checks, 70 import checks and 211 publication
checks**, plus runtime, network and database checks below. The full human/import
checks passed again after the public-release cold restart. The original local
image/profile has been restored and verified, with existing data and credentials
preserved. Test-induced login throttling during cleanup and one unexplained
browser search timeout are retained explicitly below.
These are new tests of the direct public download path, separate from the
October 19 authenticated-bundle evidence.

## Release identity

| Component | Verified identity |
| --- | --- |
| Application release | [1.7.7](https://github.com/Synnotech-AG/Baikor_R/releases/tag/1.7.7), source `6afbbaed75f4c201c584d88eaee1e196b15a2720` |
| Application image | `ghcr.io/synnotech-ag/baikor-r:1.7.7`, digest `sha256:6e9f2824b4774496783b96d6e8ef5ccfb00006c8afaa71280d2d8b3079d1a0be` |
| Helm chart | `oci://ghcr.io/synnotech-ag/baikor-r-chart`, version `1.7.7`, manifest digest `sha256:f1ffdc39cec1ea63e6d6d2fb680a180fd3acf7b5646ba7d2147701ad5b73f691` |
| Chart archive SHA256 | `c5eff82e139ba92e4ad916b181bc174238fd2d59a04c4b4f6517129ec3b4324f` |
| Addon release | [1.7.8](https://github.com/Synnotech-AG/Baikor_R.Addon/releases/tag/1.7.8), tag commit `050ce2ea7c0856395bb02cfed50007ac9cd182d0` |

The application release recovered original workflow run
[39239993018](https://github.com/Synnotech-AG/Baikor_R/actions/runs/39239993018),
attempt 2, after package visibility was changed to public. The original package
bytes and digests were retained. Anonymous release-asset downloads matched the
published checksums. Anonymous Docker and Helm downloads used empty credential
configurations; Kubernetes also pulled the application image without
`imagePullSecrets` during preflight.

The addon tag and release were verified anonymously after all four
[Validate jobs](https://github.com/Synnotech-AG/Baikor_R.Addon/actions/runs/39390324015)
passed at the released revision. Addon 1.7.8 and application/chart 1.7.7 are the
intended pair; the older addon 1.7.7 tag was not moved.

## Test environment and scope

The test targets local cluster `civitas-local-160`, Kubernetes context
`k3d-civitas-local-160`, using Core 1.6.0 with `enable_gateway: false`.
The [Core baseline report](core-1.6.0-deployment-review.md) documents the local
Keycloak and image adjustments. MDH remains on Core 1.6; the local test is not an
exact replica of its infrastructure.
The restart tests stopped and started the local k3d cluster; they were not a
Windows host reboot or a claim that every infrastructure startup race is fixed.

The reset stopped and restarted the existing cluster while retaining its data.
It reached **3/3 Ready nodes and 36/36 Ready active Pods in 152.5 seconds**.
The existing application browser session remained usable after that reset and
the public-image rollout.

The alternate test inventory uses the public OCI chart and image, with no local
chart or authenticated bundle. The original owner inventory remains unchanged.
Both `HELM_REGISTRY_CONFIG` and `DOCKER_CONFIG` point to dedicated empty credential
locations on the controller. The application image uses `imagePullPolicy: Always`;
its running digest and the installed chart templates were checked against the
published artifacts. The test profile uses **Production**, authentication enabled,
certificate-validation bypass disabled and application NetworkPolicy enabled.

The actual addon tasks deployed Helm revision **18** successfully:
`ok=115 changed=5 unreachable=0 failed=0 skipped=20`. Runtime verification found
the installed templates byte-identical to the released chart. The addon runtime
files used for the isolated bootstrap test also matched released tag 1.7.8.

## Acceptance results

| Area | Current result |
| --- | --- |
| Public package and release retrieval | Passed; exact identities are recorded above. |
| Local environment reset and published addon deployment | Initial cold reset ready after 152.5 seconds; direct public OCI/image deployment passed at Helm revision 18. |
| Authentication, roles, sessions and application workflows | **77/77** human checks passed. Real browser session survives the initial reset and rollout; temporary users and owned fixtures were cleaned. |
| Import API and importer-only permissions | **70/70** checks passed through HTTPS ingress, including valid imports, documented boundaries, validation/duplicate errors and importer rejection from general application operations. |
| PostgreSQL owner/writer/publisher privileges and TLS | Actual sessions use `VerifyFull`; role separation and owner-mode deployment pass. Wrong-host/untrusted-CA controls are rejected and the temporary admin Secret is absent. Six isolated first-bootstrap/owner/failure-recovery phases passed; fixtures removed. |
| GeoServer/Geoportal publication and private-data exclusion | **211/211** lifecycle checks passed with the synthetic fixture removed. Actual GeoServer JNDI uses Publisher/CA/`VerifyFull`; anonymous WFS/WMS, rendered Geoportal search, polygon selection and feature information were verified. |
| Namespace PSA, container security and resource limits | **55/55** runtime assertions passed. PSA rejects root/privileged Pods and accepts the valid control; read-only root, allowed temporary/PVC writes, actual resources and released artifact identities pass. |
| Application NetworkPolicy | **6/6** connectivity checks passed initially, **6/6** after the owner repeat and **6/6** after the public cold restart. Each phase's forbidden probe generated three additional CNI reject-counter packets. A new migration also completed during a real Helm upgrade with the existing policy still present. |
| Retained original data and credentials | All **10** preservation comparisons passed after publication, after the owner repeat, after the public cold restart and after final local restoration: three original sites, five table hashes, roles/objects/default ACLs/migrations, Secret identities/data, PVC identities and FeatureType metadata. |
| Repeat owner deployment and FeatureType drift repair | Repeat passed: `ok=115 changed=4 unreachable=0 failed=0`. Managed title/abstract drift on both existing FeatureTypes was repaired by the addon. **55/55** runtime assertions passed; an unchanged Helm release correctly remained at revision 18. |
| Actual Helm upgrade with existing NetworkPolicy | A harmless Pod annotation forced the Core Helm upgrade path: `ok=115 changed=5 unreachable=0 failed=0`, revision **19**, **55/55** runtime assertions. A new migration succeeded while the pre-existing NetworkPolicy kept its identity. |
| Second cold restart and post-restart acceptance | Ready after **137.1 seconds**, 3/3 nodes and 36/36 active Pods, with no redeployment or role repair before checks. **77 human + 70 import**, **34 live-runtime assertions**, **six network probes** and actual DB/GeoServer verification passed. Retained operator session: **14/14**. Attachment/content persistence: **14 passed**, followed by a cleanup error; separate owned-fixture cleanup passed **11/11**. See the observations below. |
| Final local-image restoration | Normal owner inventory, no overrides: `ok=115 changed=5 unreachable=0 failed=0`, Helm revision **20**. Local image/chart, Staging and optional NetworkPolicy off restored; **40/40** runtime assertions, **6/6** network probes, **7/7** targeted auth checks and all **10** preservation comparisons passed. Existing browser session, Create action and three original sites remain available. |

## Isolated first deployment and owner mode

The A2 test used the actual released addon tasks against an isolated database
and credential namespace on the operator-style PostgreSQL server. The bootstrap
client was pinned to `docker.io/library/postgres:15.18-bookworm`.

| Phase | Result |
| --- | --- |
| Initial administrator bootstrap | Database, three roles, schema, PostGIS and grants created successfully. |
| Owner-only repeat 1 | Passed after deleting the temporary bootstrap-admin Secret. |
| Owner-only repeat 2 | Passed; the fixture row and credential hashes were preserved. |
| Wrong CA | Rejected as expected: playbook exit 2 and terminal failed Job. |
| Privileged publisher | Rejected as expected: playbook exit 2 and terminal failed Job. |
| Owner recovery | Passed after restoring the valid configuration; retained row and credentials verified. |

Failure detection took 0.233 seconds for the wrong-CA case and 3.639 seconds for
the privileged-publisher case after terminal Job failure. These deliberate
rejections demonstrate the guards; they are not failed acceptance results.
Cleanup independently confirmed that the isolated namespace, database and all
three fixture roles were absent.

## Repeat deployment, drift repair and upgrade

Deliberate title and abstract changes were applied to both existing managed
GeoServer FeatureTypes. The normal owner deployment restored their expected
values and retained the unrelated owned metadata, without manual restoration.
The application data, grants, credentials, PVCs and FeatureType metadata passed
all ten preservation comparisons after this deployment.

Because the Helm values had not changed, Helm correctly kept revision 18 and
the already completed migration Job. An initial test assertion incorrectly
expected every Ansible deployment to create a new migration Job. This harness
assumption is retained in `public-repeat-policy-migration-assessment.json`;
it is not an application failure or proof of a new migration.

A separate test then changed only a harmless Pod annotation through the normal
Core public-release inventory. This produced a real Helm upgrade to revision 19.
All three upgrade-specific assertions passed: the NetworkPolicy UID was
unchanged, a new migration Job succeeded, and the policy existed before that
Job started. The runtime files still match released addon tag 1.7.8.

Before the second cold restart, the authentication test prepared a retained
synthetic record with a **65,536-byte attachment** and an existing session.
All five local k3d containers were confirmed stopped. The cluster returned on
the first k3d start attempt and became ready after 137.1 seconds, preserving all
three node identities and ten PVC identities. No addon redeployment or role
patch preceded the post-restart checks.

The public application still used Helm revision 19 and the published image.
Completed Job Pods had been collected by then, so post-restart runtime checks
cover **34 live-application/release assertions**; they do not claim a new
inspection of terminated migration processes. The previously recorded successful
upgrade migration remains the migration evidence.

The existing operator session passed all 14 continuity checks. The retained
synthetic session, site and attachment passed 14 checks, including byte length
and SHA256 content equality. The script then hit a JSON decoding error during
cleanup and recorded one failure; that original result is retained. A separate
fresh operator session subsequently passed all 11 ownership-checked cleanup
steps, and final housekeeping confirmed zero remaining owned test users/sites
and exactly the three original sites.

Actual post-restart Owner, Writer and Publisher connections again passed
`VerifyFull`, least-privilege and negative TLS checks. GeoServer still used the
Publisher identity, operator CA and `VerifyFull`. Stable anonymous publication
after fixture cleanup is **two sites and three areas**. An earlier three-site/
four-area sample included a temporary authentication fixture; it is not the
preserved original-data baseline.

## Restart observations retained for follow-up

- The attachment script's final cleanup attempt returned a response it could
  not decode as JSON. Persistence/session checks had already passed and the
  subsequent ownership-checked cleanup succeeded. Two test helpers overlapped
  operator login flows. The matching Keycloak event is
  `LOGIN_ERROR / user_temporarily_disabled`; the realm has brute-force protection
  with a 1,000 ms quick-login window and a 60-second minimum wait. The ingress
  timeline shows a redirect to a login page instead of the expected JSON
  response. This evidence supports test-induced login throttling. Roles and
  realm security settings were not changed, and no application fix is claimed.
- The first rendered Geoportal search wait timed out after restart. Retrying
  the same query displayed the expected site, polygon and feature information
  without configuration changes. Direct exact/contains XML title searches both
  returned HTTP 200 without GeoServer exceptions. This one transient browser
  observation remains unexplained; the retry is not presented as a fix.
  A second known published site's search passed on its first controlled attempt
  with separate input and submit steps, without a page reload or code change.
- The local worker-IP startup race recorded on October 19 is still an
  infrastructure follow-up. The two successful resets here do not establish
  that its underlying cause has been eliminated.

## Final local-image restoration

The normal deployment helper ran with the original owner inventory and no
command-line value overrides. It restored Helm revision **20**, local image
`baikor-r:review-1.7.7-6afbbae`, the local chart, **Staging**, and the optional
application NetworkPolicy disabled. Authentication remains enabled and
certificate validation remains enforced. The harmless public-upgrade test
annotation was removed.

All **40 runtime/profile assertions** and **six connectivity probes** passed.
Targeted authentication checks passed **7/7**: operator login/session and four
human roles; browser `fullScopeAllowed: false` with four explicit human scopes;
and importer-only assignment, scope and token/audience. These final targeted
checks are separate from the two earlier full **77 + 70** suites.

Actual Owner/Writer/Publisher TLS sessions, least privileges, owner bootstrap
without the temporary admin Secret and the Writer runtime identity passed
again. GeoServer's JNDI Publisher connection retained the operator CA and
`VerifyFull`; anonymous publication contains the original **two sites and three
areas**. All ten database/credential/PVC/FeatureType preservation comparisons
matched the original baseline.

All **36 active Pods** are Ready and all **ten PVC identities** are unchanged.
Byte comparisons against the locally encrypted backups confirmed that both
original owner and software inventories remained unchanged. The existing
browser session still shows the three original construction sites with Create
enabled. Test users, owned test records, temporary database/bootstrap fixtures
and test processes were cleaned up; the addon-managed importer was preserved.

## Test setup corrections

Two controller invocations needed correction before the successful deployment.
Neither required an application or addon source change:

1. Passing `inv_addons` with Ansible `-e` overrode Core's default-merging
   `set_fact`, leaving required defaults such as `enable` unavailable. That
   attempt stopped before cluster mutations. The corrected invocation uses the
   ordinary alternate inventory through `BAIKOR_CORE160_INVENTORY`.
2. An empty `HELM_REGISTRY_CONFIG` alone did not isolate registry credentials:
   WSL Helm fell back to the saved Docker `credsStore` helper `desktop.exe` and
   failed. A dedicated empty `DOCKER_CONFIG` resolved the fallback. Existing
   saved credentials and helper settings were preserved; anonymous `helm show
   chart` and the subsequent deployment passed.

## Evidence and remaining responsibilities

Sanitized local evidence is collected under the application's ignored
`artifacts/runtime-review-20261020/` directory. Release graph checks, documentation
link checks and exact-commit hosted CI summaries are in its `release/` subdirectory.
Raw credentials, tokens and database contents must not be included in this report.

Evidence for the completed phases includes:

- `cluster-initial-start.log` and `deploy-public-anonymous.log`;
- `deployment-invocation-correction.json` and
  `controller-registry-correction.json`;
- `network/public-initial-assertions.json`,
  `public-initial-connectivity.json`, `public-initial-cni-counter-evidence.json`
  and `psa-filesystem-results.json` in the same subdirectory;
- `auth/public-human.log` and `auth/public-acceptance.json`;
- `database-geo/database-public-release.json`, `fresh-bootstrap-results.json`,
  `lifecycle-results.json` and `preservation-after-public-lifecycle.json`;
- `database-geo/featuretype-drift-verify.json` and
  `preservation-after-public-repeat.json`;
- `network/public-repeat-assertions.json`, `public-repeat-connectivity.json`,
  `public-repeat-cni-counter-evidence.json`,
  `public-repeat-policy-migration-assessment.json`, `public-upgrade-assertions.json`
  and `public-upgrade-policy-migration.json`;
- `release/addon-runtime-identity.json`, `deploy-public-upgrade.log` and
  `cluster-public-stopped.txt`;
- `cluster-public-start.log`, `network/public-restart-assertions.json`,
  `network/public-restart-connectivity.json` and
  `network/public-restart-cni-counter-evidence.json`;
- `auth/public-postrestart-human.log`, `public-postrestart-acceptance.json`,
  `restart-session-results.json`, `restart-attachment-results.json`,
  `restart-attachment-cleanup.json`, `restart-cleanup-ingress-timeline.json`,
  `restart-cleanup-keycloak-events.json`, `restart-cleanup-throttle-diagnosis.json`
  and `final-housekeeping.json`
  in the auth subdirectory;
- `database-geo/database-public-postrestart.json`,
  `geoserver-public-postrestart.json`, `geoserver-postrestart-search.json` and
  `preservation-after-public-postrestart.json`;
- `browser/public-geoportal.png` and `browser/public-restart-portal.json` for the
  rendered Geoportal checks and the retained initial search delay;
- `deploy-local-restored.log`, `final-cluster-preservation.json` and
  `original-inventory-preservation.json`;
- `network/local-restored-assertions.json` and
  `network/local-restored-connectivity.json`;
- `auth/final-local-baseline.json`, `auth/final-housekeeping.json` and
  `auth/acceptance-summary.json`;
- `database-geo/database-final-local-restored.json`,
  `database-geo/geoserver-final-local-restored.json` and
  `database-geo/preservation-final-local-restored.json`;
- `browser/local-restored-browser.json` for the retained browser session.

The [October 19 runtime report](runtime-review-2026-10-19.md) remains the record of
the earlier local-image and authenticated-bundle phases. The
[review status](REVIEW_STATUS.md) maps the current evidence to A1–C8.

Business approval and the privacy review of real public free-text fields remain
the data owner/operator's responsibility before real-data publication (C7).
