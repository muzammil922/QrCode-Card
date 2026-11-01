import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.consent import Consent
from app.models.organization import Organization
from app.models.patient import Patient
from app.services.audit import write_audit

router = APIRouter(prefix="/consents", tags=["consents"])


class CreateConsentRequest(BaseModel):
    patient_id: uuid.UUID
    grantee_org_id: uuid.UUID
    purpose: str = Field(default="treatment", max_length=128)
    categories: dict[str, Any] = Field(default_factory=lambda: {"records": ["summary"]})


class ConsentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    grantee_org_id: uuid.UUID
    purpose: str
    categories: dict[str, Any]
    valid_from: datetime
    revoked_at: datetime | None


@router.post(
    "",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant organization access (synthetic consent)",
)
def create_consent(
    body: CreateConsentRequest,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ConsentResponse:
    if not db.query(Patient).filter(Patient.id == body.patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.query(Organization).filter(Organization.id == body.grantee_org_id).first():
        raise HTTPException(status_code=404, detail="Organization not found")

    consent = Consent(
        patient_id=body.patient_id,
        grantee_org_id=body.grantee_org_id,
        purpose=body.purpose,
        categories=body.categories,
    )
    db.add(consent)
    write_audit(
        db,
        actor=principal.subject,
        action="consent.create",
        resource_type="consent",
        resource_id=None,
        decision="allow",
        detail={
            "patient_id": str(body.patient_id),
            "grantee_org_id": str(body.grantee_org_id),
        },
    )
    db.commit()
    db.refresh(consent)
    return ConsentResponse(
        id=consent.id,
        patient_id=consent.patient_id,
        grantee_org_id=consent.grantee_org_id,
        purpose=consent.purpose,
        categories=consent.categories,
        valid_from=consent.valid_from,
        revoked_at=consent.revoked_at,
    )
