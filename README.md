# ACOS

ACOS is a voice-native, multi-tenant Autonomous Commerce Operating System. This
repository begins with a small deterministic kernel that keeps business logic out
of n8n and requires PostgreSQL-backed transactional persistence in production.

## Kernel bootstrap

The first vertical contract supports:

1. tenant-aware qualified opportunities;
2. deterministic selection of exactly five executable opportunities;
3. explicit, confirmed voice acceptance;
4. idempotent and atomic persistence of the approval, accepted opportunity, and
   audit evidence.

The current implementation deliberately does not include a production PostgreSQL
adapter. Migration 002 remains blocked until its schema and immutable migration
artifact are reviewed.

## Development

Requires Node.js 20 or newer.

```bash
npm test
npm run check
```

See `docs/architecture.md` for runtime boundaries and failure behavior.
