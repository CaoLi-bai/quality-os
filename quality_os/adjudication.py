from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import dump_json
from .providers import create_provider


SCHEMA = {
    "type": "object",
    "required": ["cases"],
    "properties": {
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "verdict", "severity", "evidence", "reasoning", "suggested_action"],
                "properties": {
                    "name": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["product_defect", "test_oracle_issue", "needs_human"]},
                    "severity": {"type": "string"},
                    "evidence": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "suggested_action": {"type": "string"},
                },
            },
        }
    },
}


def adjudicate_file(input_path: Path, output_dir: Path, provider_name: str = "kimi", batch_size: int = 4) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    cases = source["cases"]
    provider = create_provider(provider_name, input_path.parent)
    output_dir.mkdir(parents=True, exist_ok=True)
    verdicts = []
    evidence = []
    for index in range(0, len(cases), batch_size):
        batch = cases[index:index + batch_size]
        context = {key: value for key, value in source.items() if key != "cases"}
        context["cases"] = batch
        context["contract"] = "必须逐条返回本批所有 name，不得遗漏、合并或新增。每批最多 4 条是为了避免漏判。"
        result = provider.generate("adjudicate", context, SCHEMA)
        returned = result.output.get("cases", [])
        expected_names = [case["name"] for case in batch]
        returned_names = [case.get("name") for case in returned]
        if sorted(returned_names) != sorted(expected_names):
            raise ValueError(f"仲裁结果数量或名称不完整：期望 {expected_names}，实际 {returned_names}")
        batch_dir = output_dir / f"batch-{index // batch_size + 1}"
        batch_dir.mkdir(exist_ok=True)
        (batch_dir / "raw.txt").write_text(result.raw, encoding="utf-8")
        dump_json(batch_dir / "output.json", result.output)
        evidence.append(result.evidence())
        verdicts.extend(returned)
    summary = {
        "mechanical_failures": len(verdicts),
        "product_defects": sum(case["verdict"] == "product_defect" for case in verdicts),
        "test_oracle_issues": sum(case["verdict"] == "test_oracle_issue" for case in verdicts),
        "needs_human": sum(case["verdict"] == "needs_human" for case in verdicts),
    }
    report = {"cases": verdicts, "summary": summary, "provider_evidence": evidence, "llm_adjudication": True}
    dump_json(output_dir / "adjudication.json", report)
    return report
