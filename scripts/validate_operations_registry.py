#!/usr/bin/env python3
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "operations" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "operations-registry.schema.json"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def fail(message: str) -> None:
    print(f"operations validation error: {message}", file=sys.stderr)
    raise SystemExit(1)


def unique_ids(items, section: str):
    seen = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            fail(f"duplicate id '{item_id}' in {section}")
        seen.add(item_id)
    return seen


def main() -> None:
    registry = load_yaml(REGISTRY_PATH)
    schema = load_yaml(SCHEMA_PATH)

    errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f"{location}: {error.message}", file=sys.stderr)
        raise SystemExit(1)

    tier_ids = unique_ids(registry["service_tiers"], "service_tiers")
    severity_ids = unique_ids(registry["incident_severities"], "incident_severities")
    change_ids = unique_ids(registry["change_classes"], "change_classes")
    runbook_ids = unique_ids(registry["runbooks"], "runbooks")
    continuity_ids = unique_ids(registry["continuity_plans"], "continuity_plans")
    service_ids = unique_ids(registry["services"], "services")
    unique_ids(registry["operational_invariants"], "operational_invariants")

    if "emergency" not in change_ids:
        fail("change_classes must define 'emergency'")
    emergency = next(item for item in registry["change_classes"] if item["id"] == "emergency")
    if not emergency["retrospective_required"]:
        fail("emergency changes must require retrospective review")

    for severity in registry["incident_severities"]:
        if severity["escalation_minutes"] < severity["acknowledgement_minutes"]:
            fail(f"{severity['id']} escalation target cannot precede acknowledgement target")

    tier_map = {item["id"]: item for item in registry["service_tiers"]}
    for service in registry["services"]:
        if service["service_tier"] not in tier_ids:
            fail(f"service '{service['id']}' references unknown tier '{service['service_tier']}'")
        missing_runbooks = set(service["runbooks"]) - runbook_ids
        if missing_runbooks:
            fail(f"service '{service['id']}' references unknown runbooks: {sorted(missing_runbooks)}")
        if service["environment"] == "production" and not service["slos"]:
            fail(f"production service '{service['id']}' must define at least one SLO")
        if service["environment"] == "production" and not service["runbooks"]:
            fail(f"production service '{service['id']}' must define at least one runbook")

        tier = tier_map[service["service_tier"]]
        continuity = service.get("continuity_plan")
        if tier["requires_continuity_plan"] and not continuity:
            fail(f"service '{service['id']}' requires a continuity plan")
        if continuity and continuity not in continuity_ids:
            fail(f"service '{service['id']}' references unknown continuity plan '{continuity}'")

        slo_ids = set()
        for slo in service["slos"]:
            if slo["id"] in slo_ids:
                fail(f"duplicate SLO id '{slo['id']}' in service '{service['id']}'")
            slo_ids.add(slo["id"])
            if slo["objective_percent"] < tier["minimum_availability"] and "availability" in slo["id"]:
                fail(
                    f"availability SLO '{slo['id']}' for service '{service['id']}' "
                    f"is below tier minimum {tier['minimum_availability']}"
                )

    print(
        "Operations registry valid: "
        f"{len(service_ids)} services, {len(tier_ids)} tiers, "
        f"{len(severity_ids)} severities, {len(runbook_ids)} runbooks."
    )


if __name__ == "__main__":
    main()
