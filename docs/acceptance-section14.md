# §14 Acceptance checklist — Phase 1 complete

Synthetic data only. Run against **Flowlab** (`https://codebase.flowlab.fun`) plus local demos/extension as noted.

Automated runner: [`scripts/acceptance-section14.ps1`](../scripts/acceptance-section14.ps1)

| # | Criterion | How verified | Pass? |
|---|-----------|--------------|-------|
| 1 | Register synthetic patient → unique UHID | `acceptance-section14.ps1` + pytest | ✅ 2026-11-01 |
| 2 | QR contains no direct PHI | Opaque `qr_token`; no name/meds in payload | ✅ 2026-11-01 |
| 3 | Hospital A creates & saves synthetic prescription | `POST /integration-events` final → confirmed | ✅ 2026-11-01 |
| 4 | Integration event only after successful save | Drafts → 422; final + `local_saved` only | ✅ 2026-11-01 |
| 5 | Idempotent store on retry | Same key → same event id, `duplicate=true` | ✅ 2026-11-01 |
| 6 | Hospital B authorized user scans QR → history | B resolve-qr + records include A medication | ✅ 2026-11-01 |
| 7 | Hospital B adapter prefills after confirm | Extension **Prefill (confirm)** on `:5174` | ☐ Manual |
| 8 | Extension sync status reflects backend | A sync-events API / `data-uhq-sync-status` (API path) | ✅ 2026-11-01 |
| 9 | Unauthorized / revoked / bad token denied + audited | 401 / revoked QR 404 / audit deny rows | ✅ 2026-11-01 |
| 10 | No real patient data / live hospital system | Synthetic flags + demo orgs only | ✅ By design |

### Extra Phase 1 channels (M4–M5)

| Item | Pass? |
|------|-------|
| Patient portal / Expo shows synced prescription after Hospital A save | ✅ API `/me/records` 2026-11-01 |
| Admin stats + audit visible without bulk clinical dump | ✅ `/admin/stats` 2026-11-01 |
| Marketing shell loads (local `:5177`) | ✅ M5 delivered |

**Last automated Flowlab run:** 2026-11-01 — `scripts/acceptance-section14.ps1` → ALL AUTOMATED §14 API CHECKS PASSED. Pytest: 16 passed.

**Remaining manual:** item 7 — load Hospital B (`:5174`), scan/resolve via extension, click **Prefill (confirm)**.

**Phase 1 sign-off:** Product owner confirms this checklist after witnessing the Flowlab + demo walkthrough (incl. item 7).

Owner: ________________  Date: ________________
