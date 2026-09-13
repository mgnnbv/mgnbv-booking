async def test_create_property(auth_client):
    client, _ = auth_client
    resp = await client.post(
        "/api/v1/properties",
        json={"title": "Квартира на Ленина", "property_type": "apartment", "default_rate": "3500.00"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Квартира на Ленина"
    assert body["is_archived"] is False
    assert body["photos"] == []


async def test_list_properties_excludes_archived_by_default(auth_client):
    client, _ = auth_client
    create_resp = await client.post(
        "/api/v1/properties", json={"title": "Будет архивной", "property_type": "room"}
    )
    prop_id = create_resp.json()["id"]
    await client.delete(f"/api/v1/properties/{prop_id}")

    active_only = await client.get("/api/v1/properties")
    assert active_only.json() == []

    with_archived = await client.get("/api/v1/properties?include_archived=true")
    assert len(with_archived.json()) == 1
    assert with_archived.json()[0]["is_archived"] is True


async def test_get_property_not_found(auth_client):
    client, _ = auth_client
    resp = await client.get("/api/v1/properties/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_update_property(auth_client):
    client, _ = auth_client
    create_resp = await client.post(
        "/api/v1/properties", json={"title": "Старое имя", "property_type": "house"}
    )
    prop_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/v1/properties/{prop_id}", json={"title": "Новое имя"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Новое имя"


async def test_archive_then_restore_property(auth_client):
    client, _ = auth_client
    create_resp = await client.post(
        "/api/v1/properties", json={"title": "Циклический объект", "property_type": "number"}
    )
    prop_id = create_resp.json()["id"]

    archived = await client.delete(f"/api/v1/properties/{prop_id}")
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True

    restored = await client.patch(f"/api/v1/properties/{prop_id}", json={"is_archived": False})
    assert restored.json()["is_archived"] is False


async def test_property_not_visible_to_other_owner(register_user, client):
    owner = await register_user(email="owner-a@example.com")
    other = await register_user(email="owner-b@example.com")

    create_resp = await client.post(
        "/api/v1/properties",
        json={"title": "Собственность A", "property_type": "apartment"},
        headers=owner["headers"],
    )
    prop_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/properties/{prop_id}", headers=other["headers"])
    assert resp.status_code == 404
