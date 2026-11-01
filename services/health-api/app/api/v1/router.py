from fastapi import APIRouter

from app.api.v1 import (
    admin,
    audit,
    auth,
    consents,
    integration_events,
    organizations,
    patient_auth,
    patients,
    sync_events,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patient_auth.router)
api_router.include_router(patients.router)
api_router.include_router(consents.router)
api_router.include_router(audit.router)
api_router.include_router(organizations.router)
api_router.include_router(integration_events.router)
api_router.include_router(sync_events.router)
api_router.include_router(admin.router)
