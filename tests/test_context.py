from pathlib import Path

from quality_os.context import compile_context, scan_untrusted

ROOT = Path(__file__).parents[1]


def test_prompt_injection_is_excluded_from_model_context():
    context = compile_context(ROOT, ["specs/untrusted-external.md"], trusted=False)
    assert context["security_findings"]
    assert context["documents"] == []


def test_benign_chinese_requirement_is_not_a_false_positive():
    assert scan_untrusted("退款必须经过人工审核，禁止绕过权限检查。") == []
