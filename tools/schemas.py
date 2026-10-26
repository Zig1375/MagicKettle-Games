"""The JSON Schemas in schema/, ready to validate module files.

The schemas hold only the shape of a module. What is allowed beyond it (registry branches, file types, component
names, one module per match key) is checked by tools/check, which runs these validators first.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
KINDS = {"modules": "module.schema.json", "shared": "shared.schema.json"}


def _load(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _registry():
    # The shared schema refers to the module schema's definitions by its $id; resolve it from disk, never the network.
    resources = []
    for name in KINDS.values():
        schema = _load(name)
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def validator(kind):
    """A validator for a file in modules/ ("modules") or shared/ ("shared")."""
    schema = _load(KINDS[kind])
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


def errors(kind, module):
    """Every way `module` breaks its schema, as "path: message" lines, sorted for stable output."""
    found = []
    for error in validator(kind).iter_errors(module):
        path = "/".join(str(part) for part in error.absolute_path) or "(root)"
        found.append(f"{path}: {error.message}")
    return sorted(found)
