# Demo script

Synthetic data only. Demo authentication is **not** hospital-grade MFA/OIDC.

## M0 — foundation

1. Clone repo and copy `.env.example` → `.env`.
2. Start API (venv or Docker Compose).
3. `GET /health` → `{"status":"ok"}`.
4. Open `/docs`.
5. `POST /api/v1/auth/session` with demo user → JWT.

## M1 — patients, UHID, opaque QR (synthetic)

**Prerequisite:** PostgreSQL backup confirmed before production redeploy (`docs/m1-backup-checklist.md`). User may waive backups for demo environments.

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

## M2 — Hospital A → Universal Health Cloud → Hospital B

Prescription sync is **post-save only** (final/approved). Drafts are rejected. Idempotency key = `source_org_id + source_record_id + version`.

### UI demos (local against Flowlab API)

```powershell
# Terminal 1 — Harborview A (prescription + sync)
cd "D:\My Team Projects\QrCode-Card\apps\hospital-a-demo"
npm install
npm run dev
# http://localhost:5173

# Terminal 2 — Ridge Clinic B (retrieve history)
cd "D:\My Team Projects\QrCode-Card\apps\hospital-b-demo"
npm install
npm run dev
# http://localhost:5174
```

Default `VITE_API_BASE=https://codebase.flowlab.fun`. Override in each app’s `.env` for localhost API.

**Walkthrough**

1. In Hospital A: auto-login as demo staff for Demo Hospital A → register or select a synthetic patient → enter medication + dose source text → **Save final & sync to cloud**.
2. Confirm sync status becomes `confirmed` (polls `GET /api/v1/sync-events/{id}`).
3. Copy the patient’s UHID (or QR token from registration response).
4. In Hospital B: paste UHID / QR token → **Load synced history** → see MedicationRequest with provenance `Demo Hospital A`.

### API-only walkthrough (PowerShell / curl)

```powershell
$Base = "https://codebase.flowlab.fun"

# Hospital A session
$sa = Invoke-RestMethod -Method POST "$Base/api/v1/auth/session" -ContentType "application/json" -Body '{"username":"demo@health.local","password":"demo-password-change-me","org_name":"Demo Hospital A"}'
$Ha = @{ Authorization = "Bearer $($sa.access_token)" }

# Register synthetic patient (consents A+B by default)
$reg = Invoke-RestMethod -Method POST "$Base/api/v1/patients" -Headers $Ha -ContentType "application/json" -Body '{"display_name":"Synthetic M2 Bridge"}'
$PatientId = $reg.id
$Uhid = $reg.uhid

# Final prescription sync (not a draft)
$rxBody = @{
  patient_id = $PatientId
  source_org_name = "Demo Hospital A"
  source_record_id = "rx-demo-$(Get-Random)"
  version = 1
  medication_text = "Amoxicillin 500mg"
  dose_text = "1 capsule twice daily for 7 days"
  status = "final"
  local_saved = $true
} | ConvertTo-Json
$evt = Invoke-RestMethod -Method POST "$Base/api/v1/integration-events" -Headers $Ha -ContentType "application/json" -Body $rxBody
# Expect status confirmed; retry same payload → duplicate=true, same event id

$sync = Invoke-RestMethod -Method GET "$Base/api/v1/sync-events/$($evt.id)" -Headers $Ha

# Hospital B session + records
$sb = Invoke-RestMethod -Method POST "$Base/api/v1/auth/session" -ContentType "application/json" -Body '{"username":"demo@health.local","password":"demo-password-change-me","org_name":"Demo Hospital B"}'
$Hb = @{ Authorization = "Bearer $($sb.access_token)" }
$records = Invoke-RestMethod -Method GET "$Base/api/v1/patients/$PatientId/records" -Headers $Hb
# Expect MedicationRequest from Demo Hospital A
```

### Acceptance checks

| Check | Expected |
|-------|----------|
| Draft `status` | HTTP 422, audit deny |
| Same idempotency key retry | HTTP 200, same event, no duplicate FHIR row |
| Sync statuses | `queued` → `sent` → `confirmed` (or `failed` + retry) |
| Hospital B records | Authorized + consented; unauthorized → 403 + audit |
| QR payload | Still opaque — no medication text in token |

## M3 — Chrome / Edge extension

See [`extension/README.md`](../extension/README.md).

1. Run Hospital A (`:5173`) and Hospital B (`:5174`).
2. `chrome://extensions` → Developer mode → **Load unpacked** → `extension/` folder.
3. Open side panel → demo login (Hospital B org for read path).
4. After M2 sync: paste opaque QR token → **Resolve & load history**.
5. On Hospital B tab: **Prefill demographics (confirm)** → only approved `data-uhq-field` inputs fill.
6. On Hospital A tab: sync status marker may appear in side panel when a save is confirmed.
