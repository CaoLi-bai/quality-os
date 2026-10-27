from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import dump_json


@dataclass
class RunResult:
    run_id: str
    status: str
    exit_code: int
    tests: int
    failures: int
    errors: int
    skipped: int
    duration_seconds: float
    base_url: str
    faults: list[str]
    ui_version: str
    evidence_dir: str

    def to_dict(self):
        return asdict(self)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_health(base_url: str, process: subprocess.Popen, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"演示应用提前退出，退出码：{process.returncode}。请查看 application.log。")
        try:
            with urllib.request.urlopen(base_url + "/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("演示应用在 15 秒内未通过健康检查。请检查端口、启动日志和依赖。")


def junit_summary(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {
        "tests": sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        "failures": sum(int(suite.attrib.get("failures", 0)) for suite in suites),
        "errors": sum(int(suite.attrib.get("errors", 0)) for suite in suites),
        "skipped": sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
    }


def run_pytest(root: Path, test_path: Path, evidence_dir: Path, run_id: str, faults: set[str] | None = None, ui_version: str = "v1") -> RunResult:
    faults = faults or set()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    db_path = evidence_dir / "demo.db"
    junit_path = evidence_dir / "junit.xml"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    env["QUALITY_OS_BASE_URL"] = base_url
    env["QUALITY_OS_DB_PATH"] = str(db_path)
    env["QUALITY_OS_FAULTS"] = ",".join(sorted(faults))
    env["QUALITY_OS_UI_VERSION"] = ui_version
    env["QUALITY_OS_EVIDENCE_DIR"] = str(evidence_dir)
    command = [
        sys.executable, "-m", "demo_app.server", "--port", str(port),
        "--db", str(db_path), "--faults", ",".join(sorted(faults)), "--ui-version", ui_version,
    ]
    started = time.monotonic()
    with (evidence_dir / "application.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_for_health(base_url, process)
            pytest_command = [sys.executable, "-m", "pytest", "-q", str(test_path), f"--junitxml={junit_path}"]
            dump_json(evidence_dir / "command.json", {"pytest": pytest_command, "server": command})
            completed = subprocess.run(
                pytest_command, cwd=root, env=env, capture_output=True, text=True, timeout=240, check=False
            )
            (evidence_dir / "pytest.stdout.log").write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
            exit_code = completed.returncode
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    if not junit_path.exists():
        raise RuntimeError(f"pytest 未生成 JUnit 报告，请查看：{evidence_dir / 'pytest.stdout.log'}")
    summary = junit_summary(junit_path)
    result = RunResult(
        run_id=run_id,
        status="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        **summary,
        duration_seconds=round(time.monotonic() - started, 3),
        base_url=base_url,
        faults=sorted(faults),
        ui_version=ui_version,
        evidence_dir=str(evidence_dir),
    )
    dump_json(evidence_dir / "run.json", result.to_dict())
    return result
