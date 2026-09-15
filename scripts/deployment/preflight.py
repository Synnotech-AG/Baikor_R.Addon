"""Read-only deployment checks. Output contains field names, never credentials."""
import base64
import json
import re
import sys


def inspect(data):
    addon = data["addon"]
    db = addon["database"]
    bootstrap = db["bootstrap"]
    publication = addon.get("publication", {}).get("enable", False)
    generate = bootstrap.get("enable") and bootstrap.get("generate_credentials", False)
    local = db.get("local_provision", {}).get("enable", False)
    errors = list(data.get("registry_errors", []))
    requests = []
    if not addon.get("helm", {}).get("local_chart_path"):
        if not data.get("package", {}).get("username") or not data.get("package", {}).get("password"):
            errors.append("package_registry requires a GitLab username and token for the Helm chart.")
    for field in ("host", "name", "namespace", "application_secret", "migration_secret"):
        if not db.get(field):
            errors.append("database." + field + " is required.")
    if db.get("ssl_mode") not in ("VerifyFull", "VerifyCA", "Require"):
        errors.append("database.ssl_mode must be VerifyFull, VerifyCA or Require.")
    if db.get("name") and not re.fullmatch(r"[a-z][a-z0-9_]*", db["name"]):
        errors.append("database.name must use lowercase letters, digits and underscores, starting with a letter.")
    if addon.get("enable_ingress") and addon.get("enable_gateway"):
        errors.append("Choose either enable_ingress or enable_gateway, not both.")
    names = [db.get("application_secret"), db.get("migration_secret")]
    if publication:
        names.append(db.get("publication_secret"))
    if bootstrap.get("enable"):
        names.append(bootstrap.get("admin_secret"))
    if len([name for name in names if name]) != len(set(name for name in names if name)):
        errors.append("Database administrator, writer, owner and enabled publisher Secrets must be distinct.")
    if generate:
        users = [bootstrap.get("application_username"), bootstrap.get("migration_username")]
        if not all(users) or len(set(users)) != 2:
            errors.append("Generated application_username and migration_username must be nonempty and different.")

    def require(name, namespace, purpose, kind="credentials", optional=False):
        if not name or not namespace:
            errors.append(purpose + ": configure Secret name and namespace.")
        else:
            requests.append(dict(name=name, namespace=namespace, purpose=purpose, kind=kind, optional=optional))

    require(db.get("application_secret"), db.get("namespace"), "Database writer", optional=generate or local)
    require(db.get("migration_secret"), db.get("namespace"), "Database owner", optional=generate or local)
    if bootstrap.get("enable"):
        require(bootstrap.get("admin_secret"), db.get("namespace"), "Database administrator", optional=local)
    if publication:
        require(db.get("publication_secret"), db.get("namespace"), "Database publisher",
                optional=bool(bootstrap.get("enable")) or local)
    if db.get("ca_secret"):
        require(db["ca_secret"], db.get("namespace"), "Database CA", kind="ca", optional=local)
    access = data.get("access", {})
    require(access.get("secret"), access.get("namespace"), "Core Keycloak administrator", kind="keycloak")
    if publication:
        if not data.get("geoserver_enabled"):
            errors.append("Publication requires Core GeoServer to be enabled.")
        require("geoserver-geoserver", data.get("geodata_namespace"), "Core GeoServer administrator", kind="geoserver")
    portal = addon.get("publication", {}).get("masterportal", {})
    if portal.get("enable"):
        if not publication:
            errors.append("Masterportal export requires publication.enable.")
        if not str(portal.get("export_directory", "")).startswith("/"):
            errors.append("publication.masterportal.export_directory must be an absolute controller path (WSL/Linux).")
    for component, image in data.get("images", {}).items():
        if image.get("existing"):
            require(image["secret"], image["namespace"], component + " image pull", kind="registry")
            requests[-1]["host"] = image["host"]

    if "observed" in data:
        users = {}
        keys = {"credentials": ("username", "password"), "ca": ("ca.crt",),
                "keycloak": ("MASTER_USERNAME", "MASTER_PASSWORD"),
                "geoserver": ("geoserver-user", "geoserver-password"), "registry": (".dockerconfigjson",)}
        for result in data["observed"]:
            request = result.get("baikor_preflight_request", result.get("item"))
            if request is None:
                errors.append("A prerequisite Secret lookup returned no request context.")
                continue
            resources = result.get("resources", [])
            if not resources:
                if not request["optional"]:
                    errors.append(request["purpose"] + ": Secret " + request["namespace"] + "/" + request["name"] + " is missing.")
                continue
            secret = resources[0]
            try:
                decoded = {key: base64.b64decode(secret.get("data", {})[key], validate=True).decode()
                           for key in keys[request["kind"]]}
                if not all(decoded.values()):
                    raise ValueError()
                if request["kind"] == "registry":
                    if secret.get("type") != "kubernetes.io/dockerconfigjson" or request["host"] not in json.loads(decoded[".dockerconfigjson"])["auths"]:
                        raise ValueError()
                if request["kind"] == "credentials":
                    users[request["purpose"]] = decoded["username"]
            except (KeyError, ValueError, UnicodeError, TypeError):
                errors.append(request["purpose"] + ": Secret is missing required nonempty keys or contains invalid data.")
        if len(users.values()) != len(set(users.values())):
            errors.append("Database administrator, writer, owner and publisher must not share a username.")
    return {"errors": errors, "requests": requests}


if __name__ == "__main__":
    print(json.dumps(inspect(json.load(sys.stdin))))
