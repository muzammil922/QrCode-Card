"""FHIR-aligned mapping helpers (MedicationRequest) for synthetic sync."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_medication_request(
    *,
    patient_id: str,
    patient_uhid: str,
    source_org_id: str,
    source_org_name: str,
    source_record_id: str,
    version: int,
    medication_text: str,
    dose_text: str,
    status: str = "active",
    authored_on: str | None = None,
) -> dict[str, Any]:
    """Pass through source medication/dose text — no clinical inference."""
    authored = authored_on or datetime.now(timezone.utc).isoformat()
    return {
        "resourceType": "MedicationRequest",
        "status": status if status in ("active", "completed", "cancelled") else "active",
        "intent": "order",
        "medicationCodeableConcept": {"text": medication_text},
        "subject": {
            "reference": f"Patient/{patient_id}",
            "identifier": {"system": "uhid", "value": patient_uhid},
        },
        "authoredOn": authored,
        "dosageInstruction": [{"text": dose_text}],
        "meta": {
            "versionId": str(version),
            "source": source_org_name,
            "extension": [
                {
                    "url": (
                        "https://universal-health-qr.local/fhir/"
                        "StructureDefinition/source-org-id"
                    ),
                    "valueString": source_org_id,
                },
                {
                    "url": (
                        "https://universal-health-qr.local/fhir/"
                        "StructureDefinition/source-record-id"
                    ),
                    "valueString": source_record_id,
                },
            ],
        },
    }


def idempotency_key(source_org_id: str, source_record_id: str, version: int) -> str:
    return f"{source_org_id}:{source_record_id}:{version}"
