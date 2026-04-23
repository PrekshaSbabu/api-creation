import os
import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    # ensure parent directory exists
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        # use safe_dump with readable formatting and stable key order disabled
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
