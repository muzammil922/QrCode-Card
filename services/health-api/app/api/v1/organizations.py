import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.organization import Organization

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    org_type: str
    created_at: datetime


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List organizations (demo hospitals)",
)
def list_organizations(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[OrganizationResponse]:
    _ = principal
    rows = db.query(Organization).order_by(Organization.name.asc()).all()
    return [
        OrganizationResponse(
            id=r.id,
            name=r.name,
            org_type=r.org_type.value if hasattr(r.org_type, "value") else str(r.org_type),
            created_at=r.created_at,
        )
        for r in rows
    ]
