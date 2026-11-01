# Deploy to Flowlab / Dokploy (`codebase.flowlab.fun`)

**Target:** FastAPI health-api in `services/health-api/`.  
**Domain:** `https://codebase.flowlab.fun` → container port (Dokploy injects `PORT`; app listens on `${PORT:-8000}`).

This monorepo root is **not** a single Nixpacks-detectable app. Either use a **Dockerfile** (preferred) or the root **`nixpacks.toml`**.

## Exact Dokploy UI settings (preferred: Dockerfile)

Use **one** of these build setups:

### Option 1 — Subdirectory Dockerfile (best)

- **Build type:** Dockerfile
- **Dockerfile path:** `services/health-api/Dockerfile`
- **Docker context / build context:** `services/health-api` (or `.` only if your panel requires root and you switch to Option 2)
- **Publish / container port:** `8000` (or whatever Dokploy maps; see PORT note below)
- **Watch / auto-deploy:** `main` branch of `muzammil922/QrCode-Card`

### Option 2 — Root Dockerfile (context = repo root)

- **Build type:** Dockerfile
- **Dockerfile path:** `Dockerfile` (repo root)
- **Docker context:** `.` (repository root)
- Same port / domain settings as Option 1

### Option 3 — Nixpacks (fallback)

- **Build type:** Nixpacks
- Root `nixpacks.toml` forces Python 3.12, installs `services/health-api/requirements.txt`, runs alembic + uvicorn
- Do **not** leave Build type = Nixpacks without `nixpacks.toml` — Nixpacks cannot plan from the empty monorepo root

### Option 4 — Application base directory (if Dokploy shows it)

- **Application source / base directory:** `services/health-api`
- Then Build type = Dockerfile with Dockerfile path `Dockerfile` (relative to that directory), **or** Nixpacks with that subdirectory as the app root (it contains `requirements.txt` + `Dockerfile`)

## Domain / proxy

- **Domain:** `codebase.flowlab.fun`
- **Proxy / upstream:** map the domain to the **container port** Dokploy assigns
- App binds **`0.0.0.0`** and port **`${PORT:-8000}`**
- If Dokploy sets `PORT` (common on PaaS), leave container listen port as that value and point the proxy at it
- If Dokploy does **not** set `PORT`, the process listens on **8000** — set published/proxy port to **8000**
- Health path for probes: **`GET /health`** → `200` + `{"status":"ok"}`
- OpenAPI: `/docs`

## Required environment variables (Dokploy → Environment)

Set in the panel / secrets — **never commit**:

| Variable | Example / notes |
|----------|-----------------|
| `DATABASE_URL` | `postgresql+psycopg://QR:<PASSWORD>@qrcodecard-srwlkj:5432/code` |
| `APP_ENV` | `production` |
| `JWT_SECRET` | Strong random secret |
| `CORS_ORIGINS` | Allowed front-end origins (comma-separated) |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | M0 stub only; rotate or disable for shared demos |
| `PORT` | Optional — Dokploy often injects this; app uses `${PORT:-8000}` |

## Migrations

The Docker/`start.sh` and Nixpacks start commands run:

```bash
alembic upgrade head
```

before uvicorn. Ensure Postgres is reachable via `DATABASE_URL` **before** the first deploy, or the container will exit on migration failure.

To run migrations manually (SSH / one-off):

```bash
cd services/health-api && alembic upgrade head
```

## After changing build settings

1. Save Dokploy settings (Dockerfile path + env vars + domain → port).
2. **Redeploy** the application (pull latest `main`).
3. Verify:

```bash
curl -i https://codebase.flowlab.fun/health
curl -i https://codebase.flowlab.fun/docs
```

Expect `200` for `/health`.

## Diagnosing 502

| Check | What to look for |
|-------|------------------|
| Build failed (Nixpacks plan) | Switch to Dockerfile or confirm `nixpacks.toml` is on `main` |
| Container / process running? | Crash loops, OOM, missing deps |
| Listening port vs proxy | Proxy upstream port ≠ process `PORT` / 8000 |
| `DATABASE_URL` | Wrong host/password → alembic fails at start |
| Logs | Dokploy / Docker logs around last deploy |
| TLS / path | HTTPS at edge; `/health` not rewritten away |

## Local Docker Compose

`infra/docker-compose.yml` builds `services/health-api` and publishes `${API_PORT:-8000}:8000`.

## Access checklist (user)

- [ ] Dokploy / Flowlab login
- [ ] Build type = Dockerfile (preferred) with path above
- [ ] Env vars set (`DATABASE_URL`, `APP_ENV`, JWT/demo, CORS)
- [ ] Domain `codebase.flowlab.fun` → container port
- [ ] Redeploy after merging these deploy files to `main`
- [ ] `curl https://codebase.flowlab.fun/health` → 200
