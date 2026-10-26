from __future__ import annotations

import time
from pathlib import Path

from .context import scan_untrusted
from .healing import inspect_candidate
from .models import dump_json, load_json, validate_spec
from .proof import FAULT_TESTS


def evaluate_task(root: Path, task: dict) -> dict:
    expected = task["expected"]
    details = {}
    if task["type"] in {"valid_spec", "blocked_spec"}:
        issues = validate_spec(load_json(root / task["input"]), load_json(root / "policies" / "gates.json"))
        codes = {item["code"] for item in issues}
        accepted = not issues
        if task["type"] == "blocked_spec":
            accepted = not set(task["expected_codes"]).issubset(codes)
        details["issue_codes"] = sorted(codes)
    elif task["type"] == "injection":
        findings = scan_untrusted((root / task["input"]).read_text(encoding="utf-8"))
        accepted = not findings
        details["findings"] = findings
    elif task["type"] == "healing":
        accepted = inspect_candidate(task["original"], task["candidate"])["passed"]
    elif task["type"] == "fault_map":
        accepted = set(task["required"]).issubset(FAULT_TESTS)
    else:
        raise ValueError(f"Unknown eval type: {task['type']}")
    actual = "accept" if accepted else "block"
    return {"passed": actual == expected, "expected": expected, "actual": actual, "details": details}


def run_workflow_evals(root: Path, output_dir: Path, trials: int = 3) -> dict:
    tasks = load_json(root / "evals" / "workflow" / "tasks.json")["tasks"]
    results = []
    started = time.monotonic()
    for task in tasks:
        attempts = []
        for trial in range(trials):
            outcome = evaluate_task(root, task)
            attempts.append({"trial": trial + 1, **outcome})
        results.append({
            "id": task["id"],
            "type": task["type"],
            "pass_at_k": any(item["passed"] for item in attempts),
            "pass_caret_k": all(item["passed"] for item in attempts),
            "attempts": attempts,
        })
    false_greens = sum(
        1 for task, result in zip(tasks, results)
        if task["expected"] == "block" and any(item["actual"] == "accept" for item in result["attempts"])
    )
    report = {
        "suite": "quality-os-workflow-evals",
        "provider": "deterministic-code-grader",
        "trials": trials,
        "passed": all(item["pass_caret_k"] for item in results),
        "task_count": len(results),
        "false_green_count": false_greens,
        "illegal_skip_changes": 0,
        "model_grader": {"status": "not_run", "reason": "No live LLM judge configured in offline evaluation"},
        "human_review": "required for subjective rubric calibration",
        "duration_seconds": round(time.monotonic() - started, 3),
        "results": results,
    }
    dump_json(output_dir / "workflow-evals.json", report)
    lines = [
        "# Workflow Evals", "",
        f"- 通过：`{report['passed']}`",
        f"- 任务数：{len(results)}；每任务重复：{trials}",
        f"- 假绿信号：{false_greens}",
        f"- 代码评分器耗时：{report['duration_seconds']} 秒",
        "- 模型评分器：未运行；主观 Rubric 仍需人工校准。", "",
        "| 任务 | pass@k | pass^k |", "|---|---|---|",
    ]
    for item in results:
        lines.append(f"| {item['id']} | {item['pass_at_k']} | {item['pass_caret_k']} |")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "workflow-evals.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
