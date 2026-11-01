import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.audit_event import AuditEvent

router = APIRouter(prefix="/audit-events", tags=["audit"])


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    decision: str
    detail: dict[str, Any]
    created_at: datetime


@router.get(
    "",
    response_model=list[AuditEventResponse],
    summary="List recent audit events (demo/admin)",
)
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AuditEventResponse]:
    _ = principal  # auth required; demo role allowed in M1
    rows = (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AuditEventResponse(
            id=r.id,
            actor=r.actor,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            decision=r.decision,
            detail=r.detail or {},
            created_at=r.created_at,
        )
        for r in rows
    ]
