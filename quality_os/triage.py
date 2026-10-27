from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import dump_json

LOCATOR_MARKERS = ["locator", "selector", "timeout waiting for", "not visible", "strict mode violation"]
ENVIRONMENT_MARKERS = ["connection refused", "remote end closed", "temporary failure", "did not become healthy"]


def classify_failure(text: str) -> tuple[str, str, bool]:
    lowered = text.lower()
    if any(marker in lowered for marker in ENVIRONMENT_MARKERS):
        return "environment", "证据指向基础设施或应用可用性问题，应先恢复环境，不得自动修改测试。", False
    if any(marker in lowered for marker in LOCATOR_MARKERS):
        return "locator_drift", "证据指向浏览器定位器漂移；只允许修改定位器，测试意图必须不变。", True
    if "assert" in lowered or "http" in lowered:
        return "product_or_requirement", "实际行为与已批准 Oracle 不一致，需要人工判断是产品缺陷还是需求问题。", False
    return "unknown", "现有证据不足，无法安全归因；必须人工查看首次失败。", False


def triage_run(run_dir: Path) -> dict:
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    failures = []
    root = ET.parse(run_dir / "junit.xml").getroot()
    for case in root.iter("testcase"):
        detail = case.find("failure")
        if detail is None:
            detail = case.find("error")
        if detail is None:
            continue
        text = (detail.text or "") + " " + detail.attrib.get("message", "")
        category, rationale, healing_allowed = classify_failure(text)
        failures.append({
            "test": f"{case.attrib.get('classname', '')}::{case.attrib['name']}",
            "category": category,
            "rationale": rationale,
            "auto_healing_allowed": healing_allowed,
            "first_failure": text[-4000:],
        })
    report = {
        "run_id": metadata["run_id"],
        "status": "no_failures" if not failures else "requires_review",
        "failures": failures,
        "stop_rule": "未知原因、产品缺陷、需求问题、断言变化和高风险失败都不得进入自动修复。",
    }
    dump_json(run_dir / "triage.json", report)
    return report
