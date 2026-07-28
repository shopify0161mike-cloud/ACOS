#!/usr/bin/env python3
"""Validate the ACOS intelligence registry and its internal references."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "intelligence" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "intelligence-registry.schema.json"


def ids(items: list[dict]) -> set[str]:
    return {item["id"] for item in items}


def main() -> int:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f"schema error at {location}: {error.message}", file=sys.stderr)
        return 1

    collections = {
        "agents": registry["agents"],
        "model_policies": registry["model_policies"],
        "prompt_policies": registry["prompt_policies"],
        "memory_policies": registry["memory_policies"],
        "knowledge_sources": registry["knowledge_sources"],
        "evaluation_suites": registry["evaluation_suites"],
        "observability_profiles": registry["observability_profiles"],
    }

    for name, items in collections.items():
        item_ids = [item["id"] for item in items]
        if len(item_ids) != len(set(item_ids)):
            print(f"duplicate identifiers in {name}", file=sys.stderr)
            return 1

    model_ids = ids(collections["model_policies"])
    prompt_ids = ids(collections["prompt_policies"])
    memory_ids = ids(collections["memory_policies"])
    source_ids = ids(collections["knowledge_sources"])
    evaluation_ids = ids(collections["evaluation_suites"])
    observability_ids = ids(collections["observability_profiles"])

    for agent in collections["agents"]:
        references = [
            ("model_policy", agent["model_policy"], model_ids),
            ("prompt_policy", agent["prompt_policy"], prompt_ids),
            ("memory_policy", agent["memory_policy"], memory_ids),
            ("evaluation_suite", agent["evaluation_suite"], evaluation_ids),
            ("observability_profile", agent["observability_profile"], observability_ids),
        ]
        for field, value, valid_ids in references:
            if value not in valid_ids:
                print(f"agent {agent['id']} references unknown {field}: {value}", file=sys.stderr)
                return 1
        unknown_sources = set(agent["knowledge_sources"]) - source_ids
        if unknown_sources:
            print(f"agent {agent['id']} references unknown knowledge sources: {sorted(unknown_sources)}", file=sys.stderr)
            return 1
        if agent["risk_class"] in {"high", "critical"} and not agent["approval_required_for"]:
            print(f"high-risk agent {agent['id']} must define approval triggers", file=sys.stderr)
            return 1

    for source in collections["knowledge_sources"]:
        if not source["provenance_required"]:
            print(f"knowledge source {source['id']} must require provenance", file=sys.stderr)
            return 1

    print("Intelligence registry validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
