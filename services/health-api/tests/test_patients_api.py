from fastapi.testclient import TestClient

from app.models.audit_event import AuditEvent


def test_register_resolve_revoke_flow(client: TestClient, auth_header: dict, db_session):
    # Register synthetic patient
    reg = client.post(
        "/api/v1/patients",
        headers=auth_header,
        json={"display_name": "Synthetic Patient Zero", "date_of_birth": "1990-01-15"},
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["is_synthetic"] is True
    assert body["uhid"].startswith("UHQ-")
    assert "card" in body
    qr_token = body["card"]["qr_token"]
    assert qr_token
    # Card / QR payload must not embed medical or ID document fields
    assert "CNIC" not in qr_token
    assert "diagnosis" not in str(body["card"]).lower()
    patient_id = body["id"]

    # Resolve QR
    resolved = client.get(
        "/api/v1/patients/resolve-qr",
        headers=auth_header,
        params={"token": qr_token},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["uhid"] == body["uhid"]
    assert resolved.json()["display_name"] == "Synthetic Patient Zero"

    # Revoke without replacement first path: replace=true (default)
    revoked = client.post(
        f"/api/v1/patients/{patient_id}/qr/revoke",
        headers=auth_header,
        params={"replace": True},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["replacement_qr_token"]
    old_denied = client.get(
        "/api/v1/patients/resolve-qr",
        headers=auth_header,
        params={"token": qr_token},
    )
    assert old_denied.status_code == 404

    new_ok = client.get(
        "/api/v1/patients/resolve-qr",
        headers=auth_header,
        params={"token": revoked.json()["replacement_qr_token"]},
    )
    assert new_ok.status_code == 200

    # Audit has deny for revoked resolve
    denies = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "qr.resolve", AuditEvent.decision == "deny")
        .all()
    )
    assert len(denies) >= 1


def test_invalid_qr_audited(client: TestClient, auth_header: dict, db_session):
    bad = client.get(
        "/api/v1/patients/resolve-qr",
        headers=auth_header,
        params={"token": "this-is-not-a-valid-token-value"},
    )
    assert bad.status_code == 404
    denies = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.decision == "deny")
        .all()
    )
    assert any(d.action == "qr.resolve" for d in denies)


def test_unauthenticated_register_denied(client: TestClient):
    r = client.post(
        "/api/v1/patients",
        json={"display_name": "No Auth Synthetic"},
    )
    assert r.status_code == 401


def test_unique_uhids(client: TestClient, auth_header: dict):
    ids = set()
    for i in range(5):
        r = client.post(
            "/api/v1/patients",
            headers=auth_header,
            json={"display_name": f"Synthetic Twin {i}"},
        )
        assert r.status_code == 201
        ids.add(r.json()["uhid"])
    assert len(ids) == 5
