from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    consents,
    integration_events,
    organizations,
    patients,
    sync_events,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(consents.router)
api_router.include_router(audit.router)
api_router.include_router(organizations.router)
api_router.include_router(integration_events.router)
api_router.include_router(sync_events.router)
