import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_services_and_scenario_lifecycle(client: AsyncClient) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@opsmind.local", "password": "Admin123!"},
    )
    assert login_resp.status_code == 200
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    services_resp = await client.get("/api/v1/services", headers=headers)
    assert services_resp.status_code == 200
    services = services_resp.json()
    assert len(services) >= 6

    trigger_resp = await client.post(
        "/api/v1/simulation/scenarios/db_connection_exhaustion/trigger",
        headers=headers,
    )
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["status"] == "degraded"
    assert trigger_resp.json()["active_scenario"] == "db_connection_exhaustion"

    pause_resp = await client.post(
        "/api/v1/simulation/scenarios/db_connection_exhaustion/pause",
        headers=headers,
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["scenario_paused"] is True

    reset_resp = await client.post(
        "/api/v1/simulation/scenarios/db_connection_exhaustion/reset",
        headers=headers,
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "healthy"
    assert reset_resp.json()["active_scenario"] is None