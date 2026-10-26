from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_spec(spec: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    requirements = spec.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        return [{"code": "EMPTY_SPEC", "message": "Specification must contain requirements."}]
    seen: set[str] = set()
    for item in requirements:
        req_id = item.get("id", "<missing>")
        if req_id in seen:
            issues.append({"code": "DUPLICATE_ID", "message": req_id})
        seen.add(req_id)
        for field in ("id", "source", "risk", "rule", "oracle_source"):
            if not item.get(field):
                issues.append({"code": "MISSING_FIELD", "message": f"{req_id}: {field}"})
        if item.get("oracle_source") not in policy["allowed_oracle_sources"]:
            issues.append({"code": "UNAPPROVED_ORACLE", "message": req_id})
        if not item.get("acceptance"):
            issues.append({"code": "MISSING_ACCEPTANCE", "message": req_id})
        if item["risk"] in policy["high_risks"] and item.get("unresolved"):
            issues.append({"code": "UNRESOLVED_HIGH_RISK", "message": req_id})
    if not spec.get("approved_by"):
        issues.append({"code": "MISSING_APPROVAL", "message": "Specification has no named approver."})
    return issues


def validate_cases(cases: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    req_ids = {item["id"] for item in spec.get("requirements", [])}
    seen: set[str] = set()
    covered: set[str] = set()
    for case in cases.get("cases", []):
        case_id = case.get("id", "<missing>")
        if case_id in seen:
            issues.append({"code": "DUPLICATE_CASE", "message": case_id})
        seen.add(case_id)
        if not case.get("test_nodeid") or not case.get("oracle"):
            issues.append({"code": "INCOMPLETE_CASE", "message": case_id})
        links = case.get("requirement_ids", [])
        if not links:
            issues.append({"code": "ORPHAN_CASE", "message": case_id})
        for req_id in links:
            covered.add(req_id)
            if req_id not in req_ids:
                issues.append({"code": "UNKNOWN_REQUIREMENT", "message": f"{case_id}: {req_id}"})
    for req_id in sorted(req_ids - covered):
        issues.append({"code": "UNCOVERED_REQUIREMENT", "message": req_id})
    return issues
