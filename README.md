# Universal Health QR

Phase 1 monorepo for the Universal Health QR prototype (FastAPI + PostgreSQL on Flowlab, Expo patient app, portals, hospital demos, MV3 extension).

**Current milestone:** **M0 — Foundation** (API scaffold, Docker Compose, migrations, docs).

## Layout

```
apps/                  # mobile, web-patient, web-marketing, web-admin, hospital demos (placeholders)
services/health-api/   # FastAPI application
extension/             # MV3 placeholder
packages/              # shared-types, fhir-mapping stubs
infra/                 # docker-compose.yml + migration notes
docs/                  # architecture, security, deploy, demo script
```

## Prerequisites

- Python 3.11+ (3.12 recommended for Docker image)
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

## Demo auth (M0 stub)

```http
POST /api/v1/auth/session
Content-Type: application/json

{"username":"demo@health.local","password":"demo-password-change-me"}
```

Override with `DEMO_USERNAME` / `DEMO_PASSWORD` in `.env`.

## Flowlab / production DATABASE_URL

Set on the host only (never commit):

```text
DATABASE_URL=postgresql+psycopg://QR:<PASSWORD>@qrcodecard-srwlkj:5432/code
APP_ENV=production
CORS_ORIGINS=https://your-frontends.example
JWT_SECRET=<strong-secret>
```

Deploy notes and 502 remediation: [`docs/deploy-flowlab.md`](docs/deploy-flowlab.md).

Production URL: https://codebase.flowlab.fun/ — confirm `/health` returns 200 after deploy.

## Environment variables

See [`.env.example`](.env.example). Key settings:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL |
| `APP_ENV` | `development` / `production` |
| `CORS_ORIGINS` | Comma-separated origins |
| `JWT_SECRET` | JWT signing secret |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | M0 session stub |

## Docs

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/security.md`](docs/security.md)
- [`docs/demo-script.md`](docs/demo-script.md)
- [`docs/deploy-flowlab.md`](docs/deploy-flowlab.md)
