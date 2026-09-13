async def test_create_tenant(auth_client):
    client, _ = auth_client
    resp = await client.post(
        "/api/v1/tenants", json={"full_name": "Иван Иванов", "phone": "+79990001122"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["full_name"] == "Иван Иванов"
    assert body["has_passport_data"] is False


async def test_create_tenant_with_passport_data_is_encrypted_and_retrievable(auth_client):
    client, _ = auth_client
    resp = await client.post(
        "/api/v1/tenants",
        json={"full_name": "Пётр Петров", "passport_data": "1234 567890"},
    )
    tenant_id = resp.json()["id"]
    assert resp.json()["has_passport_data"] is True

    raw = await client.get(f"/api/v1/tenants/{tenant_id}/passport-data")
    assert raw.status_code == 200
    assert raw.json()["passport_data"] == "1234 567890"


async def test_list_tenants_search_filters_by_name(auth_client):
    client, _ = auth_client
    await client.post("/api/v1/tenants", json={"full_name": "Анна Смирнова"})
    await client.post("/api/v1/tenants", json={"full_name": "Борис Кузнецов"})

    resp = await client.get("/api/v1/tenants?search=Анна")
    names = [t["full_name"] for t in resp.json()]
    assert names == ["Анна Смирнова"]


async def test_get_tenant_not_found(auth_client):
    client, _ = auth_client
    resp = await client.get("/api/v1/tenants/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_update_tenant_replaces_passport_data(auth_client):
    client, _ = auth_client
    create_resp = await client.post(
        "/api/v1/tenants", json={"full_name": "Обновляемый", "passport_data": "old"}
    )
    tenant_id = create_resp.json()["id"]

    await client.patch(f"/api/v1/tenants/{tenant_id}", json={"passport_data": "new"})
    raw = await client.get(f"/api/v1/tenants/{tenant_id}/passport-data")
    assert raw.json()["passport_data"] == "new"


async def test_tenant_isolated_between_owners(register_user, client):
    owner = await register_user(email="tenant-owner-a@example.com")
    other = await register_user(email="tenant-owner-b@example.com")

    create_resp = await client.post(
        "/api/v1/tenants", json={"full_name": "Чужой жилец"}, headers=owner["headers"]
    )
    tenant_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/tenants/{tenant_id}", headers=other["headers"])
    assert resp.status_code == 404
