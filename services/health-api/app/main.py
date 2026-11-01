from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Universal Health QR — Phase 1 health-api (M0 foundation)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe — always 200 when the process is up."""
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "env": settings.app_env,
        "docs": "/docs",
        "health": "/health",
    }
