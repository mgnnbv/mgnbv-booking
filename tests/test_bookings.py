async def _make_property(client, title="Тестовый объект"):
    resp = await client.post(
        "/api/v1/properties", json={"title": title, "property_type": "apartment"}
    )
    return resp.json()["id"]


async def _make_tenant(client, full_name="Тестовый жилец"):
    resp = await client.post("/api/v1/tenants", json={"full_name": full_name})
    return resp.json()["id"]


async def test_create_booking(auth_client):
    client, _ = auth_client
    property_id = await _make_property(client)
    tenant_id = await _make_tenant(client)

    resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-01",
            "end_date": "2026-10-10",
            "rent_amount": "5000.00",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert "rental_type" not in body


async def test_create_booking_end_before_start_rejected(auth_client):
    client, _ = auth_client
    property_id = await _make_property(client)
    tenant_id = await _make_tenant(client)

    resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-10",
            "end_date": "2026-10-01",
            "rent_amount": "5000.00",
        },
    )
    assert resp.status_code == 422


async def test_overlapping_bookings_for_same_property_conflict(auth_client):
    client, _ = auth_client
    property_id = await _make_property(client)
    tenant_a = await _make_tenant(client, "Жилец А")
    tenant_b = await _make_tenant(client, "Жилец Б")

    first = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_a,
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "rent_amount": "1000.00",
        },
    )
    assert first.status_code == 201

    overlapping = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_b,
            "start_date": "2026-11-05",
            "end_date": "2026-11-15",
            "rent_amount": "1000.00",
        },
    )
    assert overlapping.status_code == 409


async def test_update_booking_to_invalid_dates_rejected(auth_client):
    client, _ = auth_client
    property_id = await _make_property(client)
    tenant_id = await _make_tenant(client)
    create_resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-01",
            "end_date": "2026-10-10",
            "rent_amount": "1000.00",
        },
    )
    booking_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/bookings/{booking_id}", json={"end_date": "2026-09-01"}
    )
    assert resp.status_code == 422


async def test_cancel_booking_frees_the_dates(auth_client):
    client, _ = auth_client
    property_id = await _make_property(client)
    tenant_a = await _make_tenant(client, "Жилец А")
    tenant_b = await _make_tenant(client, "Жилец Б")

    first = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_a,
            "start_date": "2026-12-01",
            "end_date": "2026-12-10",
            "rent_amount": "1000.00",
        },
    )
    booking_id = first.json()["id"]

    cancel_resp = await client.delete(f"/api/v1/bookings/{booking_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    second = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_b,
            "start_date": "2026-12-01",
            "end_date": "2026-12-10",
            "rent_amount": "1000.00",
        },
    )
    assert second.status_code == 201


async def test_booking_rejects_property_owned_by_someone_else(register_user, client):
    owner = await register_user(email="booking-owner-a@example.com")
    other = await register_user(email="booking-owner-b@example.com")

    property_resp = await client.post(
        "/api/v1/properties",
        json={"title": "Чужой объект", "property_type": "apartment"},
        headers=owner["headers"],
    )
    property_id = property_resp.json()["id"]

    tenant_resp = await client.post(
        "/api/v1/tenants", json={"full_name": "Чужой жилец"}, headers=other["headers"]
    )
    tenant_id = tenant_resp.json()["id"]

    resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-01",
            "rent_amount": "1000.00",
        },
        headers=other["headers"],
    )
    assert resp.status_code == 404
