"""API-level §14 acceptance path (synthetic)."""

from fastapi.testclient import TestClient


def test_section14_api_path(client: TestClient):
    # Staff A
    sa = client.post(
        "/api/v1/auth/session",
        json={
            "username": "demo@health.local",
            "password": "demo-password-change-me",
            "org_name": "Demo Hospital A",
        },
    )
    assert sa.status_code == 200
    ha = {"Authorization": f"Bearer {sa.json()['access_token']}"}

    reg = client.post(
        "/api/v1/patients",
        headers=ha,
        json={"display_name": "§14 Synthetic Pytest", "date_of_birth": "1990-01-01"},
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["uhid"].startswith("UHQ-")
    qr = body["card"]["qr_token"]
    assert "CNIC" not in qr

    assert client.post("/api/v1/patients", json={"display_name": "x"}).status_code == 401

    rx = {
        "patient_id": body["id"],
        "source_org_name": "Demo Hospital A",
        "source_record_id": "rx-s14-pytest-1",
        "version": 1,
        "medication_text": "Doxycycline 100mg",
        "dose_text": "BID",
        "status": "final",
        "local_saved": True,
    }
    evt = client.post("/api/v1/integration-events", headers=ha, json=rx)
    assert evt.status_code == 200
    assert evt.json()["status"] == "confirmed"

    draft = {**rx, "status": "draft", "source_record_id": "rx-s14-pytest-draft"}
    assert client.post("/api/v1/integration-events", headers=ha, json=draft).status_code == 422

    dup = client.post("/api/v1/integration-events", headers=ha, json=rx)
    assert dup.status_code == 200
    assert dup.json()["id"] == evt.json()["id"]
    assert dup.json()["duplicate"] is True

    sb = client.post(
        "/api/v1/auth/session",
        json={
            "username": "demo@health.local",
            "password": "demo-password-change-me",
            "org_name": "Demo Hospital B",
        },
    )
    hb = {"Authorization": f"Bearer {sb.json()['access_token']}"}
    resolved = client.get(
        "/api/v1/patients/resolve-qr",
        headers=hb,
        params={"token": qr},
    )
    assert resolved.status_code == 200
    assert resolved.json()["uhid"] == body["uhid"]

    records = client.get(f"/api/v1/patients/{body['id']}/records", headers=hb)
    assert records.status_code == 200
    meds = [
        i["body"].get("medicationCodeableConcept", {}).get("text")
        for i in records.json()["items"]
    ]
    assert "Doxycycline 100mg" in meds

    client.post(f"/api/v1/patients/{body['id']}/qr/revoke", headers=ha, params={"replace": True})
    assert (
        client.get("/api/v1/patients/resolve-qr", headers=hb, params={"token": qr}).status_code
        == 404
    )

    audit = client.get("/api/v1/audit-events?limit=50", headers=ha)
    assert any(a["decision"] == "deny" for a in audit.json())

    stats = client.get("/api/v1/admin/stats", headers=ha)
    assert stats.status_code == 200
    assert stats.json()["organizations"] >= 2
