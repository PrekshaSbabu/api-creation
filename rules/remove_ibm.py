def remove_ibm_extensions(obj):
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            # only string keys can startwith; keep non-string keys as-is
            if isinstance(k, str) and k.startswith("x-ibm-"):
                continue
            new[k] = remove_ibm_extensions(v)
        return new
    elif isinstance(obj, list):
        return [remove_ibm_extensions(i) for i in obj]
    return obj
