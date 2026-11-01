# Deploy to Flowlab (`codebase.flowlab.fun`)

**Current status (verified 2026-11-01):** `https://codebase.flowlab.fun/health` returns **HTTP 502 Bad Gateway**. The edge proxy is up; the upstream app process is not healthy or not reachable. This agent has **no SSH / Flowlab panel access**, so remediating production requires your host credentials.

## What the API expects

- Process: `uvicorn app.main:app --host 0.0.0.0 --port <PORT>`
- Health check path for reverse proxy: **`GET /health`** → `200` + `{"status":"ok"}`
- OpenAPI: `/docs`
- Env (set in Flowlab panel / secrets — never commit):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `postgresql+psycopg://QR:<PASSWORD>@qrcodecard-srwlkj:5432/code` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | Allowed front-end origins (comma-separated) |
| `JWT_SECRET` | Strong random secret |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | M0 stub only; disable or rotate for shared demos |

## Suggested deploy steps (you run on Flowlab)

1. **Open Flowlab panel / SSH** for the app behind `codebase.flowlab.fun`.
2. **Pull** this repo (or upload build artifacts) so `services/health-api` is on the host.
3. **Build** using `services/health-api/Dockerfile`, or install Python 3.12+ and `pip install -r requirements.txt`.
4. **Set env vars** (especially `DATABASE_URL`) in the panel or systemd/Docker env.
5. **Run migrations:** `cd services/health-api && alembic upgrade head`.
6. **Start** uvicorn (or `docker compose` equivalent) listening on the **same port** the reverse proxy forwards to (common: `8000` or `80` inside the container).
7. **Point the proxy** at that upstream; ensure health check uses `/health`.
8. **Verify:**
   ```bash
   curl -i https://codebase.flowlab.fun/health
   curl -i https://codebase.flowlab.fun/docs
   ```
   Expect `200` for `/health`.

## Diagnosing 502

| Check | What to look for |
|-------|------------------|
| Container / process running? | Restarted crash loops, OOM, missing Python deps |
| Listening port vs proxy | Proxy upstream port mismatch is the #1 cause |
| `DATABASE_URL` | Wrong host/password can crash startup if you add DB-required boot hooks; M0 `/health` itself does not require DB |
| Logs | Flowlab / Docker logs around last deploy |
| TLS / path | Confirm HTTPS terminates at proxy and `/health` is not rewritten away |

## Dockerfile

Use `services/health-api/Dockerfile`. It runs `alembic upgrade head` then uvicorn on port **8000**. Expose that port to the Flowlab reverse proxy.

## Access checklist (user)

- [ ] Flowlab login (panel or SSH)
- [ ] Ability to set env vars and view logs
- [ ] Confirm Postgres `code` reachable from the API host
- [ ] Map domain `codebase.flowlab.fun` → healthy container port
- [ ] GitHub push access for continuous deploys (optional CI later)
