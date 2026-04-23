HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


def extract_backend_url(spec):
    """Safely extract the IBM backend target URL from known locations.

    Returns None if not found.
    """
    cfg = spec.get("x-ibm-configuration")
    if not isinstance(cfg, dict):
        return None

    assembly = cfg.get("assembly")
    if not isinstance(assembly, dict):
        return None

    execute = assembly.get("execute")
    if not execute or not isinstance(execute, list):
        return None

    first = execute[0]
    if not isinstance(first, dict):
        return None

    invoke = first.get("invoke")
    if not isinstance(invoke, dict):
        return None

    # support both 'target-url' and 'target_url'
    return invoke.get("target-url") or invoke.get("target_url")


def inject_integration(spec):
    """Inject a minimal x-amazon-apigateway-integration for each HTTP operation.

    - Only injects when a backend URL is found.
    - Only injects for known HTTP methods and when operation object is a dict.
    """
    backend_url = extract_backend_url(spec)
    if not backend_url:
        # nothing to inject; return spec unchanged
        return spec

    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return spec

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        for method, details in list(methods.items()):
            if method.lower() not in HTTP_METHODS:
                continue

            if not isinstance(details, dict):
                continue

            # Compute a sensible backend URI for this operation.
            # If backend_url already ends with the same first path segment as the
            # OpenAPI path, append only the remainder (so /customers + /customers/{id}
            # becomes /customers/{id} not /customers/customers/{id}). Otherwise append
            # the full path.
            uri = backend_url
            try:
                # path like '/customers/{id}' -> first segment 'customers'
                path_first = path.lstrip("/").split("/")[0]
                backend_last = backend_url.rstrip("/").split("/")[-1]
                if backend_last == path_first:
                    # append remainder (everything after the first segment)
                    parts = path.split("/", 2)
                    remainder = ""
                    if len(parts) >= 2:
                        remainder = path[len("/" + path_first) :]
                    uri = backend_url.rstrip("/") + remainder
                else:
                    uri = backend_url.rstrip("/") + path
            except Exception:
                uri = backend_url

            # do not overwrite an existing integration; set default if absent
            details.setdefault("x-amazon-apigateway-integration", {
                "uri": uri,
                "httpMethod": method.upper(),
                "type": "http_proxy",
                "passthroughBehavior": "when_no_match",
                # helpful defaults for AWS import/deployment
                "connectionType": "INTERNET",
                "responses": {"default": {"statusCode": "200"}},
            })

    return spec
