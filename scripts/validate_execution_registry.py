#!/usr/bin/env python3
"""Validate the canonical enterprise execution registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "execution" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "execution-registry.schema.json"
DOMAIN_REGISTRY_PATH = ROOT / "config" / "domains" / "registry.yaml"
CAPABILITY_REGISTRY_PATH = ROOT / "config" / "capabilities" / "registry.yaml"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return data


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    registry = load_yaml(REGISTRY_PATH)
    schema = load_json(SCHEMA_PATH)
    errors: list[str] = []

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for issue in sorted(validator.iter_errors(registry), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in issue.path) or "<root>"
        errors.append(f"schema violation at {location}: {issue.message}")

    states = registry.get("states", [])
    state_ids = [state.get("id") for state in states]
    if len(state_ids) != len(set(state_ids)):
        errors.append("state identifiers must be unique")

    terminal_states = {state["id"] for state in states if state.get("terminal")}
    transitions = registry.get("transitions", [])
    transition_keys: set[tuple[str, str, str]] = set()
    for transition in transitions:
        source = transition.get("from")
        target = transition.get("to")
        trigger = transition.get("trigger")
        if source not in state_ids:
            errors.append(f"transition references unknown source state: {source}")
        if target not in state_ids:
            errors.append(f"transition references unknown target state: {target}")
        if source in terminal_states:
            errors.append(f"terminal state cannot have outgoing transition: {source}")
        key = (source, target, trigger)
        if key in transition_keys:
            errors.append(f"duplicate transition: {source} -> {target} ({trigger})")
        transition_keys.add(key)

    if not terminal_states:
        errors.append("at least one terminal state is required")

    failure_classes = registry.get("failure_classes", [])
    failure_ids = [item.get("id") for item in failure_classes]
    if len(failure_ids) != len(set(failure_ids)):
        errors.append("failure class identifiers must be unique")

    retry_ids: set[str] = set()
    referenced_retry_failures: set[str] = set()
    for policy in registry.get("retry_policies", []):
        policy_id = policy.get("id")
        if policy_id in retry_ids:
            errors.append(f"duplicate retry policy: {policy_id}")
        retry_ids.add(policy_id)
        if policy.get("initial_delay_seconds", 0) > policy.get("max_delay_seconds", 0):
            errors.append(f"retry policy {policy_id} has initial delay greater than maximum delay")
        for failure_id in policy.get("failure_classes", []):
            referenced_retry_failures.add(failure_id)
            if failure_id not in failure_ids:
                errors.append(f"retry policy {policy_id} references unknown failure class: {failure_id}")
            else:
                failure = next(item for item in failure_classes if item.get("id") == failure_id)
                if not failure.get("retryable"):
                    errors.append(f"retry policy {policy_id} references non-retryable failure class: {failure_id}")

    compensation_ids: set[str] = set()
    for definition in registry.get("compensation_definitions", []):
        compensation_id = definition.get("id")
        if compensation_id in compensation_ids:
            errors.append(f"duplicate compensation definition: {compensation_id}")
        compensation_ids.add(compensation_id)
        failure_state = definition.get("failure_terminal_state")
        if failure_state not in terminal_states:
            errors.append(
                f"compensation {compensation_id} failure state must reference a terminal state: {failure_state}"
            )
        if definition.get("reversibility") == "irreversible" and definition.get("command"):
            errors.append(f"irreversible compensation {compensation_id} cannot define a compensation command")

    domain_registry = load_yaml(DOMAIN_REGISTRY_PATH)
    domain_ids = {item.get("id") for item in domain_registry.get("domains", [])}
    if registry.get("owner_domain") not in domain_ids:
        errors.append(f"unknown owner domain: {registry.get('owner_domain')}")

    capability_registry = load_yaml(CAPABILITY_REGISTRY_PATH)
    capabilities = capability_registry.get("capabilities", [])
    capability_ids = {item.get("id") for item in capabilities}
    if registry.get("owner_capability") not in capability_ids:
        errors.append(f"unknown owner capability: {registry.get('owner_capability')}")

    if errors:
        fail(errors)

    print(
        "Execution registry valid: "
        f"{len(states)} states, {len(transitions)} transitions, "
        f"{len(registry.get('retry_policies', []))} retry policies, "
        f"{len(failure_classes)} failure classes and "
        f"{len(registry.get('compensation_definitions', []))} compensation definitions."
    )


if __name__ == "__main__":
    main()
