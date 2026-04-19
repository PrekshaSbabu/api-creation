def remove_ibm_extensions(obj):
    if isinstance(obj, dict):
        return {
            k: remove_ibm_extensions(v)
            for k, v in obj.items()
            if not k.startswith("x-ibm-")
        }
    elif isinstance(obj, list):
        return [remove_ibm_extensions(i) for i in obj]
    return obj
