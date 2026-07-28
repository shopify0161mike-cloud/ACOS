#!/usr/bin/env python3
"""Validate the ACOS enterprise security registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "security" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "security-registry.schema.json"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        fail(f"missing registry: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        fail("security registry root must be a mapping")
    return data


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing schema: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_unique_ids(data: dict) -> None:
    domain_ids = [item["id"] for item in data["security_domains"]]
    if len(domain_ids) != len(set(domain_ids)):
        fail("security domain ids must be unique")

    invariant_ids = [item["id"] for item in data["security_invariants"]]
    if len(invariant_ids) != len(set(invariant_ids)):
        fail("security invariant ids must be unique")


def validate_required_exception_fields(data: dict) -> None:
    required = {
        "owner",
        "rationale",
        "risk",
        "compensating_controls",
        "approved_by",
        "expires_at",
    }
    actual = set(data["exceptions"]["required_fields"])
    missing = sorted(required - actual)
    if missing:
        fail(f"security exception model is missing fields: {', '.join(missing)}")


def main() -> None:
    registry = load_yaml(REGISTRY_PATH)
    schema = load_json(SCHEMA_PATH)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(registry), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f"ERROR: {location}: {error.message}", file=sys.stderr)
        raise SystemExit(1)

    validate_unique_ids(registry)
    validate_required_exception_fields(registry)

    print(
        "Security registry valid: "
        f"{len(registry['security_domains'])} domains, "
        f"{len(registry['security_invariants'])} invariants"
    )


if __name__ == "__main__":
    main()
