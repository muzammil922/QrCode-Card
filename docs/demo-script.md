# Demo script

Synthetic data only. Demo authentication is **not** hospital-grade MFA/OIDC.

## M0 — foundation

1. Clone repo and copy `.env.example` → `.env`.
2. Start API (venv or Docker Compose).
3. `GET /health` → `{"status":"ok"}`.
4. Open `/docs`.
5. `POST /api/v1/auth/session` with demo user → JWT.

## M1 — patients, UHID, opaque QR (synthetic)

**Prerequisite:** PostgreSQL backup confirmed before production redeploy (`docs/m1-backup-checklist.md`).

### Live (Flowlab)

Base URL: `https://codebase.flowlab.fun`

```bash
# 1) Demo session (dev/test stub only)
curl -s -X POST https://codebase.flowlab.fun/api/v1/auth/session \
  -H "Content-Type: application/json" \
  -d '{"username":"demo@health.local","password":"demo-password-change-me"}'

# 2) Register synthetic patient (use access_token from step 1)
curl -s -X POST https://codebase.flowlab.fun/api/v1/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Synthetic Patient Zero","date_of_birth":"1990-01-15"}'

# 3) Resolve QR (opaque token from card.qr_token — no PHI in token)
curl -s "https://codebase.flowlab.fun/api/v1/patients/resolve-qr?token=$QR" \
  -H "Authorization: Bearer $TOKEN"

# 4) Revoke + replacement
curl -s -X POST "https://codebase.flowlab.fun/api/v1/patients/$PATIENT_ID/qr/revoke?replace=true" \
  -H "Authorization: Bearer $TOKEN"

# 5) Old token must fail; list audit
curl -s "https://codebase.flowlab.fun/api/v1/audit-events?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

Or use Swagger: https://codebase.flowlab.fun/docs

### Local tests

```powershell
cd services/health-api
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

## Later milestones

Hospital A/B demos, extension, prescription sync, §14 full acceptance — M2+.
