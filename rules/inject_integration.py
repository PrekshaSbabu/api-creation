def extract_backend_url(spec):
    try:
        return spec["x-ibm-configuration"]["assembly"]["execute"][0]["invoke"]["target-url"]
    except Exception:
        return None


def inject_integration(spec):
    backend_url = extract_backend_url(spec)

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():

            if method.startswith("x-"):
                continue

            details["x-amazon-apigateway-integration"] = {
                "uri": backend_url,
                "httpMethod": method.upper(),
                "type": "http_proxy",
                "passthroughBehavior": "when_no_match"
            }

    return spec
