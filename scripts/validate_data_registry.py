#!/usr/bin/env python3
"""Validate the ACOS enterprise data registry and its core invariants."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "data" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "data-registry.schema.json"
REQUIRED_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def main() -> int:
    try:
        registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        fail(str(exc))
        return 1

    errors: list[str] = []
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"schema {location}: {error.message}")

    classifications = registry.get("classifications", []) if isinstance(registry, dict) else []
    classification_ids = [item.get("id") for item in classifications if isinstance(item, dict)]
    if len(classification_ids) != len(set(classification_ids)):
        errors.append("classification identifiers must be unique")
    if set(classification_ids) != REQUIRED_CLASSIFICATIONS:
        errors.append("classifications must define exactly public, internal, confidential and restricted")

    products = registry.get("data_products", []) if isinstance(registry, dict) else []
    product_ids = [item.get("id") for item in products if isinstance(item, dict)]
    if len(product_ids) != len(set(product_ids)):
        errors.append("data product identifiers must be unique")

    for product in products:
        if not isinstance(product, dict):
            continue
        product_id = product.get("id", "<unknown>")
        classification = product.get("classification")
        controls = product.get("security_controls", {})
        if classification in {"confidential", "restricted"}:
            if not controls.get("encryption_at_rest") or not controls.get("encryption_in_transit"):
                errors.append(f"{product_id}: sensitive products require encryption at rest and in transit")
        quality = product.get("quality_objectives", {})
        if product.get("lifecycle_state") == "active" and quality.get("availability_percent", 0) <= 0:
            errors.append(f"{product_id}: active products require a positive availability objective")
        retention = product.get("retention", {})
        if retention.get("deletion_mode") == "legal-hold" and retention.get("period_days", 0) < 1:
            errors.append(f"{product_id}: legal-hold retention must specify a positive period")
        lineage = product.get("lineage", {})
        for key in ("sources", "transformations", "consumers"):
            values = lineage.get(key, [])
            if len(values) != len(set(values)):
                errors.append(f"{product_id}: lineage {key} must not contain duplicates")

    if errors:
        for error in errors:
            fail(error)
        return 1

    print(f"Validated {len(products)} enterprise data products.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
