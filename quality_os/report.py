from __future__ import annotations

import html
import json
from pathlib import Path


def read_optional(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def generate_report(run_dir: Path) -> dict:
    progress = read_optional(run_dir / "progress.json") or {}
    proof = read_optional(run_dir / "proof" / "proof.json")
    baseline = read_optional(run_dir / "execution" / "run.json")
    triage = read_optional(run_dir / "execution" / "triage.json")
    provider = read_optional(run_dir / "provider-evidence.json") or []
    caught = sum(1 for item in (proof or {}).get("faults", []) if item["caught"])
    total_faults = len((proof or {}).get("faults", []))
    summary = {
        "workflow_status": progress.get("status", "unknown"),
        "provider": ", ".join(sorted({item["provider"] for item in provider})) or "unknown",
        "ai_generation_used": any(item["is_ai"] for item in provider),
        "baseline": baseline.get("status") if baseline else "not_run",
        "faults_caught": f"{caught}/{total_faults}",
        "human_approval": "pending",
        "provider_duration_ms": sum(item["duration_ms"] for item in provider),
        "model_cost": "not_measured",
        "human_review_time": "not_measured",
        "cost_per_accepted_test": "unavailable_until_named_human_approval",
        "false_green_claimed": False,
    }
    lines = [
        "# QualityOS 质量证据报告", "",
        f"- 工作流状态：**{summary['workflow_status']}**",
        f"- Provider：`{summary['provider']}`",
        f"- 真实 AI 生成：`{summary['ai_generation_used']}`",
        f"- Good build：`{summary['baseline']}`",
        f"- 注入故障检出：**{summary['faults_caught']}**",
        "- 人工审批：**pending（未自动合并）**",
        "- 剩余风险：本报告仅覆盖演示规格与已登记用例，不代表全部业务风险。", "",
        "## 阶段证据", "",
        "| 阶段 | 状态 | 产物 |", "|---|---|---|",
    ]
    for stage in progress.get("stages", []):
        lines.append(f"| {stage['name']} | {stage['status']} | `{stage.get('artifact', '')}` |")
    lines += ["", "## 故障证明", "", "| 故障 | 被抓到 | 证据 |", "|---|---|---|"]
    for item in (proof or {}).get("faults", []):
        lines.append(f"| {item['fault']} | {item['caught']} | `{item['evidence_dir']}` |")
    lines += ["", "## 失败归因", ""]
    if triage and triage.get("failures"):
        for failure in triage["failures"]:
            lines.append(f"- `{failure['test']}`：{failure['category']}；自动修复：{failure['auto_healing_allowed']}")
    else:
        lines.append("基线执行无失败；故障注入产生的预期失败保留在各自证明目录。")
    lines += ["", "## 门禁结论", "", "技术证据完成后仍需命名审核人批准候选测试资产。禁止通过修改断言、删除或 Skip 测试获得绿色结果。", ""]
    markdown = "\n".join(lines)
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")
    page = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>QualityOS 质量证据报告</title>
<style>body{{font:15px/1.65 system-ui;margin:40px auto;max-width:1000px;padding:0 24px;background:#0b1020;color:#e7ecf5}}h1,h2{{color:#75e6c4}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #40506a;padding:9px;text-align:left}}code{{color:#ffd68a}}.card{{background:#111a2d;padding:20px;border-radius:12px}}pre{{white-space:pre-wrap}}</style></head>
<body><h1>QualityOS 质量证据报告</h1><div class='card'><pre>{html.escape(json.dumps(summary, ensure_ascii=False, indent=2))}</pre></div>
<h2>完整报告</h2><pre>{html.escape(markdown)}</pre></body></html>"""
    (run_dir / "report.html").write_text(page, encoding="utf-8")
    dump = {"summary": summary, "markdown": str(run_dir / "report.md"), "html": str(run_dir / "report.html")}
    (run_dir / "report.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dump
