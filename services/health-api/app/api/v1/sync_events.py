import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.integration_event import IntegrationEvent
from app.services.audit import write_audit
from app.services.sync import process_integration_event

router = APIRouter(prefix="/sync-events", tags=["sync-events"])

SyncStatus = Literal["queued", "sent", "confirmed", "failed"]


class SyncEventResponse(BaseModel):
    id: uuid.UUID
    status: SyncStatus
    idempotency_key: str
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


def _to_response(event: IntegrationEvent) -> SyncEventResponse:
    return SyncEventResponse(
        id=event.id,
        status=event.status,  # type: ignore[arg-type]
        idempotency_key=event.idempotency_key,
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
    )


@router.get(
    "/{event_id}",
    response_model=SyncEventResponse,
    summary="Get sync status (queued|sent|confirmed|failed)",
)
def get_sync_event(
    event_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> SyncEventResponse:
    event = db.query(IntegrationEvent).filter(IntegrationEvent.id == event_id).first()
    if event is None:
        write_audit(
            db,
            actor=principal.subject,
            action="sync_event.read",
            resource_type="integration_event",
            resource_id=str(event_id),
            decision="deny",
            detail={"reason": "not_found"},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Sync event not found")

    write_audit(
        db,
        actor=principal.subject,
        action="sync_event.read",
        resource_type="integration_event",
        resource_id=str(event.id),
        decision="allow",
        detail={"status": event.status},
    )
    db.commit()
    return _to_response(event)


@router.post(
    "/{event_id}/retry",
    response_model=SyncEventResponse,
    summary="Retry a failed sync event",
)
def retry_sync_event(
    event_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> SyncEventResponse:
    if principal.role not in ("demo", "staff", "admin"):
        write_audit(
            db,
            actor=principal.subject,
            action="sync_event.retry",
            resource_type="integration_event",
            resource_id=str(event_id),
            decision="deny",
            detail={"reason": "role_not_allowed"},
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Caller role cannot retry sync")

    event = db.query(IntegrationEvent).filter(IntegrationEvent.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Sync event not found")

    if event.status == "confirmed":
        write_audit(
            db,
            actor=principal.subject,
            action="sync_event.retry",
            resource_type="integration_event",
            resource_id=str(event.id),
            decision="allow",
            detail={"noop": True, "status": "confirmed"},
        )
        db.commit()
        return _to_response(event)

    if event.status not in ("failed", "queued", "sent"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retry event in status {event.status}",
        )

    event.status = "queued"
    process_integration_event(db, event)
    write_audit(
        db,
        actor=principal.subject,
        action="sync_event.retry",
        resource_type="integration_event",
        resource_id=str(event.id),
        decision="allow" if event.status == "confirmed" else "deny",
        detail={"status": event.status, "retry_count": event.retry_count},
    )
    db.commit()
    db.refresh(event)
    return _to_response(event)
