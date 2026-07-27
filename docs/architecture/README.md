# ACOS Enterprise Architecture

This directory contains the canonical enterprise and domain architecture for ACOS. It translates the Constitution into governed capability, domain, information, integration, runtime and implementation structures.

## Authority hierarchy

1. ACOS Constitution
2. Enterprise Architecture
3. Domain Architecture
4. Technical Architecture
5. Implementation Specifications
6. Source Code

When a lower-level artifact conflicts with a higher-level artifact, the lower-level artifact must change.

## Architecture chapters

### 1.0 Enterprise Context

- [Enterprise Context Map](01.0-enterprise-context-map.md)

### 1.1 Enterprise Capability Architecture

- [Capability Catalog](01.1-capability-catalog.md)
- [Capability Traceability Model](01.1-capability-traceability.md)
- [Enterprise Capability Map](diagrams/enterprise-capability-map.mmd)
- [Capability Dependency Graph](diagrams/capability-dependency-graph.mmd)
- [Capability Lifecycle](diagrams/capability-lifecycle.mmd)
- [Capability Governance Flow](diagrams/capability-governance-flow.mmd)
- [Capability Registry](../../config/capabilities/registry.yaml)
- [Capability Registry Schema](../../schemas/capability-registry.schema.json)

### 1.2 Enterprise Domain Architecture

Status: planned.

The domain architecture will assign capability ownership to bounded domains and define domain boundaries, contracts, events, data ownership and anti-corruption layers.

## Machine-readable architecture

The canonical capability registry is maintained in:

```text
config/capabilities/registry.yaml
```

Its structure is governed by:

```text
schemas/capability-registry.schema.json
```

Human-readable documentation and diagrams must remain consistent with the registry. The registry is the source of truth for capability identifiers, ownership, dependencies, authority, lifecycle state, policies, events, metrics, data ownership, recovery objectives and implementation references.

## Validation

Run the architecture controls locally with:

```bash
python scripts/validate_capability_registry.py
python scripts/validate_capability_dependencies.py
python scripts/validate_capability_diagrams.py
```

Run the complete repository compliance suite with:

```bash
python scripts/validate_constitution.py
python -m unittest discover -s tests -p 'test_*.py'
```

The same checks run through `.github/workflows/architecture-validation.yml` for relevant pushes and pull requests.

## Change governance

A material architecture change must:

1. identify the affected capability or domain;
2. preserve constitutional constraints;
3. update the machine-readable registry or schema when applicable;
4. update diagrams and documentation when meaning changes;
5. include an ADR for material, irreversible or cross-domain decisions;
6. pass automated validation;
7. retain attributable review and approval evidence.

No implementation reference may be treated as architecture authority. Implementation exists to realize approved architecture, not redefine it.
