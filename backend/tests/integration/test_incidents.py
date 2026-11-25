import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_incident_lifecycle_evidence_and_postmortem(client: AsyncClient) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@opsmind.local", "password": "Admin123!"},
    )
    assert login_resp.status_code == 200
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    create_resp = await client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "title": "Simulated connection pool exhaustion on primary-postgres",
            "description": "Connection errors rising in checkout flow.",
            "severity": "critical",
            "environment": "prod-sim",
        },
    )
    assert create_resp.status_code == 201
    incident = create_resp.json()
    inc_id = incident["id"]
    assert incident["status"] == "incident_created"

    ev_resp = await client.post(
        f"/api/v1/incidents/{inc_id}/evidence",
        headers=headers,
        json={
            "evidence_type": "log",
            "reference_id": "corr-db_connection_exhaustion-01",
            "stance": "supporting",
            "notes": "Timeout errors correlate with pool saturation.",
        },
    )
    assert ev_resp.status_code == 201

    ack_resp = await client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        headers=headers,
        json={"status": "incident_acknowledged", "note": "On-call engineer acknowledged"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["acknowledged_at"] is not None

    res_resp = await client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        headers=headers,
        json={"status": "incident_resolved", "note": "Simulated pool limit adjusted"},
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["resolved_at"] is not None

    pm_resp = await client.post(f"/api/v1/incidents/{inc_id}/postmortem", headers=headers)
    assert pm_resp.status_code == 200
    assert pm_resp.json()["status"] == "postmortem_generated"
    assert "# Post-Incident Report:" in pm_resp.json()["postmortem_markdown"]