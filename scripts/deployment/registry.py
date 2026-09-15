"""Resolve each image and its credentials together. Never borrow Helm credentials for a mirror."""
import json
import re
import sys


def resolve(config, software, core, package, *, namespace, secret_name, private_source=False):
    explicit = bool(config.get("registry"))
    inherited = not explicit and config.get("inherit_core", True) and core.get("enable", False)
    overrides = any(config.get(key) for key in ("repository", "username", "password", "existing_pull_secret"))
    if overrides and not explicit:
        raise ValueError("Set registry explicitly before specifying repository, credentials or existing_pull_secret.")
    source = config["registry"] if explicit else core.get("registry_full_url", "") if inherited else software["registry"]
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*(?::[0-9]+)?(?:/[a-z0-9._/-]+)?", source):
        raise ValueError("Registry must be host[:port], with an optional Core mirror path, without a URL scheme.")
    if explicit and "/" in source:
        raise ValueError("Explicit registry must be a hostname; put its path in repository.")
    host = source.split("/")[0]
    repository = config.get("repository") or software["repository"]
    if not re.fullmatch(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*", repository):
        raise ValueError("Repository must be a lowercase path without an image tag.")
    if inherited:
        if core.get("registry_url", host) != host:
            raise ValueError("Core registry_url must match the hostname in registry_full_url.")
        username, password = core.get("registry_username", ""), core.get("registry_password", "")
    elif explicit:
        username, password = config.get("username", ""), config.get("password", "")
    elif private_source:
        username, password = package.get("username", ""), package.get("password", "")
    else:
        username, password = "", ""
    existing = config.get("existing_pull_secret", "")
    if existing and (username or password):
        raise ValueError("Use either existing_pull_secret or username/password, not both.")
    needs_auth = explicit or inherited or private_source
    if not existing and (bool(username) != bool(password) or (needs_auth and not username)):
        raise ValueError("Matching registry credentials or an existing pull Secret are required.")
    secret = existing or (config.get("image_pull_secret_name") or secret_name) if (existing or username) else ""
    return {
        "image": source + "/" + repository,
        "host": host,
        "namespace": namespace,
        "secret": secret,
        "existing": bool(existing),
        "username": username,
        "password": password,
        "tag": str(software["tag"]),
    }


def plan(data):
    addon = data["addon"]
    software = data["software"]
    result, errors = {}, []
    components = [
        ("application", addon.get("image_registry", {}), software["baikor_r"], addon["ns_name"],
         "baikor-r-image-registry", True),
    ]
    if addon["database"]["bootstrap"]["enable"]:
        components.append(("bootstrap", addon.get("bootstrap_image_registry", {}), software["postgres_client"],
                           addon["database"]["namespace"], "baikor-r-bootstrap-registry", False))
    for name, config, image, namespace, secret, private in components:
        try:
            # Locally loaded images need no package token; mirrors still need their own access.
            private = private and not addon.get("helm", {}).get("local_chart_path")
            result[name] = resolve(config, image, data.get("core_registry", {}), data.get("package", {}),
                                   namespace=namespace, secret_name=secret, private_source=private)
        except ValueError as error:
            errors.append(name + " image: " + str(error))
    return {"images": result, "errors": errors}


if __name__ == "__main__":
    print(json.dumps(plan(json.load(sys.stdin))))
