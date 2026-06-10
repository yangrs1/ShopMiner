import os
import re
import yaml
from tests.utils.faker_data import resolve_faker


_YAML_CACHE = {}

YAML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "yaml")


def load_yaml(module_name, use_cache=True):
    path = os.path.join(YAML_DIR, f"{module_name}.yaml")
    if use_cache and path in _YAML_CACHE:
        return _YAML_CACHE[path]

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    data = _resolve_all_faker(raw)
    if use_cache:
        _YAML_CACHE[path] = data
    return data


def _resolve_all_faker(obj):
    if isinstance(obj, str):
        return resolve_faker(obj)
    if isinstance(obj, dict):
        return {k: _resolve_all_faker(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_all_faker(item) for item in obj]
    return obj
