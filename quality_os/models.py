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
        return [{"code": "EMPTY_SPEC", "message": "规格必须包含至少一条 requirements 需求。"}]
    seen: set[str] = set()
    for item in requirements:
        req_id = item.get("id", "<missing>")
        if req_id in seen:
            issues.append({"code": "DUPLICATE_ID", "message": f"需求 ID 重复：{req_id}"})
        seen.add(req_id)
        for field in ("id", "source", "risk", "rule", "oracle_source"):
            if not item.get(field):
                issues.append({"code": "MISSING_FIELD", "message": f"需求 {req_id} 缺少必填字段：{field}"})
        if item.get("oracle_source") not in policy["allowed_oracle_sources"]:
            issues.append({"code": "UNAPPROVED_ORACLE", "message": f"需求 {req_id} 的 Oracle 来源未经批准，不能从产品现有行为反推。"})
        if not item.get("acceptance"):
            issues.append({"code": "MISSING_ACCEPTANCE", "message": f"需求 {req_id} 缺少可验证的验收条件。"})
        if item["risk"] in policy["high_risks"] and item.get("unresolved"):
            issues.append({"code": "UNRESOLVED_HIGH_RISK", "message": f"需求 {req_id} 属于高风险且仍有未决项：{item['unresolved']}"})
    if not spec.get("approved_by"):
        issues.append({"code": "MISSING_APPROVAL", "message": "规格没有真实命名批准人；AI 不能代签。"})
    return issues


def validate_cases(cases: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    req_ids = {item["id"] for item in spec.get("requirements", [])}
    seen: set[str] = set()
    covered: set[str] = set()
    for case in cases.get("cases", []):
        case_id = case.get("id", "<missing>")
        if case_id in seen:
            issues.append({"code": "DUPLICATE_CASE", "message": f"用例 ID 重复：{case_id}"})
        seen.add(case_id)
        if not case.get("test_nodeid") or not case.get("oracle"):
            issues.append({"code": "INCOMPLETE_CASE", "message": f"用例 {case_id} 缺少 test_nodeid 或可观测 oracle。"})
        links = case.get("requirement_ids", [])
        if not links:
            issues.append({"code": "ORPHAN_CASE", "message": f"用例 {case_id} 未关联任何需求。"})
        for req_id in links:
            covered.add(req_id)
            if req_id not in req_ids:
                issues.append({"code": "UNKNOWN_REQUIREMENT", "message": f"用例 {case_id} 关联了不存在的需求：{req_id}"})
    for req_id in sorted(req_ids - covered):
        issues.append({"code": "UNCOVERED_REQUIREMENT", "message": f"需求 {req_id} 没有任何用例覆盖。"})
    return issues
