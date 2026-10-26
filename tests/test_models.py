import json
from pathlib import Path

from quality_os.models import load_json, validate_cases, validate_spec

ROOT = Path(__file__).parents[1]


def test_approved_spec_and_cases_pass_deterministic_gates():
    policy = load_json(ROOT / "policies" / "gates.json")
    spec = load_json(ROOT / "specs" / "requirements.json")
    cases = load_json(ROOT / "specs" / "cases.json")
    assert validate_spec(spec, policy) == []
    assert validate_cases(cases, spec) == []


def test_ambiguous_high_risk_spec_is_blocked():
    policy = load_json(ROOT / "policies" / "gates.json")
    spec = load_json(ROOT / "specs" / "ambiguous-requirements.json")
    codes = {issue["code"] for issue in validate_spec(spec, policy)}
    assert {"UNAPPROVED_ORACLE", "UNRESOLVED_HIGH_RISK", "MISSING_ACCEPTANCE", "MISSING_APPROVAL"} <= codes


def test_orphan_and_unknown_case_links_are_blocked():
    spec = load_json(ROOT / "specs" / "requirements.json")
    invalid = {"cases": [{"id": "CASE-X", "requirement_ids": ["REQ-NOT-FOUND"], "test_nodeid": "", "oracle": ""}]}
    codes = {issue["code"] for issue in validate_cases(invalid, spec)}
    assert "UNKNOWN_REQUIREMENT" in codes
    assert "INCOMPLETE_CASE" in codes
    assert "UNCOVERED_REQUIREMENT" in codes
