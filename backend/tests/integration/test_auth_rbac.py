import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["simulation_mode"] is True


@pytest.mark.asyncio
async def test_login_and_rbac_enforcement(client: AsyncClient) -> None:
    viewer_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@opsmind.local", "password": "Viewer123!"},
    )
    assert viewer_login.status_code == 200
    viewer_token = viewer_login.json()["access_token"]

    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert me_resp.status_code == 200
    assert "Viewer" in me_resp.json()["role_names"]

    forbidden_resp = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert forbidden_resp.status_code == 403

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@opsmind.local", "password": "Admin123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    users_resp = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 3