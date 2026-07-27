#!/usr/bin/env python3
"""Reject circular downstream domain dependencies in the ACOS domain registry."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config/domains/registry.yaml"


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    """Return a rotation-stable representation for cycle de-duplication."""
    body = cycle[:-1]
    rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
    normalized = min(rotations)
    return normalized + (normalized[0],)


def main() -> int:
    if not REGISTRY_PATH.is_file():
        print(f"ERROR: Required registry is missing: {REGISTRY_PATH.relative_to(ROOT)}")
        return 1

    registry = load_yaml(REGISTRY_PATH)
    domains = registry.get("domains", [])
    graph = {
        domain["id"]: list(domain.get("downstream_domains", []))
        for domain in domains
    }

    unknown = sorted(
        (source, target)
        for source, targets in graph.items()
        for target in targets
        if target not in graph
    )
    if unknown:
        print("Domain dependency validation failed:")
        for source, target in unknown:
            print(f"  - {source} references unknown downstream domain {target}")
        return 1

    white, gray, black = 0, 1, 2
    state = {node: white for node in graph}
    stack: list[str] = []
    positions: dict[str, int] = {}
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = gray
        positions[node] = len(stack)
        stack.append(node)

        for dependency in graph[node]:
            if state[dependency] == white:
                visit(dependency)
            elif state[dependency] == gray:
                start = positions[dependency]
                cycles.add(canonical_cycle(stack[start:] + [dependency]))

        stack.pop()
        positions.pop(node, None)
        state[node] = black

    for node in graph:
        if state[node] == white:
            visit(node)

    if cycles:
        print("Circular downstream domain dependencies detected:")
        for cycle in sorted(cycles):
            print("  - " + " -> ".join(cycle))
        return 1

    print(f"Domain downstream dependency graph is acyclic across {len(graph)} domains.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
