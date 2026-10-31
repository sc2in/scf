"""Draft-07 JSON Schemas for every generated artifact."""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

import jsonschema

CATALOG_RE = re.compile(r"scf-\d{4}(?:-\d+)+\.json$")

_FILE_SCHEMAS = {
    "scf-assessment-objectives.json": "assessment-objectives.schema.json",
    "scf-compensating-controls.json": "compensating-controls.schema.json",
    "scf-crosswalks.json": "crosswalks.schema.json",
    "scf-evidence-requests.json": "evidence-requests.schema.json",
    "scf-legacy-map.json": "legacy-map.schema.json",
    "scf-privacy-principles.json": "privacy-principles.schema.json",
    "scf-risks.json": "risks.schema.json",
    "scf-threats.json": "threats.schema.json",
}


def load_schema(name: str) -> dict:
    text = resources.files(__package__).joinpath(name).read_text(encoding="utf-8")
    return json.loads(text)


def schema_for(filename: str) -> dict | None:
    if CATALOG_RE.match(filename):
        return load_schema("catalog.schema.json")
    if filename in _FILE_SCHEMAS:
        return load_schema(_FILE_SCHEMAS[filename])
    return None


def validate_schemas(data_dir: Path) -> list[str]:
    """Validate every recognized data file; returns human-readable errors."""
    errors: list[str] = []
    for path in sorted(Path(data_dir).glob("*.json")):
        schema = schema_for(path.name)
        if schema is None:
            continue
        instance = json.loads(path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for err in validator.iter_errors(instance):
            where = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{path.name}:{where}: {err.message[:200]}")
    return errors


def validate_overrides_file(path: Path) -> list[str]:
    schema = load_schema("overrides.schema.json")
    instance = json.loads(Path(path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    return [err.message for err in validator.iter_errors(instance)]
