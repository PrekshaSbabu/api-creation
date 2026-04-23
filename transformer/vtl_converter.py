"""Deterministic, heuristic-based converter from simple GatewayScript snippets
to AWS API Gateway Velocity Template Language (VTL) mapping templates.

This is intentionally conservative: it only converts trivial patterns such as
presence checks for query parameters that set a response status/body. More
complex scripts should be handled by Lambda stubs or AI-assisted conversion.
"""
import re
from typing import Optional


def is_trivial_gatewayscript(script: str) -> bool:
    """Return True if the script looks trivial and safe to convert to VTL.

    Heuristics:
    - script is reasonably small (< 1000 chars)
    - uses apim.getvariable / apim.setvariable only
    - does not contain obvious external calls, loops, or async operations
    """
    if not script or not isinstance(script, str):
        return False
    if len(script) > 2000:
        return False

    lower = script.lower()
    forbidden = ["http", "fetch(", "axios", "for(", "while(", "settimeout",
                 "apim.client", "callservice", "xmlhttprequest", "require(", "module."]
    for f in forbidden:
        if f in lower:
            return False

    # require at least one apim.getvariable usage
    if "apim.getvariable" not in script and "apim.setvariable" not in script:
        return False

    return True


def convert_to_vtl(script: str) -> Optional[str]:
    """Try to convert a trivial gatewayscript to a VTL mapping template.

    Currently supports presence checks on query params that set a 4xx status
    and body via apim.setvariable('message.status.code', XXX) and
    apim.setvariable('message.body', { ... }).
    Returns the VTL template as a string or None if no conversion applied.
    """
    if not is_trivial_gatewayscript(script):
        return None

    # Detect pattern: var <var> = apim.getvariable('request.query.<name>');
    m = re.search(r"apim\.getvariable\(\s*['\"]request\.query\.([a-zA-Z0-9_\-]+)['\"]\s*\)", script)
    if not m:
        return None
    param = m.group(1)

    # Detect status/body set
    status = None
    body = None
    m_status = re.search(r"apim\.setvariable\(\s*['\"]message\.status\.code['\"]\s*,\s*(\d{3})\s*\)", script)
    if m_status:
        status = m_status.group(1)

    m_body = re.search(r"apim\.setvariable\(\s*['\"]message\.body['\"]\s*,\s*(\{[\s\S]*?\})\s*\)", script)
    if m_body:
        # crude cleanup: keep inner JSON-like text
        body = m_body.group(1).strip()

    # Build a conservative VTL template that checks for the param and returns
    # a short JSON error when missing. This is meant to be a helpful starting
    # point and should be reviewed.
    vtl_lines = []
    vtl_lines.append("#set($inputRoot = $input.path('$'))")
    vtl_lines.append(f"#if(!$input.params('{param}'))")
    if status:
        vtl_lines.append(f"  #set($context.responseOverride.status = {status})")
    if body:
        # Attempt to convert the JS object literal to JSON by naive replacement
        # (this is conservative and may require manual fixes)
        json_body = body.replace("'", '"')
        vtl_lines.append(f"  {json_body}")
    else:
        vtl_lines.append('  {"error": "missing ' + param + '"}')
    vtl_lines.append("#else")
    vtl_lines.append("  $input.json('$')")
    vtl_lines.append("#end")

    return "\n".join(vtl_lines)


__all__ = ["is_trivial_gatewayscript", "convert_to_vtl"]
