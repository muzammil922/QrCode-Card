# Security notes (M0 stub)

## Non-negotiables (Phase 1+)

- QR tokens are opaque; never embed PHI in QR payloads.
- Staff access requires authenticated session + server-side authorization.
- No silent writes into hospital EHR forms; adapters confirm before fill.
- Phase 1 uses **synthetic data only**.
- Secrets live in host env / `.env` (gitignored), never in source.

## M0 auth stub

`POST /api/v1/auth/session` is a **demo credential check** against env vars. It is not production identity. Rotate `JWT_SECRET` and demo passwords before any shared environment.

## Database

Prefer TLS for managed Postgres when available. Do not commit connection strings with passwords.

## Audit

Full append-only `audit_events` arrives in M1. M0 has no clinical endpoints.
