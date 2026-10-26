from __future__ import annotations

import os
import threading

import pytest

from demo_app.server import create_server


@pytest.fixture(scope="session", autouse=True)
def demo_server(tmp_path_factory):
    if os.environ.get("QUALITY_OS_BASE_URL"):
        yield
        return
    db_path = tmp_path_factory.mktemp("demo") / "test.db"
    server = create_server(db_path=str(db_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    os.environ["QUALITY_OS_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
    os.environ["QUALITY_OS_DB_PATH"] = str(db_path)
    os.environ["QUALITY_OS_FAULTS"] = ""
    os.environ["QUALITY_OS_UI_VERSION"] = "v1"
    yield
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
