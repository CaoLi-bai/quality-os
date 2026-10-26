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
        return "environment", "Infrastructure or application availability evidence matched.", False
    if any(marker in lowered for marker in LOCATOR_MARKERS):
        return "locator_drift", "Browser locator evidence matched; intent must remain unchanged.", True
    if "assert" in lowered or "http" in lowered:
        return "product_or_requirement", "Behavior differs from the approved oracle; human review is required.", False
    return "unknown", "Evidence is insufficient for a safe classification.", False


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
        "stop_rule": "Unknown, product, requirement, assertion and high-risk failures cannot enter automatic healing.",
    }
    dump_json(run_dir / "triage.json", report)
    return report
