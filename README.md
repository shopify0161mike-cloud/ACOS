# ACOS - Autonomous Commerce Operating System

ACOS is an enterprise commerce operating system that discovers, evaluates, launches, operates and improves commerce opportunities while preserving explicit human decision rights.

This repository is the canonical source of truth for the ACOS Constitution, architecture, contracts, workflows and implementation standards.

## Non-negotiable operating rules

1. ACOS may research and recommend autonomously.
2. ACOS may never select the final product on behalf of the owner.
3. Product approval, build approval, publication approval, ad-spend approval and inventory-purchase approval are separate decisions.
4. Financial calculations are deterministic, reproducible and traceable.
5. AI outputs are proposals until validated by contracts and quality gates.
6. n8n remains the workflow orchestrator; business intelligence lives in versioned services and contracts.
7. Every material decision is auditable and reproducible.
8. No implementation may bypass the Constitution.

## Repository map

- `docs/00-governance/` - Constitution, glossary, decision rights and governance controls
- `docs/01-architecture/` - system, kernel, memory and event architecture
- `docs/02-intelligence/` - specialist intelligence services
- `docs/03-workflows/` - end-to-end workflow specifications
- `docs/04-contracts/` - API, event, JSON and error contracts
- `docs/05-data/` - canonical data model and database standards
- `docs/06-n8n/` - orchestration and migration standards
- `docs/07-engineering/` - coding, testing, prompt and release standards
- `docs/08-operations/` - monitoring, incidents, recovery and change control
- `docs/09-roadmap/` - phased implementation plan and definitions of done
- `schemas/` - machine-readable schemas
- `sql/` - database DDL
- `.github/workflows/` - automated documentation and contract validation

## Documentation authority

When implementation and documentation conflict, the following precedence applies:

1. ACOS Constitution
2. Accepted Architecture Decision Records
3. Versioned machine-readable contracts
4. Approved architecture and workflow specifications
5. Runtime implementation
6. Operational notes

A runtime behavior that violates a higher-order source is a defect, not an alternative interpretation.

## Current workstream

Branch: `acos-constitution-v1`

Active block: **00 - Governance & Constitution**

The first block establishes the permanent rules, vocabulary and decision boundaries that every later ACOS component must obey.