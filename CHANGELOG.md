# Changelog

Released revisions are listed in
[GitHub Releases](https://github.com/Synnotech-AG/Baikor_R.Addon/releases).

## 0.4.2 — 2026-11-27

- Pin the application image and Helm chart to 0.4.2. The addon provisions a
  shared application encryption key automatically and preserves existing mail
  passwords and custom Secret references during upgrades.
- Verify the required Secret reference and key in every ready Baikor replica.
  A deployment with an unused Secret, an incompatible image or an unreadable
  saved password fails the playbook with recovery instructions.
- Report the Secret name and field if Kubernetes denies creation, and document
  how platform administrators can provide the same key through Kubernetes.

## 0.4.1 — 2026-11-27

- Pin the application image and Helm chart to 0.4.1. Baikor administrators can
  edit an active IMAP connection, test it and request a mail check from Settings.
- Simplify email import history to the ZIP filename, completion time and result.
  Settings and history remain restricted to users with the `baikor_admin` role.

## 0.4.0 — 2026-11-26

- Pin the application image and Helm chart to 0.4.0. Expired browser sessions
  now show the signed-out page, where users can sign in again through Keycloak.
- Support native IMAP imports with a dedicated create-once encryption Secret,
  shared by app instances and preserved across upgrades. Mail credentials are
  configured in Baikor; native imports require no Node-RED flow or import user.
- Document native-mail setup, key backup and migration while retaining the
  optional external import API and its default-disabled machine client.

## 0.3.2 — 2026-11-26

- Pin application/chart 0.3.2, which starts a fresh Keycloak login from the
  signed-out page and prevents stale application HTML after logout and login.
- Include the updated hints panel, which hides evaluation-status banners while
  retaining automatic detection, administrator rechecks and loading/saving errors.
- Update installation examples to the 0.3.2 release pairing.

## 0.3.1 — 2026-11-12

- Pin application/chart 0.3.1, which sizes the Baikor ingress-nginx response
  buffers for OIDC sign-in cookies and prevents callback 502 responses with
  default controller buffers.
- Document application-scoped buffer overrides and update installation examples
  to the 0.3.1 release pairing.

## 0.3.0 — 2026-11-05

- Pin the image and Helm chart to [Baikor_R 0.3.0](https://github.com/Synnotech-AG/Baikor_R/releases/tag/0.3.0).
- Update the installation guides to use the 0.3.0 release pairing.

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
