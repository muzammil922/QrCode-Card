# Database migrations

Canonical Alembic migrations live under `services/health-api/alembic/`.

Run from the health-api directory (or via Docker Compose on API start):

```bash
cd services/health-api
alembic upgrade head
```

This folder is reserved for SQL dumps / ops scripts that are not Alembic revisions.
