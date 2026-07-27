#!/usr/bin/env python3
"""Validate the ACOS enterprise domain registry against its JSON Schema."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config/domains/registry.yaml"
SCHEMA_PATH = ROOT / "schemas/domain-registry.schema.json"
DOMAIN_ID_PATTERN = re.compile(r"^DOM-(COM|INT|GOV|PLT)-[A-Z]{3}-\d{3}$")


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    failures: list[str] = []

    for path in (REGISTRY_PATH, SCHEMA_PATH):
        if not path.is_file():
            failures.append(f"Required domain architecture artifact is missing: {path.relative_to(ROOT)}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    registry = load_yaml(REGISTRY_PATH)
    schema = load_json(SCHEMA_PATH)

    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema, format_checker=jsonschema.FormatChecker())
    schema_errors = sorted(
        validator.iter_errors(registry),
        key=lambda error: [str(part) for part in error.absolute_path],
    )

    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        failures.append(f"{location}: {error.message}")

    domains = registry.get("domains", []) if isinstance(registry, dict) else []
    identifiers = [domain.get("id") for domain in domains if isinstance(domain, dict)]

    for identifier, count in Counter(identifiers).items():
        if count > 1:
            failures.append(f"Duplicate domain ID: {identifier}")

    for identifier in identifiers:
        if not isinstance(identifier, str) or not DOMAIN_ID_PATTERN.fullmatch(identifier):
            failures.append(f"Invalid domain ID: {identifier!r}")

    bounded_contexts = [domain.get("bounded_context") for domain in domains if isinstance(domain, dict)]
    for bounded_context, count in Counter(bounded_contexts).items():
        if count > 1:
            failures.append(f"Duplicate bounded context: {bounded_context}")

    for domain in domains:
        if not isinstance(domain, dict):
            continue
        domain_id = domain.get("id", "<missing-id>")
        for field in (
            "owned_capabilities",
            "owned_data",
            "commands_accepted",
            "events_published",
            "events_consumed",
            "upstream_domains",
            "downstream_domains",
            "governance_policies",
        ):
            values = domain.get(field, [])
            if isinstance(values, list):
                duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
                if duplicates:
                    failures.append(f"{domain_id} contains duplicate {field}: {duplicates}")

    if failures:
        print("Domain registry validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"Validated {len(domains)} domains against {SCHEMA_PATH.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
