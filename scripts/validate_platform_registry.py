#!/usr/bin/env python3
"""Validate the ACOS platform registry and platform invariants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "platform" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "platform-registry.schema.json"


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(registry), key=lambda error: list(error.path))
    errors = [
        f"schema {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in schema_errors
    ]

    services = registry.get("services", []) if isinstance(registry, dict) else []
    ids = [service.get("id") for service in services if isinstance(service, dict)]
    if len(ids) != len(set(ids)):
        errors.append("service ids must be unique")

    known = set(ids)
    graph: dict[str, list[str]] = {}
    for service in services:
        service_id = service.get("id")
        dependencies = service.get("dependencies", [])
        graph[service_id] = dependencies
        for dependency in dependencies:
            if dependency not in known:
                errors.append(f"{service_id} references unknown dependency {dependency}")
            if dependency == service_id:
                errors.append(f"{service_id} cannot depend on itself")

        if "production" in service.get("environments", []):
            controls = service.get("controls", {})
            required = {
                "authentication": "required",
                "encryption_in_transit": "required",
                "encryption_at_rest": "required",
                "audit_logging": "required",
            }
            for key, value in required.items():
                if controls.get(key) != value:
                    errors.append(f"production service {service_id} must set {key} to {value}")

        if service.get("criticality") == "tier-0":
            if service.get("availability_slo", 0) < 99.9:
                errors.append(f"tier-0 service {service_id} must have availability_slo >= 99.9")
            if service.get("recovery_test_frequency_days", 366) > 90:
                errors.append(f"tier-0 service {service_id} must test recovery at least every 90 days")
            if service.get("deployment_strategy") == "recreate":
                errors.append(f"tier-0 service {service_id} cannot use recreate deployment")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            start = path.index(node) if node in path else 0
            errors.append("circular platform dependency: " + " -> ".join(path[start:] + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in known:
                visit(dependency, path + [node])
        visiting.remove(node)
        visited.add(node)

    for service_id in known:
        visit(service_id, [])

    if errors:
        fail(errors)

    print(f"Platform registry valid: {len(services)} services")


if __name__ == "__main__":
    main()
