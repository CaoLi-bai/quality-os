from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .db import DemoDB

STATIC = Path(__file__).parent / "static"


class DemoHandler(BaseHTTPRequestHandler):
    server: "DemoServer"

    def send_json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, name: str, content_type: str) -> None:
        content = (STATIC / name).read_bytes()
        if name == "index.html":
            testid = "confirm-refund" if self.server.ui_version == "v2" else "refund-submit"
            content = content.replace(b"__REFUND_TESTID__", testid.encode())
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.send_static("index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self.send_static("app.js", "text/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self.send_static("styles.css", "text/css; charset=utf-8")
        if parsed.path == "/api/health":
            return self.send_json(200, {"status": "ok", "faults": sorted(self.server.faults), "ui_version": self.server.ui_version})
        if parsed.path == "/api/orders":
            user_id = parse_qs(parsed.query).get("user_id", [""])[0]
            return self.send_json(200, {"orders": self.server.db.list_orders(user_id)})
        if parsed.path.startswith("/api/orders/"):
            order_id = parsed.path.rsplit("/", 1)[-1]
            user_id = parse_qs(parsed.query).get("user_id", [""])[0]
            status, value = self.server.db.get_order(order_id, user_id, self.server.faults)
            return self.send_json(status, value)
        self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/reset":
            self.server.db.reset()
            return self.send_json(200, {"reset": True})
        if parsed.path.startswith("/api/orders/") and parsed.path.endswith("/refund"):
            order_id = parsed.path.split("/")[-2]
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self.send_json(422, {"error": "invalid_json"})
            status, value = self.server.db.refund(order_id, payload, self.server.faults)
            return self.send_json(status, value)
        self.send_json(404, {"error": "not_found"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"demo-app {self.address_string()} {fmt % args}", flush=True)


class DemoServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], db_path: str, faults: set[str], ui_version: str):
        super().__init__(address, DemoHandler)
        self.db = DemoDB(db_path)
        self.db.reset()
        self.faults = faults
        self.ui_version = ui_version


def create_server(host: str = "127.0.0.1", port: int = 0, db_path: str = "artifacts/demo.db", faults: set[str] | None = None, ui_version: str = "v1") -> DemoServer:
    return DemoServer((host, port), db_path, faults or set(), ui_version)


def main() -> None:
    parser = argparse.ArgumentParser(description="QualityOS refund demo application")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="artifacts/demo.db")
    parser.add_argument("--faults", default=os.getenv("QUALITY_OS_FAULTS", ""))
    parser.add_argument("--ui-version", default=os.getenv("QUALITY_OS_UI_VERSION", "v1"), choices=["v1", "v2"])
    args = parser.parse_args()
    faults = {item for item in args.faults.split(",") if item}
    server = create_server(args.host, args.port, args.db, faults, args.ui_version)
    print(f"QualityOS demo listening on http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
