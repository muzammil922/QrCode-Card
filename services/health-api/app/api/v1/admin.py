"""Platform admin endpoints — demo JWT / admin role. No unrestricted clinical dump."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.audit_event import AuditEvent
from app.models.fhir_resource import FhirResource
from app.models.integration_event import IntegrationEvent
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(principal: Principal) -> None:
    if principal.role not in ("demo", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or demo staff token required",
        )


class PlatformStats(BaseModel):
    patients: int
    organizations: int
    users: int
    clinical_records: int
    integration_events: int
    integration_failed: int
    integration_confirmed: int
    audit_events: int
    audit_denials: int
    note: str = (
        "Aggregate counts only — no bulk clinical export. Synthetic prototype."
    )


class OrgAdminRow(BaseModel):
    id: uuid.UUID
    name: str
    org_type: str
    is_active: bool
    approval_status: str
    created_at: datetime


class OrgStatusUpdate(BaseModel):
    approval_status: Literal["pending", "approved", "suspended"] = "approved"
    is_active: bool = True
    note: str | None = Field(default=None, max_length=500)


class FailedSyncRow(BaseModel):
    id: uuid.UUID
    status: str
    idempotency_key: str
    retry_count: int
    error_message: str | None
    created_at: datetime


@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform aggregate stats (no clinical dump)",
)
def platform_stats(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PlatformStats:
    _require_admin(principal)
    return PlatformStats(
        patients=db.query(func.count(Patient.id)).scalar() or 0,
        organizations=db.query(func.count(Organization.id)).scalar() or 0,
        users=db.query(func.count(User.id)).scalar() or 0,
        clinical_records=db.query(func.count(FhirResource.id)).scalar() or 0,
        integration_events=db.query(func.count(IntegrationEvent.id)).scalar() or 0,
        integration_failed=db.query(func.count(IntegrationEvent.id))
        .filter(IntegrationEvent.status == "failed")
        .scalar()
        or 0,
        integration_confirmed=db.query(func.count(IntegrationEvent.id))
        .filter(IntegrationEvent.status == "confirmed")
        .scalar()
        or 0,
        audit_events=db.query(func.count(AuditEvent.id)).scalar() or 0,
        audit_denials=db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.decision == "deny")
        .scalar()
        or 0,
    )


@router.get(
    "/organizations",
    response_model=list[OrgAdminRow],
    summary="List orgs with approval stub fields",
)
def admin_list_orgs(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[OrgAdminRow]:
    _require_admin(principal)
    rows = db.query(Organization).order_by(Organization.name.asc()).all()
    out: list[OrgAdminRow] = []
    for r in rows:
        is_active = bool(getattr(r, "is_active", True))
        approval = getattr(r, "approval_status", None) or "approved"
        out.append(
            OrgAdminRow(
                id=r.id,
                name=r.name,
                org_type=r.org_type.value if hasattr(r.org_type, "value") else str(r.org_type),
                is_active=is_active,
                approval_status=str(approval),
                created_at=r.created_at,
            )
        )
    return out


@router.patch(
    "/organizations/{org_id}",
    response_model=OrgAdminRow,
    summary="Approve / suspend organization (demo stub)",
)
def update_org_status(
    org_id: uuid.UUID,
    body: OrgStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> OrgAdminRow:
    _require_admin(principal)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    if hasattr(org, "is_active"):
        org.is_active = body.is_active
    if hasattr(org, "approval_status"):
        org.approval_status = body.approval_status

    write_audit(
        db,
        actor=principal.subject,
        action="admin.org_status",
        resource_type="organization",
        resource_id=str(org.id),
        decision="allow",
        detail={
            "approval_status": body.approval_status,
            "is_active": body.is_active,
            "note": body.note,
        },
    )
    db.commit()
    db.refresh(org)
    return OrgAdminRow(
        id=org.id,
        name=org.name,
        org_type=org.org_type.value if hasattr(org.org_type, "value") else str(org.org_type),
        is_active=bool(getattr(org, "is_active", True)),
        approval_status=str(getattr(org, "approval_status", "approved")),
        created_at=org.created_at,
    )


@router.get(
    "/sync-failures",
    response_model=list[FailedSyncRow],
    summary="Recent failed integration events",
)
def list_sync_failures(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[FailedSyncRow]:
    _require_admin(principal)
    rows = (
        db.query(IntegrationEvent)
        .filter(IntegrationEvent.status == "failed")
        .order_by(IntegrationEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        FailedSyncRow(
            id=r.id,
            status=r.status,
            idempotency_key=r.idempotency_key,
            retry_count=r.retry_count,
            error_message=getattr(r, "error_message", None),
            created_at=r.created_at,
        )
        for r in rows
    ]
