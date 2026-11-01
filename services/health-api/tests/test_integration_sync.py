from fastapi.testclient import TestClient

from app.models.audit_event import AuditEvent
from app.models.fhir_resource import FhirResource
from app.models.integration_event import IntegrationEvent
from app.models.organization import Organization


def _org(db, name: str) -> Organization:
    return db.query(Organization).filter(Organization.name == name).one()


def _register(client: TestClient, headers: dict, name: str = "Synthetic Sync Patient"):
    r = client.post(
        "/api/v1/patients",
        headers=headers,
        json={"display_name": name, "date_of_birth": "1988-04-02"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_with_org(client: TestClient, org_name: str) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/session",
        json={
            "username": "demo@health.local",
            "password": "demo-password-change-me",
            "org_name": org_name,
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_draft_rejected(client: TestClient, auth_header: dict, db_session):
    patient = _register(client, auth_header)
    org_a = _org(db_session, "Demo Hospital A")
    r = client.post(
        "/api/v1/integration-events",
        headers=auth_header,
        json={
            "patient_id": patient["id"],
            "source_org_id": str(org_a.id),
            "source_record_id": "rx-draft-1",
            "version": 1,
            "medication_text": "Amoxicillin 500mg",
            "dose_text": "1 capsule twice daily",
            "status": "draft",
            "local_saved": True,
        },
    )
    assert r.status_code == 422, r.text
    asserts = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.action == "integration_event.accept",
            AuditEvent.decision == "deny",
        )
        .all()
    )
    assert any(a.detail.get("reason") == "draft_or_non_final" for a in asserts)
    assert db_session.query(IntegrationEvent).count() == 0
    assert db_session.query(FhirResource).count() == 0


def test_idempotent_integration_event(
    client: TestClient, auth_header: dict, db_session
):
    patient = _register(client, auth_header, "Synthetic Idempotent")
    org_a = _org(db_session, "Demo Hospital A")
    payload = {
        "patient_id": patient["id"],
        "source_org_id": str(org_a.id),
        "source_record_id": "rx-100",
        "version": 1,
        "medication_text": "Ibuprofen 200mg",
        "dose_text": "1 tablet every 8 hours as needed",
        "status": "final",
        "local_saved": True,
    }
    first = client.post(
        "/api/v1/integration-events", headers=auth_header, json=payload
    )
    assert first.status_code == 200, first.text
    body1 = first.json()
    assert body1["status"] == "confirmed"
    assert body1["duplicate"] is False
    assert body1["fhir_resource_id"]

    second = client.post(
        "/api/v1/integration-events", headers=auth_header, json=payload
    )
    assert second.status_code == 200, second.text
    body2 = second.json()
    assert body2["id"] == body1["id"]
    assert body2["duplicate"] is True
    assert body2["status"] == "confirmed"

    assert db_session.query(IntegrationEvent).count() == 1
    assert db_session.query(FhirResource).count() == 1

    sync = client.get(
        f"/api/v1/sync-events/{body1['id']}", headers=auth_header
    )
    assert sync.status_code == 200
    assert sync.json()["status"] == "confirmed"


def test_records_visible_after_confirm_hospital_b(
    client: TestClient, auth_header: dict, db_session
):
    patient = _register(client, auth_header, "Synthetic Cross Hospital")
    org_a = _org(db_session, "Demo Hospital A")
    org_b = _org(db_session, "Demo Hospital B")

    headers_a = _auth_with_org(client, "Demo Hospital A")
    create = client.post(
        "/api/v1/integration-events",
        headers=headers_a,
        json={
            "uhid": patient["uhid"],
            "source_org_name": "Demo Hospital A",
            "source_record_id": "rx-hosp-a-1",
            "version": 1,
            "medication_text": "Metformin 500mg",
            "dose_text": "1 tablet with breakfast",
            "status": "approved",
            "local_saved": True,
        },
    )
    assert create.status_code == 200, create.text
    assert create.json()["status"] == "confirmed"

    headers_b = _auth_with_org(client, "Demo Hospital B")
    records = client.get(
        f"/api/v1/patients/{patient['id']}/records",
        headers=headers_b,
        params={"org_id": str(org_b.id)},
    )
    assert records.status_code == 200, records.text
    page = records.json()
    assert page["total"] >= 1
    item = page["items"][0]
    assert item["resource_type"] == "MedicationRequest"
    assert item["source_org_name"] == "Demo Hospital A"
    assert item["body"]["medicationCodeableConcept"]["text"] == "Metformin 500mg"
    assert org_a.id  # seeded


def test_unauthorized_records_deny_audited(
    client: TestClient, auth_header: dict, db_session
):
    # Register without granting Hospital B consent
    reg = client.post(
        "/api/v1/patients",
        headers=auth_header,
        json={
            "display_name": "Synthetic No Consent B",
            "grant_org_names": ["Demo Hospital A"],
        },
    )
    assert reg.status_code == 201, reg.text
    patient_id = reg.json()["id"]
    org_a = _org(db_session, "Demo Hospital A")

    headers_a = _auth_with_org(client, "Demo Hospital A")
    sync = client.post(
        "/api/v1/integration-events",
        headers=headers_a,
        json={
            "patient_id": patient_id,
            "source_org_id": str(org_a.id),
            "source_record_id": "rx-private-1",
            "version": 1,
            "medication_text": "Synthetic Drug",
            "dose_text": "as directed",
            "status": "final",
            "local_saved": True,
        },
    )
    assert sync.status_code == 200, sync.text

    headers_b = _auth_with_org(client, "Demo Hospital B")
    denied = client.get(
        f"/api/v1/patients/{patient_id}/records",
        headers=headers_b,
    )
    assert denied.status_code == 403, denied.text
    denies = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.action == "patient.records",
            AuditEvent.decision == "deny",
        )
        .all()
    )
    assert len(denies) >= 1


def test_unauthenticated_integration_denied(client: TestClient, db_session):
    org_a = _org(db_session, "Demo Hospital A")
    r = client.post(
        "/api/v1/integration-events",
        json={
            "uhid": "UHQ-NOPE",
            "source_org_id": str(org_a.id),
            "source_record_id": "x",
            "version": 1,
            "medication_text": "x",
            "dose_text": "y",
            "status": "final",
        },
    )
    assert r.status_code == 401


def test_hospital_b_cannot_submit_as_source(
    client: TestClient, auth_header: dict, db_session
):
    patient = _register(client, auth_header, "Synthetic Wrong Source")
    headers_b = _auth_with_org(client, "Demo Hospital B")
    r = client.post(
        "/api/v1/integration-events",
        headers=headers_b,
        json={
            "patient_id": patient["id"],
            "source_org_name": "Demo Hospital B",
            "source_record_id": "rx-b-1",
            "version": 1,
            "medication_text": "Should Fail",
            "dose_text": "n/a",
            "status": "final",
            "local_saved": True,
        },
    )
    assert r.status_code == 403
