#!/usr/bin/env python3
"""Validate the canonical ACOS governance registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "governance" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "governance-registry.schema.json"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def main() -> int:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry),
        key=lambda error: list(error.absolute_path),
    )
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        fail(f"schema violation at {path}: {error.message}")

    authority_ids = [item["id"] for item in registry.get("authority_levels", [])]
    risk_ids = [item["id"] for item in registry.get("risk_tiers", [])]
    policy_ids = [item["id"] for item in registry.get("policies", [])]
    approval_ids = [item["id"] for item in registry.get("approval_requirements", [])]

    semantic_errors: list[str] = []
    for label, values in {
        "authority level": authority_ids,
        "risk tier": risk_ids,
        "policy": policy_ids,
        "approval requirement": approval_ids,
    }.items():
        duplicates = duplicate_values(values)
        if duplicates:
            semantic_errors.append(f"duplicate {label} identifiers: {sorted(duplicates)}")

    authority_set = set(authority_ids)
    risk_set = set(risk_ids)
    approval_set = set(approval_ids)
    policy_set = set(policy_ids)

    previous_max: int | None = None
    for tier in sorted(registry.get("risk_tiers", []), key=lambda item: item["score_min"]):
        if tier["score_min"] > tier["score_max"]:
            semantic_errors.append(f"risk tier {tier['id']} has score_min above score_max")
        if previous_max is not None and tier["score_min"] != previous_max + 1:
            semantic_errors.append(f"risk tier {tier['id']} does not continue the score range")
        previous_max = tier["score_max"]

    for requirement in registry.get("approval_requirements", []):
        if requirement["minimum_authority"] not in authority_set:
            semantic_errors.append(
                f"approval requirement {requirement['id']} references unknown authority "
                f"{requirement['minimum_authority']}"
            )
        unknown_tiers = set(requirement["risk_tiers"]) - risk_set
        if unknown_tiers:
            semantic_errors.append(
                f"approval requirement {requirement['id']} references unknown risk tiers {sorted(unknown_tiers)}"
            )
        if requirement["quorum"] > len(requirement["sequence"]):
            semantic_errors.append(
                f"approval requirement {requirement['id']} quorum exceeds approval sequence length"
            )

    for policy in registry.get("policies", []):
        approval_requirement = policy.get("approval_requirement")
        if approval_requirement and approval_requirement not in approval_set:
            semantic_errors.append(
                f"policy {policy['id']} references unknown approval requirement {approval_requirement}"
            )
        if policy["effect"] == "require_approval" and not approval_requirement:
            semantic_errors.append(f"policy {policy['id']} requires approval but defines no requirement")
        if policy["effect"] == "require_control" and not policy.get("controls_required"):
            semantic_errors.append(f"policy {policy['id']} requires controls but defines none")

    emergency_policy = registry.get("budget_controls", {}).get("emergency_exception_policy")
    if emergency_policy not in policy_set:
        semantic_errors.append(f"budget controls reference unknown emergency policy {emergency_policy}")

    if registry.get("default_effect") != "deny":
        semantic_errors.append("default governance effect must be deny")
    if registry.get("conflict_resolution") != "explicit_deny":
        semantic_errors.append("governance conflict resolution must be explicit_deny")
    if registry.get("budget_controls", {}).get("overcommit_allowed") is not False:
        semantic_errors.append("budget overcommit must be disabled")
    if registry.get("exception_policy", {}).get("automatic_renewal") is not False:
        semantic_errors.append("governance exceptions must not renew automatically")

    for message in semantic_errors:
        fail(message)

    if errors or semantic_errors:
        return 1

    print(
        "Governance registry valid: "
        f"{len(policy_ids)} policies, {len(risk_ids)} risk tiers, "
        f"{len(approval_ids)} approval requirements."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
