#!/usr/bin/env python3
"""Validate the canonical ACOS capability architecture diagrams."""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_DIAGRAMS = (
    Path("docs/architecture/diagrams/enterprise-capability-map.mmd"),
    Path("docs/architecture/diagrams/capability-dependency-graph.mmd"),
    Path("docs/architecture/diagrams/capability-lifecycle.mmd"),
    Path("docs/architecture/diagrams/capability-governance-flow.mmd"),
)
MERMAID_DECLARATIONS = ("flowchart", "graph ", "stateDiagram")


def validate_diagram(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Missing canonical diagram: {path}"]

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return [f"Canonical diagram is empty: {path}"]
    if not any(token in content for token in MERMAID_DECLARATIONS):
        return [f"No Mermaid diagram declaration found in: {path}"]
    return []


def main() -> int:
    failures = [
        failure
        for diagram in REQUIRED_DIAGRAMS
        for failure in validate_diagram(diagram)
    ]

    if failures:
        print("Canonical capability diagram validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"Validated {len(REQUIRED_DIAGRAMS)} canonical capability diagrams.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
