"""Integration event processing — post-save prescription sync (synthetic)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.fhir_resource import FhirResource
from app.models.integration_event import IntegrationEvent
from app.models.organization import Organization
from app.models.patient import Patient
from app.services.fhir_mapping import build_medication_request, idempotency_key

FINAL_STATUSES = frozenset({"final", "approved"})
DRAFT_STATUSES = frozenset({"draft", "preliminary", "entered-in-error"})
SOURCE_HOSPITAL_A = "Demo Hospital A"


def make_idempotency_key(
    source_org_id: uuid.UUID, source_record_id: str, version: int
) -> str:
    return idempotency_key(str(source_org_id), source_record_id, version)


def resolve_source_org(
    db: Session,
    *,
    source_org_id: uuid.UUID | None,
    source_org_name: str | None,
) -> Organization | None:
    if source_org_id is not None:
        return db.query(Organization).filter(Organization.id == source_org_id).first()
    if source_org_name:
        return (
            db.query(Organization)
            .filter(Organization.name == source_org_name.strip())
            .first()
        )
    return None


def resolve_patient(
    db: Session,
    *,
    patient_id: uuid.UUID | None,
    uhid: str | None,
) -> Patient | None:
    if patient_id is not None:
        return db.query(Patient).filter(Patient.id == patient_id).first()
    if uhid:
        return db.query(Patient).filter(Patient.uhid == uhid.strip()).first()
    return None


def process_integration_event(db: Session, event: IntegrationEvent) -> IntegrationEvent:
    """Advance queued/failed event: sent → store FHIR MedicationRequest → confirmed."""
    now = datetime.now(timezone.utc)
    event.status = "sent"
    event.updated_at = now
    event.error_message = None
    db.flush()

    try:
        payload = event.payload or {}
        patient = db.query(Patient).filter(Patient.id == event.patient_id).first()
        org = (
            db.query(Organization)
            .filter(Organization.id == event.source_org_id)
            .first()
        )
        if patient is None or org is None:
            raise ValueError("patient_or_org_missing")

        existing_fhir = (
            db.query(FhirResource)
            .filter(
                FhirResource.patient_id == patient.id,
                FhirResource.source_org_id == org.id,
                FhirResource.source_record_id == event.source_record_id,
                FhirResource.version == (event.version or 1),
                FhirResource.resource_type == "MedicationRequest",
            )
            .first()
        )
        if existing_fhir is not None:
            event.fhir_resource_id = existing_fhir.id
            event.status = "confirmed"
            event.processed_at = now
            event.updated_at = now
            return event

        body = build_medication_request(
            patient_id=str(patient.id),
            patient_uhid=patient.uhid,
            source_org_id=str(org.id),
            source_org_name=org.name,
            source_record_id=event.source_record_id or "",
            version=event.version or 1,
            medication_text=str(payload.get("medication_text", "")),
            dose_text=str(payload.get("dose_text", "")),
            status="active",
            authored_on=payload.get("authored_on"),
        )
        fhir = FhirResource(
            patient_id=patient.id,
            resource_type="MedicationRequest",
            version=event.version or 1,
            source_org_id=org.id,
            source_record_id=event.source_record_id,
            status="final",
            body=body,
        )
        db.add(fhir)
        db.flush()
        event.fhir_resource_id = fhir.id
        event.status = "confirmed"
        event.processed_at = now
        event.updated_at = now
        return event
    except Exception as exc:  # noqa: BLE001 — surface failure on sync status
        event.status = "failed"
        event.error_message = str(exc)[:2000]
        event.processed_at = now
        event.updated_at = now
        event.retry_count = (event.retry_count or 0) + 1
        return event
