# Monorepo-root Dockerfile for Dokploy / Flowlab when build context is the repo root.
# Preferred alternative (smaller context): Build type=Dockerfile,
#   Dockerfile path = services/health-api/Dockerfile
#   Docker context   = services/health-api
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/health-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/health-api/ .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1'

# Bind all interfaces; honor PaaS PORT (Dokploy) when set.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
