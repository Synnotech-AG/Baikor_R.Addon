# Initial installation plan

**Goal:** Provision a new CIVITAS Core 1.6 installation directly in its intended secure state, without obsolete pre-release upgrade cleanup.

**Scope:** Remove the import client's editor-role transition and the application's obsolete pre-baseline schema/history reset. Preserve normal EF schema creation, repeat deployment, owner operation, operator configuration and existing user data. Existing public release tags remain unchanged.

## Implementation and verification

- [x] Replace legacy importer request assertions with direct importer-only provisioning checks; observe failure before removing the obsolete tasks.
- [x] Exercise actual Keycloak tasks from an empty realm: imports disabled, enabled, then repeated. Verify role scopes, issued tokens and stable client credentials.
- [x] Prove the initial application schema preserves a bootstrap-created marker in a real PostGIS database; remove the historical reset and run the complete isolated platform suite.
- [x] Update current installation guidance, CI labels and changelogs. Preserve historical release/test records as historical evidence.
- [x] Run addon unit/integration checks, application checks and Core 1.6 lint/integration validation.
- [x] Provision a separate full Core 1.6 cluster with fresh volumes, database, Keycloak realm and CA. Retain the previous cluster and its data.
- [x] Deploy the modified addon/application; verify bootstrap-to-owner operation, denied importer APIs, human-role workflows, public/private Geoportal behavior, PSA and optional network enforcement.
- [x] Correct the observed uncached-image bootstrap deadline failure; verify bounded polling, immediate terminal failure and actual delayed creation from an empty database.
- [x] Repeat deployment and cold restart; verify retained records, roles, credentials, sessions and attachments.
- [x] Restore and verify the prior local environment's readiness, configuration, identities and authentication.
- [x] Obtain an independent source review of the final changes; no findings reported.
- [x] Complete the read-only historical database comparison and finalize exact tested revisions/images, outcomes and limitations; all six database sections match the October 20 baseline.

## Boundaries to test

- A fresh importer must never receive editor rights or require old grants to exist.
- Repeating setup must not rotate secrets or revoke valid human access.
- Fresh schema creation must not drop an existing bootstrap schema or unrelated objects.
- GeoServer must expose only eligible sanitized views; machine clients must not delete records.
- A new cluster must not read or mutate the retained cluster's state; every operation uses its explicit kubeconfig/context.
