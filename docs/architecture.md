# Architecture (M0 stub)

## Overview

Universal Health QR Phase 1 is a monorepo:

| Path | Role |
|------|------|
| `services/health-api` | FastAPI + PostgreSQL (central API) |
| `apps/*` | Patient mobile/web, marketing, admin, hospital demos (placeholders in M0) |
| `extension/` | Chrome/Edge MV3 (post-M0) |
| `packages/shared-types`, `packages/fhir-mapping` | Shared TS/Python stubs |
| `infra/` | Docker Compose + migration notes |

## Runtime (local)

```
Browser / clients → health-api (:8000) → PostgreSQL (:5432)
```

## Production (Flowlab)

```
Users → Reverse proxy (codebase.flowlab.fun) → FastAPI/Uvicorn container → Managed PostgreSQL
```

## Auth (M0)

Dev stub only: `POST /api/v1/auth/session` issues a JWT when credentials match `DEMO_USERNAME` / `DEMO_PASSWORD`. Full OAuth2/OIDC-ready patient and staff flows start in M1.

## Data (M0)

Alembic revision `20261101_0001` creates:

- `organizations` (hospital/clinic/lab/other)
- `users` (patient/staff/admin placeholders)

Further FHIR/consent/QR tables arrive in M1.
