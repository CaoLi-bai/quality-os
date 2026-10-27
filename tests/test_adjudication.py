import json

import pytest

from quality_os.adjudication import adjudicate_file
from quality_os.providers.base import GenerationResult


def result_for(batch):
    return GenerationResult(
        provider="kimi", stage="adjudicate",
        output={"cases": [{"name": case["name"], "verdict": "test_oracle_issue", "severity": "low", "evidence": "证据", "reasoning": "理由", "suggested_action": "修正"} for case in batch["cases"]]},
        raw="{}", duration_ms=1, is_ai=True, command=[], model="test",
    )


def test_adjudication_batches_require_every_case(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"cases": [{"name": f"case-{index}"} for index in range(5)]}), encoding="utf-8")

    class FakeProvider:
        def generate(self, stage, context, schema):
            return result_for(context)

    import quality_os.adjudication as module
    original = module.create_provider
    module.create_provider = lambda *args: FakeProvider()
    try:
        report = adjudicate_file(source, tmp_path / "out")
    finally:
        module.create_provider = original
    assert report["summary"]["mechanical_failures"] == 5
    assert len(report["provider_evidence"]) == 2


def test_adjudication_rejects_missing_case(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"cases": [{"name": "case-1"}]}), encoding="utf-8")

    class IncompleteProvider:
        def generate(self, stage, context, schema):
            return result_for({"cases": []})

    import quality_os.adjudication as module
    original = module.create_provider
    module.create_provider = lambda *args: IncompleteProvider()
    try:
        with pytest.raises(ValueError, match="不完整"):
            adjudicate_file(source, tmp_path / "out")
    finally:
        module.create_provider = original
