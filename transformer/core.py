from .rules.remove_ibm import remove_ibm_extensions
from .rules.normalize import normalize_host_basepath
from .rules.inject_integration import inject_integration

def transform_spec(spec):
    spec = remove_ibm_extensions(spec)
    spec = normalize_host_basepath(spec)
    spec = inject_integration(spec)
    return spec
