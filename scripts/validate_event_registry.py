#!/usr/bin/env python3
"""Validate the canonical ACOS event registry and its domain traceability."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
EVENT_REGISTRY = ROOT / "config" / "events" / "registry.yaml"
EVENT_SCHEMA = ROOT / "schemas" / "event-registry.schema.json"
DOMAIN_REGISTRY = ROOT / "config" / "domains" / "registry.yaml"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []

    for path in (EVENT_REGISTRY, EVENT_SCHEMA, DOMAIN_REGISTRY):
        if not path.is_file():
            errors.append(f"Missing required file: {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    registry = load_yaml(EVENT_REGISTRY)
    schema = load_json(EVENT_SCHEMA)
    domain_registry = load_yaml(DOMAIN_REGISTRY)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for failure in sorted(validator.iter_errors(registry), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in failure.absolute_path) or "<root>"
        errors.append(f"Schema violation at {location}: {failure.message}")

    events = registry.get("events", []) if isinstance(registry, dict) else []
    domains = domain_registry.get("domains", []) if isinstance(domain_registry, dict) else []
    domain_by_id = {domain.get("id"): domain for domain in domains if isinstance(domain, dict)}

    event_names = [event.get("name") for event in events if isinstance(event, dict)]
    for name, count in Counter(event_names).items():
        if name and count > 1:
            errors.append(f"Duplicate canonical event: {name}")

    for event in events:
        if not isinstance(event, dict):
            continue

        name = event.get("name")
        producer_id = event.get("producer_domain")
        producer = domain_by_id.get(producer_id)
        if producer is None:
            errors.append(f"{name}: unknown producer domain {producer_id}")
        elif name not in producer.get("events_published", []):
            errors.append(f"{name}: producer {producer_id} does not declare the event in events_published")

        field_names = [field.get("name") for field in event.get("schema_fields", []) if isinstance(field, dict)]
        for field_name, count in Counter(field_names).items():
            if field_name and count > 1:
                errors.append(f"{name}: duplicate schema field {field_name}")

        for consumer_id in event.get("consumers", []):
            consumer = domain_by_id.get(consumer_id)
            if consumer is None:
                errors.append(f"{name}: unknown consumer domain {consumer_id}")
            elif name not in consumer.get("events_consumed", []):
                errors.append(f"{name}: consumer {consumer_id} does not declare the event in events_consumed")

        if event.get("contains_personal_data"):
            classified = {
                field.get("classification")
                for field in event.get("schema_fields", [])
                if isinstance(field, dict)
            }
            if not classified.intersection({"confidential", "restricted"}):
                errors.append(f"{name}: personal-data event lacks confidential or restricted fields")

        if event.get("retention") == "permanent" and event.get("compatibility") != "full":
            errors.append(f"{name}: permanent events must use full compatibility")

    if errors:
        print("Canonical event registry validation failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(f"Canonical event registry is valid: {len(events)} events across {len(domain_by_id)} domains.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
