#!/usr/bin/env python3
"""Reject circular dependencies in the ACOS capability registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY = Path("config/capabilities/registry.yaml")


def load_registry(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Required capability registry is missing: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            registry = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"Capability registry is not valid YAML: {path}: {exc}") from exc
    if not isinstance(registry, dict):
        raise ValueError("Registry root must be an object")
    return registry


def build_graph(registry: dict[str, Any]) -> dict[str, list[str]]:
    capabilities = registry.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise ValueError("Registry field 'capabilities' must be an array")

    graph: dict[str, list[str]] = {}
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            raise ValueError(f"Capability at index {index} must be an object")
        capability_id = capability.get("id")
        dependencies = capability.get("dependencies", [])
        if not isinstance(capability_id, str):
            raise ValueError(f"Capability at index {index} has no valid string ID")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            raise ValueError(f"{capability_id} dependencies must be an array of strings")
        graph[capability_id] = list(dependencies)

    unresolved = sorted(
        (node, dependency)
        for node, dependencies in graph.items()
        for dependency in dependencies
        if dependency not in graph
    )
    if unresolved:
        details = ", ".join(f"{node} -> {dependency}" for node, dependency in unresolved)
        raise ValueError(f"Dependency graph contains unresolved references: {details}")

    return graph


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    white, gray, black = 0, 1, 2
    state = {node: white for node in graph}
    stack: list[str] = []
    stack_index: dict[str, int] = {}
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def canonicalize(cycle: list[str]) -> tuple[str, ...]:
        body = cycle[:-1]
        rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
        canonical = min(rotations)
        return canonical + (canonical[0],)

    def visit(node: str) -> None:
        state[node] = gray
        stack_index[node] = len(stack)
        stack.append(node)

        for dependency in graph[node]:
            if state[dependency] == white:
                visit(dependency)
            elif state[dependency] == gray:
                start = stack_index[dependency]
                cycle = stack[start:] + [dependency]
                canonical = canonicalize(cycle)
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    cycles.append(list(canonical))

        stack.pop()
        stack_index.pop(node, None)
        state[node] = black

    for node in sorted(graph):
        if state[node] == white:
            visit(node)

    return sorted(cycles)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        registry = load_registry(args.registry)
        graph = build_graph(registry)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    cycles = find_cycles(graph)
    if cycles:
        print("Circular capability dependencies detected:", file=sys.stderr)
        for cycle in cycles:
            print("  - " + " -> ".join(cycle), file=sys.stderr)
        return 1

    edge_count = sum(len(dependencies) for dependencies in graph.values())
    print(
        f"Capability dependency graph is acyclic across {len(graph)} nodes "
        f"and {edge_count} directed edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
