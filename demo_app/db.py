from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    paid_amount INTEGER NOT NULL,
    refunded_amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refunds (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    UNIQUE(order_id, idempotency_key)
);
"""

SEED = [
    ("order-1001", "user-1", 10000, 0, "paid"),
    ("order-1002", "user-1", 5000, 2000, "partially_refunded"),
    ("order-1003", "user-2", 8000, 0, "paid"),
    ("order-1004", "user-1", 2000, 0, "cancelled"),
]


class DemoDB:
    def __init__(self, path: str | Path):
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def reset(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute("DELETE FROM refunds")
            connection.execute("DELETE FROM orders")
            connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", SEED)

    def list_orders(self, user_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_order(self, order_id: str, user_id: str, faults: set[str]) -> tuple[int, dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return 404, {"error": "order_not_found"}
        if row["user_id"] != user_id and "idor" not in faults:
            return 403, {"error": "forbidden"}
        return 200, dict(row)

    def refund(self, order_id: str, payload: dict[str, Any], faults: set[str]) -> tuple[int, dict[str, Any]]:
        user_id = str(payload.get("user_id", ""))
        key = str(payload.get("idempotency_key", ""))
        amount = payload.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or not key:
            return 422, {"error": "invalid_refund_request"}
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order:
                return 404, {"error": "order_not_found"}
            if order["user_id"] != user_id and "idor" not in faults:
                return 403, {"error": "forbidden"}
            if "duplicate_refund" not in faults:
                previous = connection.execute(
                    "SELECT * FROM refunds WHERE order_id = ? AND idempotency_key = ?",
                    (order_id, key),
                ).fetchone()
                if previous:
                    return 200, {"refund_id": previous["id"], "amount": previous["amount"], "idempotent_replay": True}
            allowed_states = {"paid", "partially_refunded"}
            if "status_check" in faults:
                allowed_states |= {"cancelled", "fully_refunded"}
            if order["status"] not in allowed_states:
                return 409, {"error": "invalid_order_state"}
            remaining = order["paid_amount"] - order["refunded_amount"]
            if amount > remaining and "over_refund" not in faults:
                return 400, {"error": "refund_exceeds_remaining", "remaining": remaining}
            refund_id = f"refund-{uuid.uuid4().hex[:12]}"
            stored_key = f"{key}-duplicate-{refund_id}" if "duplicate_refund" in faults else key
            connection.execute(
                "INSERT INTO refunds VALUES (?, ?, ?, ?)",
                (refund_id, order_id, amount, stored_key),
            )
            refunded = order["refunded_amount"] + amount
            status = "fully_refunded" if refunded == order["paid_amount"] else "partially_refunded"
            connection.execute(
                "UPDATE orders SET refunded_amount = ?, status = ? WHERE id = ?",
                (refunded, status, order_id),
            )
        return 200, {"refund_id": refund_id, "amount": amount, "idempotent_replay": False}


def order_snapshot(db_path: str | Path) -> str:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM orders ORDER BY id").fetchall()
        refunds = connection.execute("SELECT * FROM refunds ORDER BY id").fetchall()
    return json.dumps({"orders": [dict(row) for row in rows], "refunds": [dict(row) for row in refunds]}, indent=2)
