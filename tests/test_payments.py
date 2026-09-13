from datetime import date, timedelta


async def _make_booking(client, rent_amount="1000.00"):
    prop_resp = await client.post(
        "/api/v1/properties", json={"title": "Объект для платежей", "property_type": "apartment"}
    )
    property_id = prop_resp.json()["id"]
    tenant_resp = await client.post("/api/v1/tenants", json={"full_name": "Плательщик"})
    tenant_id = tenant_resp.json()["id"]

    booking_resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-01",
            "end_date": "2026-10-30",
            "rent_amount": rent_amount,
        },
    )
    return booking_resp.json()["id"]


async def test_create_payment(auth_client):
    client, _ = auth_client
    booking_id = await _make_booking(client)

    resp = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        json={"payment_type": "rent", "amount": "1000.00", "due_date": "2026-10-05", "payment_method": "card"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["payment_method"] == "card"


async def test_create_payment_negative_amount_rejected(auth_client):
    client, _ = auth_client
    booking_id = await _make_booking(client)

    resp = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        json={"amount": "-50.00", "due_date": "2026-10-05"},
    )
    assert resp.status_code == 422


async def test_update_payment_to_paid_sets_paid_at(auth_client):
    client, _ = auth_client
    booking_id = await _make_booking(client)
    create_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        json={"amount": "1000.00", "due_date": "2026-10-05"},
    )
    payment_id = create_resp.json()["id"]
    assert create_resp.json()["paid_at"] is None

    resp = await client.patch(f"/api/v1/payments/{payment_id}", json={"status": "paid"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"
    assert resp.json()["paid_at"] is not None


async def test_cancel_payment(auth_client):
    client, _ = auth_client
    booking_id = await _make_booking(client)
    create_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        json={"amount": "1000.00", "due_date": "2026-10-05"},
    )
    payment_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/payments/{payment_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_list_overdue_payments_includes_past_due_only(auth_client):
    client, _ = auth_client
    booking_id = await _make_booking(client)

    past_due = (date.today() - timedelta(days=3)).isoformat()
    future_due = (date.today() + timedelta(days=10)).isoformat()

    await client.post(
        f"/api/v1/bookings/{booking_id}/payments", json={"amount": "1000.00", "due_date": past_due}
    )
    await client.post(
        f"/api/v1/bookings/{booking_id}/payments", json={"amount": "1000.00", "due_date": future_due}
    )

    resp = await client.get("/api/v1/payments/overdue")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["due_date"] == past_due
    assert "property_title" in body[0]
    assert "tenant_full_name" in body[0]


async def test_payment_not_visible_to_other_owner(register_user, client):
    owner = await register_user(email="payment-owner-a@example.com")
    other = await register_user(email="payment-owner-b@example.com")

    prop_resp = await client.post(
        "/api/v1/properties",
        json={"title": "Объект владельца A", "property_type": "apartment"},
        headers=owner["headers"],
    )
    property_id = prop_resp.json()["id"]
    tenant_resp = await client.post(
        "/api/v1/tenants", json={"full_name": "Жилец A"}, headers=owner["headers"]
    )
    tenant_id = tenant_resp.json()["id"]
    booking_resp = await client.post(
        "/api/v1/bookings",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": "2026-10-01",
            "rent_amount": "1000.00",
        },
        headers=owner["headers"],
    )
    booking_id = booking_resp.json()["id"]
    payment_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        json={"amount": "1000.00", "due_date": "2026-10-05"},
        headers=owner["headers"],
    )
    payment_id = payment_resp.json()["id"]

    resp = await client.get(f"/api/v1/payments/{payment_id}", headers=other["headers"])
    assert resp.status_code == 404
