# ACOS kernel architecture

The kernel is the deterministic business-logic boundary of the Autonomous Commerce
Operating System. n8n remains the control-plane orchestrator; it invokes kernel use
cases and never becomes the source of truth.

## Runtime boundaries

- PostgreSQL is the only production source of truth.
- Production adapters must implement the transactional unit-of-work port in
  `src/kernel/ports.js`.
- The kernel is tenant-aware and market-agnostic. DOGVISION uses tenant ID `001`,
  but no business rule is hard-coded to that tenant or to the Netherlands.
- Global supplier countries and branded dropshipping are data, not special cases.
- Exactly five executable, unblocked opportunities form an approval set.
- Voice acceptance is the only normal human acceptance channel.
- Approval, accepted opportunity, and audit event are written in one transaction.
- Evidence versions and idempotency keys are mandatory.

## Control flow

```text
discovery adapters
  -> qualification workers
  -> selectExactTopFive
  -> n8n voice/visual presentation
  -> acceptOpportunity
  -> PostgreSQL transaction
       approval event
       accepted opportunity
       audit event
```

Discovery, supplier, market, qualification, scoring, and evidence-collection workers
belong outside n8n. n8n schedules work, transports contracts, handles control-plane
timeouts, and observes durable status.

## Migration 002

Migration 002 is intentionally blocked. This bootstrap defines the runtime port and
domain contracts but does not create, execute, checksum, or imply readiness of the
PostgreSQL execution-runtime migration. A production adapter must not be enabled
until the reviewed immutable Migration 002 artifact exists and its schema supports
the contracts in this kernel.

## Failure behavior

- Contract, tenant, evidence, and channel violations fail closed.
- Fewer than five executable opportunities prevents approval presentation.
- Idempotent replays return the original approval without duplicate writes.
- Conflicting reuse of an idempotency key fails.
- Any persistence or audit failure rolls back the complete acceptance transaction.
