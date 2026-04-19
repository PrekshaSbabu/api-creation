def normalize_host_basepath(spec):
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")

    spec["_meta"] = {
        "base_url": f"https://{host}{base_path}"
    }

    return spec
