from sqlalchemy import text


async def _make_admin(user_id):
    from booking.core.database import engine

    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET role = 'admin' WHERE id = :user_id"),
            {"user_id": user_id},
        )


async def test_verified_user_has_user_role(register_user):
    registration = await register_user()
    assert registration["user"]["role"] == "user"


async def test_email_from_allowlist_becomes_admin(register_user, monkeypatch):
    from booking.services import auth_service

    monkeypatch.setattr(auth_service.settings, "admin_emails", ["automated-admin@example.com"])
    registration = await register_user(email="automated-admin@example.com")
    assert registration["user"]["role"] == "admin"


async def test_regular_user_cannot_access_admin_routes(auth_client):
    client, _ = auth_client
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 403


async def test_admin_can_list_users_change_role_and_view_overview(client, register_user):
    admin = await register_user(email="admin@example.com")
    user = await register_user(email="user@example.com")
    await _make_admin(admin["user"]["id"])
    client.headers.update(admin["headers"])

    users_response = await client.get("/api/v1/admin/users")
    assert users_response.status_code == 200
    assert {item["email"] for item in users_response.json()} == {"admin@example.com", "user@example.com"}

    role_response = await client.patch(
        f"/api/v1/admin/users/{user['user']['id']}/role", json={"role": "admin"}
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "admin"

    overview_response = await client.get("/api/v1/admin/overview")
    assert overview_response.status_code == 200
    assert overview_response.json()["users_count"] == 2
