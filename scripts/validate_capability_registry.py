#!/usr/bin/env python3
"""Validate the ACOS capability registry against its schema and invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import yaml

DEFAULT_REGISTRY = Path("config/capabilities/registry.yaml")
DEFAULT_SCHEMA = Path("schemas/capability-registry.schema.json")
CAPABILITY_ID_PATTERN = re.compile(r"^CAP-(COM|INT|GOV|PLT)-[A-Z]{3}-\d{3}$")


def load_yaml(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"Required capability registry is missing: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"Capability registry is not valid YAML: {path}: {exc}") from exc


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"Required capability schema is missing: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Capability schema is not valid JSON: {path}: {exc}") from exc


def validate_schema(registry: Any, schema: Any) -> list[str]:
    try:
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
    except jsonschema.SchemaError as exc:
        return [f"Capability schema is invalid: {exc.message}"]

    validator = validator_class(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(
        validator.iter_errors(registry),
        key=lambda error: [str(part) for part in error.absolute_path],
    )

    failures: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        failures.append(f"{location}: {error.message}")
    return failures


def validate_registry_invariants(registry: Any) -> list[str]:
    if not isinstance(registry, dict):
        return ["Registry root must be an object"]

    capabilities = registry.get("capabilities", [])
    if not isinstance(capabilities, list):
        return ["Registry field 'capabilities' must be an array"]

    failures: list[str] = []
    identifiers = [capability.get("id") for capability in capabilities if isinstance(capability, dict)]

    duplicate_ids = sorted(
        identifier
        for identifier, count in Counter(identifiers).items()
        if identifier is not None and count > 1
    )
    if duplicate_ids:
        failures.append(f"Duplicate capability IDs: {duplicate_ids}")

    invalid_ids = sorted(
        repr(identifier)
        for identifier in identifiers
        if not isinstance(identifier, str) or not CAPABILITY_ID_PATTERN.fullmatch(identifier)
    )
    if invalid_ids:
        failures.append(f"Invalid capability IDs: {invalid_ids}")

    known_ids = {identifier for identifier in identifiers if isinstance(identifier, str)}

    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            failures.append(f"Capability at index {index} must be an object")
            continue

        capability_id = capability.get("id", f"<index:{index}>")
        dependencies = capability.get("dependencies", [])
        if not isinstance(dependencies, list):
            failures.append(f"{capability_id} dependencies must be an array")
            continue

        if capability_id in dependencies:
            failures.append(f"{capability_id} depends on itself")

        duplicate_dependencies = sorted(
            dependency
            for dependency, count in Counter(dependencies).items()
            if count > 1
        )
        if duplicate_dependencies:
            failures.append(
                f"{capability_id} contains duplicate dependencies: {duplicate_dependencies}"
            )

        unresolved = sorted(
            dependency
            for dependency in set(dependencies)
            if not isinstance(dependency, str) or dependency not in known_ids
        )
        if unresolved:
            failures.append(f"{capability_id} contains unresolved dependencies: {unresolved}")

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        registry = load_yaml(args.registry)
        schema = load_json(args.schema)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    failures = validate_schema(registry, schema)
    failures.extend(validate_registry_invariants(registry))

    if failures:
        print("Capability registry validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    capability_count = len(registry.get("capabilities", []))
    print(
        f"Validated {capability_count} capabilities against {args.schema} "
        "with identifier and dependency-reference invariants."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
