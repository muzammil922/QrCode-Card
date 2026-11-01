from fastapi.testclient import TestClient


def test_admin_stats_and_org_patch(client: TestClient, auth_header: dict):
    stats = client.get("/api/v1/admin/stats", headers=auth_header)
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert "patients" in body
    assert "organizations" in body
    assert body["organizations"] >= 2

    orgs = client.get("/api/v1/admin/organizations", headers=auth_header)
    assert orgs.status_code == 200
    assert len(orgs.json()) >= 2
    org_id = orgs.json()[0]["id"]

    patched = client.patch(
        f"/api/v1/admin/organizations/{org_id}",
        headers=auth_header,
        json={"approval_status": "approved", "is_active": True, "note": "m5 stub"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["approval_status"] == "approved"

    fails = client.get("/api/v1/admin/sync-failures", headers=auth_header)
    assert fails.status_code == 200
