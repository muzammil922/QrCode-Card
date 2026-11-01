# Demo script (stub)

Full §14 acceptance lives in later milestones. **M0 demo** (local):

1. Clone repo and copy `.env.example` → `.env`.
2. Start stack: `docker compose -f infra/docker-compose.yml up --build`.
3. Open `http://localhost:8000/health` → `{"status":"ok"}`.
4. Open `http://localhost:8000/docs` → Swagger UI loads.
5. `POST /api/v1/auth/session` with demo user → JWT returned.
6. Confirm Alembic applied (`organizations`, `users` exist in Postgres / Adminer).

See README and `docs/deploy-flowlab.md` for Flowlab once hosting access is available.
