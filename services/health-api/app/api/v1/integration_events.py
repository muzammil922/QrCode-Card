import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.integration_event import IntegrationEvent
from app.services.audit import write_audit
from app.services.sync import (
    DRAFT_STATUSES,
    FINAL_STATUSES,
    SOURCE_HOSPITAL_A,
    make_idempotency_key,
    process_integration_event,
    resolve_patient,
    resolve_source_org,
)

router = APIRouter(prefix="/integration-events", tags=["integration-events"])


class IntegrationEventRequest(BaseModel):
    patient_id: uuid.UUID | None = None
    uhid: str | None = Field(default=None, max_length=64)
    source_org_id: uuid.UUID | None = None
    source_org_name: str | None = Field(default=None, max_length=255)
    source_record_id: str = Field(..., min_length=1, max_length=128)
    version: int = Field(..., ge=1)
    medication_text: str = Field(..., min_length=1, max_length=512)
    dose_text: str = Field(..., min_length=1, max_length=512)
    status: Literal["final", "approved", "draft", "preliminary"] = "final"
    authored_on: str | None = None
    local_saved: bool = Field(
        default=True,
        description="Caller affirms local EHR save succeeded before cloud sync",
    )

    @model_validator(mode="after")
    def require_patient_ref(self) -> "IntegrationEventRequest":
        if self.patient_id is None and not self.uhid:
            raise ValueError("patient_id or uhid is required")
        if self.source_org_id is None and not self.source_org_name:
            raise ValueError("source_org_id or source_org_name is required")
        return self


class IntegrationEventResponse(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    status: str
    patient_id: uuid.UUID | None
    source_org_id: uuid.UUID | None
    source_record_id: str | None
    version: int | None
    retry_count: int
    error_message: str | None
    fhir_resource_id: uuid.UUID | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    duplicate: bool = False


def _to_response(
    event: IntegrationEvent, *, duplicate: bool = False
) -> IntegrationEventResponse:
    return IntegrationEventResponse(
        id=event.id,
        idempotency_key=event.idempotency_key,
        status=event.status,
        patient_id=event.patient_id,
        source_org_id=event.source_org_id,
        source_record_id=event.source_record_id,
        version=event.version,
        retry_count=event.retry_count,
        error_message=event.error_message,
        fhir_resource_id=event.fhir_resource_id,
        processed_at=event.processed_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
        duplicate=duplicate,
    )


@router.post(
    "",
    response_model=IntegrationEventResponse,
    summary="Accept final prescription sync event (idempotent)",
)
def create_integration_event(
    body: IntegrationEventRequest,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> IntegrationEventResponse:
    if principal.role not in ("demo", "staff", "admin"):
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "role_not_allowed", "role": principal.role},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller role cannot submit integration events",
        )

    if not body.local_saved:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "local_save_required"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cloud sync only after successful local prescription save",
        )

    status_norm = body.status.lower().strip()
    if status_norm in DRAFT_STATUSES or status_norm not in FINAL_STATUSES:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "draft_or_non_final", "status": status_norm},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only final/approved prescriptions may sync — drafts rejected",
        )

    org = resolve_source_org(
        db, source_org_id=body.source_org_id, source_org_name=body.source_org_name
    )
    if org is None:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "source_org_not_found"},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Source organization not found")

    if org.name != SOURCE_HOSPITAL_A:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "source_org_not_hospital_a", "org": org.name},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo sync accepts source_org Demo Hospital A only",
        )

    if principal.org_id and str(org.id) != str(principal.org_id):
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "org_mismatch", "token_org": principal.org_id},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token org_id must match source_org",
        )

    patient = resolve_patient(db, patient_id=body.patient_id, uhid=body.uhid)
    if patient is None:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=None,
            decision="deny",
            detail={"reason": "patient_not_found"},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Patient not found")

    key = make_idempotency_key(org.id, body.source_record_id, body.version)
    existing = (
        db.query(IntegrationEvent)
        .filter(IntegrationEvent.idempotency_key == key)
        .first()
    )
    if existing is not None:
        write_audit(
            db,
            actor=principal.subject,
            action="integration_event.accept",
            resource_type="integration_event",
            resource_id=str(existing.id),
            decision="allow",
            detail={"idempotent": True, "status": existing.status},
        )
        db.commit()
        return _to_response(existing, duplicate=True)

    payload: dict[str, Any] = {
        "medication_text": body.medication_text.strip(),
        "dose_text": body.dose_text.strip(),
        "status": status_norm,
        "authored_on": body.authored_on,
        "uhid": patient.uhid,
        "display_name": patient.display_name,
        "source_org_name": org.name,
    }
    event = IntegrationEvent(
        idempotency_key=key,
        status="queued",
        payload=payload,
        retry_count=0,
        patient_id=patient.id,
        source_org_id=org.id,
        source_record_id=body.source_record_id,
        version=body.version,
    )
    db.add(event)
    db.flush()

    write_audit(
        db,
        actor=principal.subject,
        action="integration_event.accept",
        resource_type="integration_event",
        resource_id=str(event.id),
        decision="allow",
        detail={"idempotency_key": key, "status": "queued"},
    )

    process_integration_event(db, event)
    write_audit(
        db,
        actor=principal.subject,
        action="integration_event.process",
        resource_type="integration_event",
        resource_id=str(event.id),
        decision="allow" if event.status == "confirmed" else "deny",
        detail={
            "status": event.status,
            "fhir_resource_id": str(event.fhir_resource_id)
            if event.fhir_resource_id
            else None,
            "error": event.error_message,
        },
    )
    db.commit()
    db.refresh(event)
    return _to_response(event)
