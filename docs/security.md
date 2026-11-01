# Security & privacy — Phase 1 prototype

## Non-negotiables

1. **QR payloads are opaque** — never CNIC, name, diagnosis, or medication text in the code.
2. **Scan ≠ access** — staff/patient JWT + server authorization + consent checks on reads.
3. **No draft sync** — integration events require final/approved + successful local save.
4. **No silent EHR write-back** — Hospital B prefill only after explicit confirmation; allowlisted origins only.
5. **Synthetic data only** in Phase 1 — no real patients or live hospital systems without written authorization.
6. **Secrets** in host env / Dokploy only — never commit `.env` passwords.

## Auth posture (honest limits)

| Component | Status |
|-----------|--------|
| Demo staff session | Env password stub — **not** production hospital auth |
| Patient OTP | Fixed `123456` for prototype — replace before any real pilot |
| JWT | HS256 with `JWT_SECRET`; rotate on shared hosts |
| MFA / OIDC | Deferred to Phase 2+ |

## Tenancy & consent

- Organizations seeded as Demo Hospital A/B.
- Patient registration grants treatment consents to those orgs by default (demo).
- Record reads require role checks; patients may only access `/me*` for their linked patient_id.
- Unauthorized / revoked QR / wrong org → HTTP deny + **audit_events** row.

## Extension surface

- MV3; `host_permissions` limited to localhost demo ports + API origin.
- Credentials in `chrome.storage` / service worker — not written into page DOM for login.
- Camera permission only on user-initiated scan; USB/NFC HID wedge supported as keyboard input.

## Admin surface

- `/admin/*` returns **aggregates** and org status stubs — not a bulk clinical browser.
- Org approve/suspend is audited.

## Operational

- Prefer TLS everywhere (Flowlab HTTPS).
- CORS merges localhost Vite ports for demos; production `CORS_ORIGINS` should list real frontends.
- Failed syncs retained for retry; do not silently discard.
- Independent penetration test + DPIA required before any real-world deployment (Phase 3 gate).

## Incident basics (prototype)

1. Rotate `JWT_SECRET`, demo passwords, DB password.
2. Revoke QR tokens via patient card rotate / revoke API.
3. Suspend org via admin stub if needed.
4. Review `GET /api/v1/audit-events`.
