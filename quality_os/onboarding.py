from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .context import scan_untrusted
from .models import dump_json, validate_cases, validate_spec
from .providers import create_provider


ONBOARD_SCHEMA = {
    "type": "object",
    "required": ["spec", "cases", "questions"],
    "properties": {
        "spec": {
            "type": "object",
            "required": ["spec_version", "requirements"],
            "properties": {
                "spec_version": {"type": "string"},
                "approved_by": {"type": "string"},
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "source", "risk", "rule", "oracle_source", "unresolved", "acceptance"],
                        "properties": {
                            "id": {"type": "string"},
                            "source": {"type": "string"},
                            "risk": {"type": "string"},
                            "rule": {"type": "string"},
                            "oracle_source": {"type": "string", "enum": ["approved_spec"]},
                            "unresolved": {"type": "array", "items": {"type": "string"}},
                            "acceptance": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        },
        "cases": {
            "type": "object",
            "required": ["cases"],
            "properties": {
                "cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "requirement_ids", "risk", "test_nodeid", "oracle"],
                        "properties": {
                            "id": {"type": "string"},
                            "requirement_ids": {"type": "array", "items": {"type": "string"}},
                            "risk": {"type": "string"},
                            "test_nodeid": {"type": "string"},
                            "oracle": {"type": "string"},
                        },
                    },
                }
            },
        },
        "questions": {"type": "array", "items": {"type": "string"}},
    },
}


def load_documents(paths: list[Path], root: Path) -> dict[str, Any]:
    sources = []
    findings = []
    documents = []
    for path in paths:
        resolved = path.resolve()
        content = resolved.read_text(encoding="utf-8")
        try:
            display_path = str(resolved.relative_to(root.resolve()))
        except ValueError:
            display_path = str(resolved)
        sources.append({
            "path": display_path,
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "trusted": False,
        })
        matches = scan_untrusted(content)
        if matches:
            findings.append({"path": display_path, "patterns": matches, "action": "已从模型上下文排除"})
        else:
            documents.append({"path": display_path, "content": content})
    return {"sources": sources, "security_findings": findings, "documents": documents}


def onboard_project(root: Path, documents: list[Path], output_dir: Path, provider_name: str = "kimi") -> dict[str, Any]:
    context = load_documents(documents, root)
    if not context["documents"]:
        raise ValueError("所有文档都因提示词注入风险被隔离，未调用模型。请先清理文档中的指令性攻击内容。")
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(output_dir / "context-security.json", context["security_findings"])
    provider = create_provider(provider_name, root)
    result = provider.generate("onboard", context, ONBOARD_SCHEMA)
    output = result.output
    spec = output.get("spec")
    cases = output.get("cases")
    if not isinstance(spec, dict) or not isinstance(cases, dict):
        raise ValueError("模型输出缺少 spec 或 cases 对象，未生成项目草案。")
    spec["approved_by"] = ""
    questions = output.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("模型输出的 questions 必须是数组。")
    spec_issues = validate_spec(spec, {"allowed_oracle_sources": ["approved_spec"], "high_risks": ["money", "authorization", "security", "compliance"]})
    case_issues = validate_cases(cases, spec)
    evidence_dir = output_dir / "agent" / "onboard"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "raw.txt").write_text(result.raw, encoding="utf-8")
    dump_json(evidence_dir / "output.json", output)
    dump_json(evidence_dir / "context.json", context)
    dump_json(output_dir / "provider-evidence.json", [result.evidence()])
    dump_json(output_dir / "requirements.draft.json", spec)
    dump_json(output_dir / "cases.draft.json", cases)
    dump_json(output_dir / "questions.json", questions)
    report = {
        "status": "waiting_for_human_approval",
        "provider": result.provider,
        "ai_generation_used": result.is_ai,
        "requirement_count": len(spec.get("requirements", [])),
        "case_count": len(cases.get("cases", [])),
        "questions": questions,
        "spec_issues": spec_issues,
        "case_issues": case_issues,
        "security_findings": context["security_findings"],
        "tests_executed": False,
        "next_step": "逐条确认业务规则和未决项，由真实业务负责人填写 approved_by，再把草案转为正式规格。",
    }
    dump_json(output_dir / "onboarding.json", report)
    lines = [
        "# 项目接入草案", "",
        "本目录是 AI 生成的候选资产，不是已批准规格，也不代表真实项目测试已经执行或通过。", "",
        f"- 模型提供方：`{result.provider}`",
        f"- 真实 AI 生成：`{str(result.is_ai).lower()}`",
        f"- 候选需求：{report['requirement_count']} 条；候选用例：{report['case_count']} 条",
        "- 当前门禁：**等待真实业务负责人批准**",
        "- 测试执行：**未执行**", "",
        "## 必须回答的问题", "",
    ]
    lines.extend(f"- {question}" for question in questions) if questions else lines.append("- 模型未列出问题；仍须由业务负责人逐条复核，不能自动批准。")
    lines += ["", "## 确定性校验发现", ""]
    issues = spec_issues + case_issues
    lines.extend(f"- `{item['code']}`：{item['message']}" for item in issues) if issues else lines.append("- 未发现结构问题，但仍需人工批准。")
    if context["security_findings"]:
        lines += ["", "## 文档安全", "", "以下文档命中提示词注入规则，已排除，未交给模型："]
        lines.extend(f"- `{item['path']}`" for item in context["security_findings"])
    lines += ["", "## 下一步", "", report["next_step"], "", "不要直接把这些草案合并进正式测试资产。", ""]
    (output_dir / "onboarding.md").write_text("\n".join(lines), encoding="utf-8")
    return report
