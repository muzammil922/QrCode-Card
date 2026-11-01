from fastapi.testclient import TestClient


def test_patient_register_login_me_records(client: TestClient, auth_header: dict):
    # Staff creates a synced rx for a hospital-registered patient first path:
    # Patient self-registers separately
    email = "synthetic.patient@example.com"
    reg = client.post(
        "/api/v1/auth/patient/register",
        json={
            "email": email,
            "password": "synthet1c-pass",
            "display_name": "Synthetic Portal Patient",
            "otp": "123456",
            "date_of_birth": "1992-05-01",
        },
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["uhid"].startswith("UHQ-")
    assert body["qr_token"]
    assert body["role"] == "patient"
    patient_token = body["access_token"]
    headers = {"Authorization": f"Bearer {patient_token}"}

    me = client.get("/api/v1/patients/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Synthetic Portal Patient"

    card = client.get("/api/v1/patients/me/card", headers=headers)
    assert card.status_code == 200
    assert card.json()["qr_token"]
    assert "CNIC" not in card.json()["qr_token"]

    # Staff syncs a prescription for this patient
    patient_id = body["patient_id"]
    staff = client.post(
        "/api/v1/auth/session",
        json={
            "username": "demo@health.local",
            "password": "demo-password-change-me",
            "org_name": "Demo Hospital A",
        },
    )
    assert staff.status_code == 200
    sh = {"Authorization": f"Bearer {staff.json()['access_token']}"}
    evt = client.post(
        "/api/v1/integration-events",
        headers=sh,
        json={
            "patient_id": patient_id,
            "source_org_name": "Demo Hospital A",
            "source_record_id": "rx-portal-1",
            "version": 1,
            "medication_text": "Ibuprofen 200mg",
            "dose_text": "1 tablet as needed",
            "status": "final",
            "local_saved": True,
        },
    )
    assert evt.status_code == 200, evt.text
    assert evt.json()["status"] == "confirmed"

    records = client.get("/api/v1/patients/me/records", headers=headers)
    assert records.status_code == 200, records.text
    assert records.json()["total"] >= 1
    meds = [
        i["body"].get("medicationCodeableConcept", {}).get("text")
        for i in records.json()["items"]
    ]
    assert "Ibuprofen 200mg" in meds

    login = client.post(
        "/api/v1/auth/patient/login",
        json={"email": email, "password": "synthet1c-pass", "otp": "123456"},
    )
    assert login.status_code == 200
    assert login.json()["uhid"] == body["uhid"]


def test_bad_otp_rejected(client: TestClient):
    r = client.post(
        "/api/v1/auth/patient/register",
        json={
            "email": "bad.otp@example.com",
            "password": "synthet1c-pass",
            "display_name": "Nope",
            "otp": "000000",
        },
    )
    assert r.status_code == 400
