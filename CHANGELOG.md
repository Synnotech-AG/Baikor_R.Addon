# Changelog

Released revisions are listed in
[GitHub Releases](https://github.com/Synnotech-AG/Baikor_R.Addon/releases).

## Unreleased — requires application/chart 1.7.7

- Scope the browser client's tokens explicitly to the four human Baikor roles.
- Give the optional import service account its own `baikor_importer` role and
  remove the previously assigned editor role and token scope during upgrades.
- Map Core deployment names to standard ASP.NET environment names.
- Update existing managed GeoServer feature types as well as creating missing
  ones; correct the datastore-read task name.
- Document business approval and privacy review before enabling publication.
- Add regression checks for Keycloak reconciliation, environment mapping and
  GeoServer feature-type updates to CI.
- Stop the database bootstrap wait when its Job fails, and report that failure
  immediately instead of exhausting the successful-completion retry budget.

Public package publication is deferred. The importer change requires the matching
application; do not combine this revision with a 1.7.6 application image.

## Deployment and CI review — 2026-10-19

- Use the Core namespace template and verify restricted Pod Security Admission.
- Document initial database bootstrap privileges and ongoing owner-login mode.
- Verify patched Core 1.6.0 locally with `enable_gateway: false`, including
  construction-site publication to GeoServer/Masterportal.
- Add isolated database, namespace security and real bootstrap-job CI checks.
- Configure GHCR application/chart references.

This entry records source changes and test evidence, not a new addon release.
