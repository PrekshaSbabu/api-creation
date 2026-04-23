def normalize_host_basepath(spec):
    # Prefer OpenAPI 3 'servers' if present
    servers = spec.get("servers")
    if isinstance(servers, list) and len(servers) > 0:
        first = servers[0]
        if isinstance(first, dict):
            url = first.get("url", "")
        else:
            url = str(first)

        spec.setdefault("_meta", {})["base_url"] = url
        return spec

    # Fallback to Swagger 2 'host' and 'basePath'
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")

    if host:
        spec.setdefault("_meta", {})["base_url"] = f"https://{host}{base_path}"
    else:
        spec.setdefault("_meta", {})["base_url"] = ""

    return spec
