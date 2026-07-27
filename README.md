# ACOS — Autonomous Commerce Operating System

ACOS is an enterprise-grade, AI-native commerce operating system designed to research, launch, operate and continuously optimize branded commerce businesses while preserving human authority, governance, auditability and long-term scalability.

## Core doctrine

> Every decision made by ACOS must create measurable commercial value while preserving simplicity, governance, trust and long-term scalability.

ACOS is built around stable business capabilities and bounded domains—not screens, vendors, prompts or individual workflows. Technology is replaceable. Business authority, constitutional rules and domain ownership are not.

## Repository structure

```text
docs/
  constitution/       Canonical constitutional specification
  architecture/       Enterprise and domain architecture
  adr/                Architectural Decision Records
config/
  constitution/       Machine-readable constitutional registry
  capabilities/       Machine-readable enterprise capability registry
schemas/               Validation schemas
scripts/               Architecture and constitutional validation
.github/workflows/     Automated compliance checks
tests/                 Executable compliance tests
```

## Constitutional hierarchy

1. Constitution
2. Enterprise Architecture
3. Domain Architecture
4. Technical Architecture
5. Implementation Specifications
6. Source Code

When implementation conflicts with the Constitution, implementation changes.

## Enterprise domains

- **Commerce** — product, supplier, brand, marketing, sales, customer, pricing, inventory, orders, fulfillment, finance and analytics.
- **Intelligence** — executive coordination and specialized domain intelligence.
- **Governance** — policy, approval, risk, compliance, security, audit and constitutional validation.
- **Platform** — identity, events, workflows, integrations, storage, observability, configuration and deployment.

## Non-negotiable constraints

- Human strategic authority is permanent.
- AI cannot modify the Constitution or expand its own authority.
- Business logic does not live in prompts, UI code, integrations or workflow definitions.
- Domains own their data and communicate through explicit contracts.
- Irreversible and constitutionally sensitive actions require human approval.
- Every autonomous action must be explainable and auditable.
- External providers are isolated behind anti-corruption layers.

## Validate the repository

```bash
python scripts/validate_constitution.py
python scripts/validate_capability_registry.py
python scripts/validate_capability_dependencies.py
python scripts/validate_capability_diagrams.py
python -m unittest discover -s tests -p 'test_*.py'
```

GitHub Actions runs the corresponding checks for relevant pushes and pull requests.

## Canonical documents

- [ACOS Constitution](docs/constitution/ACOS-CONSTITUTION.md)
- [Enterprise Architecture Index](docs/architecture/README.md)
- [Enterprise Context Map](docs/architecture/01.0-enterprise-context-map.md)
- [Enterprise Capability Catalog](docs/architecture/01.1-capability-catalog.md)
- [Capability Traceability Model](docs/architecture/01.1-capability-traceability.md)
- [ADR index](docs/adr/README.md)
- [Machine-readable constitutional registry](config/constitution/registry.yaml)
- [Machine-readable capability registry](config/capabilities/registry.yaml)

## Status

Part 0 — Constitution is canonical through Chapter 0.13.

Part I — Enterprise Architecture is canonical through Chapter 1.1, Enterprise Capability Architecture. Chapter 1.2, Enterprise Domain Architecture, is next.
