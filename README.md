# Universal Health QR

Phase 1 monorepo for the Universal Health QR prototype (FastAPI + PostgreSQL on Flowlab, Expo patient app, portals, hospital demos, MV3 extension).

**Current milestone:** **M3 — Chrome/Edge MV3 extension** (side panel, QR resolve, Hospital B confirmed prefill). M2 demos + sync and M0/M1 APIs remain intact.

**Demo auth** is for development/testing only — not production hospital authentication. See `docs/demo-script.md` and `docs/m1-backup-checklist.md`.

## Layout

```
apps/
  hospital-a-demo/   # Harborview A — prescribe + post-save sync
  hospital-b-demo/   # Ridge Clinic B — retrieve synced history
  …                  # mobile, web-patient, marketing, admin (placeholders)
services/health-api/ # FastAPI application
extension/           # MV3 placeholder
packages/            # shared-types, fhir-mapping stubs
infra/               # docker-compose.yml + migration notes
docs/                # architecture, security, deploy, demo script
```

## Prerequisites

- Python 3.11+ (3.12 recommended for Docker image)
- Node 20+ (for hospital demos)
- Docker Desktop **or** local PostgreSQL (for migrations)
- Git

## Quick start (Docker)

```powershell
cd "D:\My Team Projects\QrCode-Card"
Copy-Item .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Optional Adminer UI:

```powershell
docker compose -f infra/docker-compose.yml --profile tools up --build
```

- API: http://localhost:8000  
- Health: http://localhost:8000/health → `{"status":"ok"}`  
- Swagger: http://localhost:8000/docs  
- Adminer (tools profile): http://localhost:8080  

## Quick start (local Python, no Docker)

```powershell
cd "D:\My Team Projects\QrCode-Card\services\health-api"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\..\.env.example ..\..\.env   # if not already
# Set DATABASE_URL in .env if you have Postgres; /health works without DB
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run migrations when Postgres is available:

```powershell
cd services/health-api
alembic upgrade head
```

## Hospital A / B demos (M2)

Against production Flowlab API (default) or local API:

```powershell
# Hospital A — http://localhost:5173
cd apps/hospital-a-demo
npm install
npm run dev

# Hospital B — http://localhost:5174
cd apps/hospital-b-demo
npm install
npm run dev
```

Set `VITE_API_BASE` in each app’s `.env` (see `.env.example`). Full A→cloud→B script: [`docs/demo-script.md`](docs/demo-script.md).

## Demo auth (stub)

```http
POST /api/v1/auth/session
Content-Type: application/json

{"username":"demo@health.local","password":"demo-password-change-me","org_name":"Demo Hospital A"}
```

Optional `org_name`: `Demo Hospital A` or `Demo Hospital B` stamps `org_id` on the JWT. Override credentials with `DEMO_USERNAME` / `DEMO_PASSWORD`.

## Key M2 API routes

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/api/v1/integration-events` | Final/approved only; idempotent |
| `GET` | `/api/v1/sync-events/{id}` | `queued` \| `sent` \| `confirmed` \| `failed` |
| `POST` | `/api/v1/sync-events/{id}/retry` | Failed events |
| `GET` | `/api/v1/patients/{id}/records` | Auth + consent required |
| `GET` | `/api/v1/patients` | List / UHID lookup |
| `GET` | `/api/v1/organizations` | Demo hospitals |

## Flowlab / production DATABASE_URL

Set on the host only (never commit):

```text
DATABASE_URL=postgresql+psycopg://QR:<PASSWORD>@qrcodecard-srwlkj:5432/code
APP_ENV=production
CORS_ORIGINS=https://your-frontends.example,http://localhost:5173,http://localhost:5174
JWT_SECRET=<strong-secret>
```

Deploy notes: [`docs/deploy-flowlab.md`](docs/deploy-flowlab.md).

Production URL: https://codebase.flowlab.fun/ — confirm `/health` returns 200 after deploy.

## Environment variables

See [`.env.example`](.env.example). Key settings:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL |
| `APP_ENV` | `development` / `production` |
| `CORS_ORIGINS` | Comma-separated origins (include demo Vite ports) |
| `JWT_SECRET` | JWT signing secret |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | Session stub |

## Docs

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/security.md`](docs/security.md)
- [`docs/demo-script.md`](docs/demo-script.md)
- [`docs/deploy-flowlab.md`](docs/deploy-flowlab.md)
