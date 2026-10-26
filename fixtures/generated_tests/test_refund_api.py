from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid

def base_url():
    return os.environ["QUALITY_OS_BASE_URL"].rstrip("/")


def request(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base_url() + path, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def reset():
    status, _ = request("POST", "/reset")
    assert status == 200


def refund(order_id="order-1001", user_id="user-1", amount=100, key=None):
    return request("POST", f"/api/orders/{order_id}/refund", {
        "user_id": user_id,
        "amount": amount,
        "idempotency_key": key or str(uuid.uuid4()),
    })


def test_refund_equal_to_remaining_is_accepted():
    reset()
    status, value = refund(order_id="order-1002", amount=3000)
    assert status == 200
    assert value["amount"] == 3000
    _, order = request("GET", "/api/orders/order-1002?user_id=user-1")
    assert order["refunded_amount"] == 5000
    assert order["status"] == "fully_refunded"


def test_over_refund_is_rejected_without_state_change():
    reset()
    status, value = refund(amount=10001)
    assert status == 400
    assert value["error"] == "refund_exceeds_remaining"
    _, order = request("GET", "/api/orders/order-1001?user_id=user-1")
    assert order["refunded_amount"] == 0


def test_idempotent_retry_creates_one_refund():
    reset()
    key = "retry-001"
    first_status, first = refund(amount=500, key=key)
    second_status, second = refund(amount=500, key=key)
    assert first_status == second_status == 200
    assert first["refund_id"] == second["refund_id"]
    assert second["idempotent_replay"] is True
    _, order = request("GET", "/api/orders/order-1001?user_id=user-1")
    assert order["refunded_amount"] == 500


def test_other_user_cannot_read_or_refund_order():
    reset()
    read_status, _ = request("GET", "/api/orders/order-1003?user_id=user-1")
    refund_status, _ = refund(order_id="order-1003", user_id="user-1", amount=100)
    assert read_status == 403
    assert refund_status == 403
    _, order = request("GET", "/api/orders/order-1003?user_id=user-2")
    assert order["refunded_amount"] == 0


def test_cancelled_order_cannot_be_refunded():
    reset()
    status, value = refund(order_id="order-1004", amount=100)
    assert status == 409
    assert value["error"] == "invalid_order_state"
    _, order = request("GET", "/api/orders/order-1004?user_id=user-1")
    assert order["refunded_amount"] == 0
