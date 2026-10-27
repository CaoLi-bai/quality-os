from __future__ import annotations

import html
import json
from pathlib import Path


STATUS_ZH = {
    "unknown": "未知",
    "running": "执行中",
    "passed": "通过",
    "failed": "失败",
    "blocked": "已阻断",
    "pending": "待处理",
    "pending_human_approval": "等待人工批准",
    "not_run": "未执行",
    "not_ready": "尚未具备批准条件",
    "not_measured": "未统计",
    "unavailable_until_named_human_approval": "命名审核人批准前不可计算",
}

STAGE_ZH = {
    "validate-spec": "规格与安全校验",
    "plan": "风险测试规划",
    "generate": "候选测试生成",
    "independent-review": "独立审查",
    "execute-good-build": "正确版本执行",
    "fault-proof": "故障检出证明",
    "human-approval": "人工批准",
}

SUMMARY_ZH = {
    "workflow_status": "工作流状态",
    "provider": "模型提供方",
    "ai_generation_used": "真实 AI 生成",
    "baseline": "正确版本基线",
    "faults_caught": "注入故障检出",
    "human_approval": "人工审批",
    "provider_duration_ms": "模型调用耗时（毫秒）",
    "model_cost": "模型费用",
    "human_review_time": "人工审查耗时",
    "cost_per_accepted_test": "每条验收测试成本",
    "false_green_claimed": "宣称假绿",
}


def read_optional(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def chinese_value(value: object) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    return STATUS_ZH.get(str(value), str(value))


def generate_report(run_dir: Path) -> dict:
    progress = read_optional(run_dir / "progress.json") or {}
    proof = read_optional(run_dir / "proof" / "proof.json")
    baseline = read_optional(run_dir / "execution" / "run.json")
    triage = read_optional(run_dir / "execution" / "triage.json")
    provider = read_optional(run_dir / "provider-evidence.json") or []
    caught = sum(1 for item in (proof or {}).get("faults", []) if item["caught"])
    total_faults = len((proof or {}).get("faults", []))
    workflow_status = progress.get("status", "unknown")
    next_step = (
        "打开报告逐项核对证据，由命名审核人批准或拒绝候选测试；系统不会自动合并。"
        if workflow_status == "pending_human_approval"
        else f"先处理阻断原因：{progress.get('error', '查看当前阶段日志')}；修复后使用 --resume 重跑，不得删测试或改断言求绿。"
    )
    summary = {
        "workflow_status": workflow_status,
        "provider": ", ".join(sorted({item["provider"] for item in provider})) or "unknown",
        "ai_generation_used": any(item["is_ai"] for item in provider),
        "baseline": baseline.get("status") if baseline else "not_run",
        "faults_caught": f"{caught}/{total_faults}",
        "human_approval": "pending" if workflow_status == "pending_human_approval" else "not_ready",
        "provider_duration_ms": sum(item["duration_ms"] for item in provider),
        "model_cost": "not_measured",
        "human_review_time": "not_measured",
        "cost_per_accepted_test": "unavailable_until_named_human_approval",
        "false_green_claimed": False,
        "next_step": next_step,
    }
    lines = [
        "# QualityOS 质量证据报告", "",
        f"- 工作流状态：**{chinese_value(workflow_status)}**",
        f"- 模型提供方：`{summary['provider']}`",
        f"- 真实 AI 生成：**{chinese_value(summary['ai_generation_used'])}**",
        f"- 正确版本基线：**{chinese_value(summary['baseline'])}**",
        f"- 注入故障检出：**{summary['faults_caught']}**",
        f"- 人工审批：**{chinese_value(summary['human_approval'])}（不会自动合并）**",
        f"- 下一步：{next_step}",
        "- 剩余风险：本报告仅覆盖演示规格与已登记用例，不代表全部业务风险。", "",
        "## 阶段证据", "",
        "| 阶段 | 状态 | 产物 |", "|---|---|---|",
    ]
    for stage in progress.get("stages", []):
        lines.append(f"| {STAGE_ZH.get(stage['name'], stage['name'])} | {chinese_value(stage['status'])} | `{stage.get('artifact', '')}` |")
    lines += ["", "## 故障证明", "", "只有正确版本通过且故障版本失败，才能证明测试具有缺陷检出能力。", "", "| 故障 | 是否抓到 | 证据 |", "|---|---|---|"]
    for item in (proof or {}).get("faults", []):
        lines.append(f"| {item['fault']} | {chinese_value(item['caught'])} | `{item['evidence_dir']}` |")
    lines += ["", "## 失败归因", ""]
    if triage and triage.get("failures"):
        for failure in triage["failures"]:
            lines.append(f"- `{failure['test']}`：{failure['rationale']}；允许定位器候选修复：{chinese_value(failure['auto_healing_allowed'])}")
    else:
        lines.append("基线执行无失败；故障注入产生的预期失败保留在各自证明目录。")
    lines += ["", "## 门禁结论", "", "技术证据完成后仍需命名审核人批准候选测试资产。禁止通过修改断言、删除或 Skip 测试获得绿色结果。", ""]
    markdown = "\n".join(lines)
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")
    summary_rows = "".join(
        f"<tr><th>{html.escape(SUMMARY_ZH.get(key, key))}</th><td>{html.escape(chinese_value(value))}</td></tr>"
        for key, value in summary.items()
    )
    page = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>QualityOS 质量证据报告</title>
<style>body{{font:15px/1.65 system-ui;margin:40px auto;max-width:1000px;padding:0 24px;background:#0b1020;color:#e7ecf5}}h1,h2{{color:#75e6c4}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #40506a;padding:9px;text-align:left}}code{{color:#ffd68a}}.card{{background:#111a2d;padding:20px;border-radius:12px;margin-bottom:24px}}pre{{white-space:pre-wrap}}</style></head>
<body><h1>QualityOS 质量证据报告</h1><div class='card'><table>{summary_rows}</table></div>
<h2>完整证据与下一步</h2><pre>{html.escape(markdown)}</pre></body></html>"""
    (run_dir / "report.html").write_text(page, encoding="utf-8")
    dump = {"summary": summary, "markdown": str(run_dir / "report.md"), "html": str(run_dir / "report.html")}
    (run_dir / "report.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dump
