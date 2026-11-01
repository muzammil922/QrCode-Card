from fastapi import APIRouter

from app.api.v1 import audit, auth, consents, patients

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(consents.router)
api_router.include_router(audit.router)
