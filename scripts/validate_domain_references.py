#!/usr/bin/env python3
"""Validate domain references, capability ownership and event contracts."""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_REGISTRY_PATH = ROOT / "config/domains/registry.yaml"
CAPABILITY_REGISTRY_PATH = ROOT / "config/capabilities/registry.yaml"

# Events intentionally entering the modeled domain landscape from a capability
# not yet represented as a bounded context in Chapter 1.2.
EXTERNAL_EVENT_ALLOWLIST = {
    "analytics.outcome_recorded.v1",
}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    for path in (DOMAIN_REGISTRY_PATH, CAPABILITY_REGISTRY_PATH):
        if not path.is_file():
            failures.append(f"Required registry is missing: {path.relative_to(ROOT)}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    domain_registry = load_yaml(DOMAIN_REGISTRY_PATH)
    capability_registry = load_yaml(CAPABILITY_REGISTRY_PATH)
    domains = domain_registry.get("domains", [])
    capabilities = capability_registry.get("capabilities", [])

    domain_ids = {domain["id"] for domain in domains}
    capability_ids = {capability["id"] for capability in capabilities}

    capability_owners: dict[str, list[str]] = defaultdict(list)
    data_owners: dict[str, list[str]] = defaultdict(list)
    event_producers: dict[str, list[str]] = defaultdict(list)
    event_consumers: dict[str, list[str]] = defaultdict(list)

    for domain in domains:
        domain_id = domain["id"]

        upstream = domain.get("upstream_domains", [])
        downstream = domain.get("downstream_domains", [])

        for referenced_domain in upstream + downstream:
            if referenced_domain not in domain_ids:
                failures.append(f"{domain_id} references unknown domain {referenced_domain}")
            if referenced_domain == domain_id:
                failures.append(f"{domain_id} contains a self domain reference")

        for capability_id in domain.get("owned_capabilities", []):
            capability_owners[capability_id].append(domain_id)
            if capability_id not in capability_ids:
                failures.append(f"{domain_id} owns unknown capability {capability_id}")

        for data_object in domain.get("owned_data", []):
            data_owners[data_object].append(domain_id)

        for event in domain.get("events_published", []):
            event_producers[event].append(domain_id)

        for event in domain.get("events_consumed", []):
            event_consumers[event].append(domain_id)

    for capability_id in sorted(capability_ids):
        owners = capability_owners.get(capability_id, [])
        if not owners:
            failures.append(f"Capability {capability_id} has no owning domain")
        elif len(owners) > 1:
            failures.append(f"Capability {capability_id} has multiple owning domains: {owners}")

    for capability_id in sorted(set(capability_owners) - capability_ids):
        failures.append(f"Domain registry references capability absent from capability registry: {capability_id}")

    for data_object, owners in sorted(data_owners.items()):
        if len(owners) > 1:
            failures.append(f"Data object {data_object} has multiple authoritative owners: {owners}")

    for event, producers in sorted(event_producers.items()):
        if len(producers) > 1:
            failures.append(f"Event {event} has multiple producers: {producers}")

    for event, consumers in sorted(event_consumers.items()):
        if event not in event_producers and event not in EXTERNAL_EVENT_ALLOWLIST:
            failures.append(f"Consumed event {event} has no producer; consumers: {consumers}")

    for event in sorted(EXTERNAL_EVENT_ALLOWLIST):
        if event in event_consumers and event not in event_producers:
            warnings.append(f"Allowlisted external event has no modeled producer: {event}")

    # Cross-check capability event ownership. A domain owning a capability must
    # also publish the capability's modeled output events, unless the event is
    # intentionally emitted by an infrastructural delivery mechanism.
    infrastructure_events = {
        "audit.evidence_recorded.v1",
        "event.delivery_recorded.v1",
        "integration.operation_recorded.v1",
    }
    capability_by_id = {capability["id"]: capability for capability in capabilities}
    domain_by_id = {domain["id"]: domain for domain in domains}

    for capability_id, owners in sorted(capability_owners.items()):
        if len(owners) != 1 or capability_id not in capability_by_id:
            continue
        owner = domain_by_id[owners[0]]
        published = set(owner.get("events_published", []))
        expected = set(capability_by_id[capability_id].get("events_emitted", []))
        missing = sorted(expected - published - infrastructure_events)
        if missing:
            failures.append(
                f"{owners[0]} does not publish events emitted by owned capability {capability_id}: {missing}"
            )

    for warning in warnings:
        print(f"WARNING: {warning}")

    if failures:
        print("Domain reference validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(
        "Validated domain references, unique capability/data ownership and "
        f"event producer-consumer contracts across {len(domains)} domains."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
