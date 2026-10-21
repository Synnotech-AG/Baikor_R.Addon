# Changelog

Released revisions are listed in
[GitHub Releases](https://github.com/Synnotech-AG/Baikor_R.Addon/releases).

## Unreleased

## 0.2.0 — 2026-10-21

- Restart release numbering at 0.2.0 for the addon, application image and Helm
  chart, superseding the previous 1.7.x package line.
- Pin application/chart 0.2.0 and align the README and Windows / Core 1.6
  first-install guide. Preserve earlier release evidence as historical records.

## 1.7.10 — 2026-10-21

- Pin application/chart 1.7.9 and align the Windows / Core 1.6 first-install
  guide and registry examples with the addon 1.7.10 release pairing.

## 1.7.9 — 2026-10-21

- Pin application/chart 1.7.8 for public GHCR installation.
- Add a complete Windows 11 / WSL2 / Core 1.6 first-install guide using the
  public application image and OCI chart, with explicit Core patches, TLS,
  database-owner transition and restart checks.
- Allow ten minutes for database bootstrap, including uncached image downloads,
  and align controller polling with that deadline. Report failed Job conditions
  immediately even when no failed Pod count is available.
- Provision the optional import client directly with importer-only permissions;
  remove the obsolete editor-role transition for pre-release installations.
- Test fresh Keycloak provisioning, optional importer activation and repeated
  deployment with stable credentials instead of seeding a legacy client.
- Run addon CI against Core 1.6.0, matching the supported ingress deployment.
- Address installation guidance to platform operators without customer-specific
  provisioning assumptions.

## 1.7.8 — 2026-10-20

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
- Record public source and package availability, verified with anonymous Docker
  and Helm downloads on 2026-10-20, and the decision to keep MDH on Core 1.6.

The importer change requires application/chart 1.7.7; do not combine this revision
with a 1.7.6 application image. Addon release numbers are independent of application
versions. The existing addon 1.7.7 tag is an older revision and remains unchanged.

## Deployment and CI review — 2026-10-19

- Use the Core namespace template and verify restricted Pod Security Admission.
- Document initial database bootstrap privileges and ongoing owner-login mode.
- Verify patched Core 1.6.0 locally with `enable_gateway: false`, including
  construction-site publication to GeoServer/Masterportal.
- Add isolated database, namespace security and real bootstrap-job CI checks.
- Configure GHCR application/chart references.

This entry records source changes and test evidence, not a new addon release.
