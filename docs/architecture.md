# Architecture — Universal Health QR Phase 1

## Purpose

Demonstrable interoperability prototype: one opaque Universal Health QR identity, post-save sync from Demo Hospital A to a central FastAPI + PostgreSQL store, authorized read at Demo Hospital B (extension side panel + demos), patient portal/mobile view of synced prescriptions. **Not** a certified EHR or universal scraper.

## System context

```
Patient (Expo / web-portal)
        │
Hospital A demo ──POST integration-events──► health-api ──► PostgreSQL
        │                                         ▲
Hospital B demo / MV3 extension ──resolve-qr─────┘
Admin dashboard ──/admin/stats, audit────────────┘
Marketing site (static)
```

Production API: `https://codebase.flowlab.fun` (Dokploy → uvicorn `${PORT:-8000}`).

## Monorepo map

| Path | Milestone | Role |
|------|-----------|------|
| `services/health-api` | M0–M6 | FastAPI, Alembic, FHIR-aligned storage |
| `apps/hospital-a-demo` | M2 | Prescribe + sync UI (`:5173`) |
| `apps/hospital-b-demo` | M2 | History + prefill fields (`:5174`) |
| `extension/` | M3 | Chrome/Edge MV3 side panel |
| `apps/web-patient` | M4 | Patient portal (`:5175`) |
| `apps/mobile` | M4 | Expo digital card |
| `apps/web-admin` | M5 | Ops dashboard (`:5176`) |
| `apps/web-marketing` | M5 | Public shell (`:5177`) |
| `packages/*` | stubs | shared-types / fhir-mapping placeholders |
| `infra/` | M0 | docker-compose |

## Auth model

| Actor | Mechanism | Notes |
|-------|-----------|--------|
| Demo staff | `POST /api/v1/auth/session` + `DEMO_*` | Not hospital IdP / MFA |
| Patient | `POST /api/v1/auth/patient/register\|login` + OTP stub `123456` | Synthetic accounts |
| Extension / demos | Bearer JWT in SW / memory | Tokens not injected into page DOM for auth |

## Sync rules

- Only `final` / `approved` + `local_saved` events accepted.
- Idempotency key = `source_org_id + source_record_id + version`.
- Status: `queued` → `sent` → `confirmed` | `failed` (+ retry).
- Stored as FHIR-aligned `MedicationRequest` JSON in `fhir_resources` with provenance.

## Data (Alembic)

| Revision | Contents |
|----------|----------|
| `20261101_0001` | organizations, users |
| `20261101_0002` | patients, qr_tokens, consents, audit, stubs, Hospital A/B seed |
| `20261101_0003` | integration_events columns for sync |
| `20261101_0004` | org `is_active`, `approval_status` |

## Out of Phase 1

Real EHR connectors, production OIDC/MFA, billing, family profiles, break-glass emergency access, App Store release polish.
