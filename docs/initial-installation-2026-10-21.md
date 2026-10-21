# Fresh Core 1.6 installation — 2026-10-21

Status: **working-tree verification complete**. Fresh installation, owner repeat, NetworkPolicy enforcement, cold restart and original-environment restoration passed.
The adapted local Core profile is not a new release.

## Source and image identity

- Application base HEAD: `fce5cfcde669ef026b71dc5e8ca6b3df0546256d`, with current setup and namespace changes.
- Addon base HEAD: `b1b0c7d009df0b3f2206be872a7e8c0b9a3fb63d`, with current setup and bootstrap-deadline changes.
- Core v1.6.0: `86e69334800ce96bb2731782d2c1a9de9c5a9e91`; the selected local Keycloak/platform adaptations are recorded in `core-source-profile.json`.
- Tested image: `baikor-r:initial-installation-namespaces-20261021`.
- Image index digest: `sha256:4178818a12f62cff53e160ee97c229979e8b8805a381e16e8c58c4d34977b71e`.
- Platform manifest: `sha256:b60e548060e493458cb5afd0c7dab678385f4c4d2feb38321f70084c35fd3bed`.
- Running image configuration: `sha256:521e09dc8c7b151cf1eceb744f4f076fff5c0e7bcbd90a9f9a41312f6f638a2f`.
- Build-input SHA-256: `3f6e2337bb1909e43dd8d76b0c6fc78e0f482be23ce1311f8c282afb4ad29e3f`; inputs remained stable through the namespace verification run.

## Direct first setup

Initial schema setup preserves pre-baseline tables and the EF migration chain.
The optional import client receives `baikor_importer` directly; obsolete editor-role
transition tasks and Node-RED upgrade guidance were removed. Fresh browser-client setup, importer activation and repeats preserve identities and credentials.
Owner-mode grant and GeoServer reconciliation remain.

The new Core profile had new node/PVC identities and no copied database, realm or PVC data.
Before the addon, all **43 active Pods** were ready and the Baikor database, roles, clients and namespace were absent. After installation, all
**44 active Pods** and all three nodes were ready; the running image chain matched.

| Executed check | Result |
| --- | --- |
| Backend Release tests | **105 passed**, zero failures/skips |
| Isolated PostGIS / human / importer suites | **5 / 77 / 24 passed** on the latest namespace image |
| Addon unit suite / Core 1.6 Ansible lint | **48 passed** / **46 files**, zero rule failures or warnings |
| Full fresh Core human / import / publication suites | **77 / 70 / 211 passed** |
| Runtime assertions / PSA and filesystem / initial network baseline | **40 / 5 / 6 passed** |

## Cold-start failure, correction and first-database proof

The first uncached PostgreSQL client image pull took **226.581 seconds**, exceeding the old **180-second** Job deadline. SQL briefly ran before termination and left
one database and three roles; this was not a failure before database creation.
The fix allows **600 seconds** for the whole Job and **660 seconds** of controller
polling, with immediate failed-Pod, `Failed` and `FailureTarget` detection.
Normal addon recovery retained all **five credential/CA Secrets** unchanged.

A separate actual-Ansible fixture injected a **200-second init delay**. At **183.261 seconds**,
the Job was active with zero databases and roles. It subsequently created one database, PostGIS, the schema and three
unprivileged login roles successfully with `verify-full`; the fixture was cleaned. This proves delayed first creation separately from partial-setup recovery.

## Owner repeat and preservation

After removal of the temporary bootstrap-admin Secret, owner deployment passed:
`ok=112 changed=5 unreachable=0 failed=0`. All **seven** database/data/grant,
Secret and PVC comparisons and **14 Keycloak identity/permission comparisons** passed.
Strict GeoServer JSON equality remains **false**: only `encodeMeasures` and
`simpleConversionEnabled` changed from absent to `false` on both managed types.
GeoServer 2.28.0 getter semantics confirm equivalent false defaults; there were
no other differences. This bounded finding does not excuse arbitrary metadata drift.

Enabled NetworkPolicy owner repeat passed (`ok=112 changed=5 failed=0`), with **40 runtime + 6 network checks** and **eight strict preservation comparisons**.
Denied probes increased the CNI REJECT counter by **three packets**.

## Cold restart and restoration

All **three nodes and 44 Pods** restarted with new container starts and became
ready in **146.4 seconds**, without manual repair or redeployment. Post-restart
**77 human, 70 import, 40 runtime and 6 network checks** passed; denied probes
added **three CNI REJECT packets**. All **eight strict preservation** and **14 Keycloak**
comparisons passed. The same cookie session (**14 checks**) and **64 KiB attachment**
(**19 checks**, including cleanup) survived. Test-owned users and records were cleaned.
HTTPS used the fresh CA. No new browser UI acceptance or Windows OS reboot is claimed.
Original environment restored: **three nodes / 36 Pods ready**, all Pod containers restarted;
**10 PVCs, 98 Secrets, node identities and configuration hashes** remained unchanged.
All **20 original auth/API checks** passed, including the same three site IDs and import-only denial.
The fresh cluster is stopped and retained; only the original profile is active. Its existing kubelet certificate IP SAN mismatch blocks `kubectl exec`.
Read-only Docker→CRI SQL matched **all six sections** (roles, objects, default ACLs, sites, table hashes, migration history), including **five table hashes and three sites**,
against **2026-10-20 08:34:43 UTC** evidence, a historical baseline not captured immediately before this test.
No TLS bypass or repair was used. The expected image and HTTPS health/frontend/OIDC statuses (**200/302/200**) passed.

Ignored evidence: application `artifacts/first-install-20261021/`, including source/image and Core readiness records, bootstrap failure/recovery, `delay-fixture/result.json`,
`validation/`, restart/restoration and `acceptance/` records. GeoServer's bounded comparison is in `acceptance/database-geo/feature-type-repeat-analysis.json`.
Private inventories/logs are not published; historical release evidence is unchanged.
