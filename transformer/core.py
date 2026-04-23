from rules.remove_ibm import remove_ibm_extensions
from rules.normalize import normalize_host_basepath
from rules.inject_integration import inject_integration

# optional AI integration
try:
    from utils.ai import convert_gateway_script
except Exception:
    convert_gateway_script = None

# deterministic VTL converter for trivial scripts
try:
    from transformer.vtl_converter import is_trivial_gatewayscript, convert_to_vtl
except Exception:
    is_trivial_gatewayscript = None
    convert_to_vtl = None


def transform_spec(spec):
    # extract backend FIRST
    spec = normalize_host_basepath(spec)

    # If there are assembly scripts that look like IBM gateway scripts,
    # attempt a best-effort AI conversion to an AWS-compatible snippet.
    try:
        cfg = spec.get("x-ibm-configuration", {})
        assembly = cfg.get("assembly", {})
        execute = assembly.get("execute")
        if isinstance(execute, list):
            for step in execute:
                if not isinstance(step, dict):
                    continue
                # If the step is an 'invoke' operation, it may contain inline scripts
                invoke = step.get("invoke")
                if isinstance(invoke, dict):
                    # look for keys that may contain scripts
                    script = None
                    for k in ("script", "gatewayScript", "policy"):
                        if k in invoke and isinstance(invoke[k], str):
                            script = invoke[k]
                            script_key = k
                            break

                    if script:
                        try:
                            # Try deterministic VTL conversion first (fast, auditable)
                            converted = None
                            if convert_to_vtl is not None and is_trivial_gatewayscript(script):
                                try:
                                    vtl = convert_to_vtl(script)
                                    if vtl:
                                        converted = {"type": "vtl", "content": vtl}
                                except Exception:
                                    converted = None

                            # If not converted deterministically, fall back to AI if available
                            if converted is None and convert_gateway_script:
                                ai_out = convert_gateway_script(script)
                                converted = {"type": "ai", "content": ai_out}

                            if converted is not None:
                                # store the converted script in a preserved metadata area so it
                                # survives removal of IBM-specific extensions later in the pipeline
                                meta = spec.setdefault("_meta", {})
                                conv_list = meta.setdefault("x_aws_conversions", [])
                                conv_list.append({"source_preview": script[:400], "converted": converted})
                                # also attach to the invoke for immediate inspection (may be removed later)
                                invoke["x-aws-conversion"] = converted
                        except Exception:
                            # best-effort only
                            pass

                # Some IBM assemblies place a 'gatewayscript' step directly with a 'source' field
                gw = step.get("gatewayscript")
                if isinstance(gw, dict):
                    src = gw.get("source")
                    if isinstance(src, str):
                            try:
                                converted = None
                                if convert_to_vtl is not None and is_trivial_gatewayscript(src):
                                    try:
                                        vtl = convert_to_vtl(src)
                                        if vtl:
                                            converted = {"type": "vtl", "content": vtl}
                                    except Exception:
                                        converted = None

                                if converted is None and convert_gateway_script:
                                    ai_out = convert_gateway_script(src)
                                    converted = {"type": "ai", "content": ai_out}

                                if converted is not None:
                                    meta = spec.setdefault("_meta", {})
                                    conv_list = meta.setdefault("x_aws_conversions", [])
                                    conv_list.append({"source_preview": src[:400], "converted": converted})
                                    gw["x-aws-conversion"] = converted
                            except Exception:
                                pass
    except Exception:
        # don't block the transform if AI step fails
        pass

    spec = inject_integration(spec)

    # THEN remove ibm
    spec = remove_ibm_extensions(spec)
    return spec
