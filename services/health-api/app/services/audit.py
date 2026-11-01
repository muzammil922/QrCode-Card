from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def write_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    decision: str,
    detail: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        detail=detail or {},
    )
    db.add(event)
    return event
