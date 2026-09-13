async def test_register_does_not_create_user_until_verified(client):
    email = "pending@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Pending Guy"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == email

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login_resp.status_code == 403


async def test_verify_email_wrong_code_rejected(client, register_user):
    email = "wrongcode@example.com"
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    resp = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": "000000"}
    )
    assert resp.status_code == 422


async def test_verify_email_success_creates_real_user(register_user):
    reg = await register_user(email="verified@example.com")
    assert reg["user"]["email"] == "verified@example.com"
    assert "id" in reg["user"]


async def test_abandoned_registration_does_not_block_email(client):
    """Регрессия: незавершённая регистрация не должна навсегда занимать email."""
    email = "abandoned@example.com"
    first = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password456"}
    )
    assert second.status_code == 201


async def test_login_wrong_password_rejected(register_user, client):
    reg = await register_user(email="loginfail@example.com", password="correct-password")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": reg["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_success_returns_token_pair(register_user, client):
    reg = await register_user(email="loginok@example.com", password="correct-password")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": reg["email"], "password": "correct-password"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_refresh_token_returns_new_access_token(register_user, client):
    reg = await register_user(email="refresh@example.com")
    refresh_token = reg["tokens"]["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_protected_endpoint_requires_auth(client):
    resp = await client.get("/api/v1/properties")
    assert resp.status_code == 401
