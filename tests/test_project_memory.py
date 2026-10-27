import json

from quality_os.agent_workflow import AgentWorkflow
from quality_os.project_memory import ProjectMemory


def test_project_memory_reuses_candidates_for_regression(tmp_path, monkeypatch):
    document = tmp_path / "PRD.md"
    document.write_text("# 需求\n用户能查看订单。", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "agent-runs" / "first"
    workflow = AgentWorkflow(run_dir, "http://127.0.0.1:8765", [document], install_dependencies=False)
    workflow.write_workspace()
    candidate = workflow.workspace / "tests" / "candidates" / "orders.spec.ts"
    candidate.write_text("import { test, expect } from '@playwright/test';\ntest('订单', async ({page}) => { expect(1).toBe(1); });", encoding="utf-8")
    execution = {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": True}
    report = workflow.report(execution, execution, "pending_human_approval")
    memory = ProjectMemory(tmp_path, "orders")
    memory.record(run_dir, report)
    monkeypatch.setattr(AgentWorkflow, "run_tests", lambda self, label: {**execution, "label": label, "evidence_dir": "evidence"})
    regression = memory.regression(tmp_path / "artifacts" / "agent-runs" / "second", install_dependencies=False)
    profile = json.loads((tmp_path / "artifacts" / "projects" / "orders" / "profile.json").read_text(encoding="utf-8"))
    assert regression["ai_generation_used"] is False
    assert regression["comparison"] == "持续通过"
    assert len(profile["runs"]) == 2
    assert (tmp_path / "artifacts" / "agent-runs" / "second" / "workspace" / "tests" / "candidates" / "orders.spec.ts").exists()

    profile["latest_status"] = "tests_failed"
    (tmp_path / "artifacts" / "projects" / "orders" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    monkeypatch.setattr(AgentWorkflow, "run_tests", lambda self, label: {**execution, "passed": False, "failures": 1, "label": label})
    failed = memory.regression(tmp_path / "artifacts" / "agent-runs" / "third", install_dependencies=False)
    assert failed["comparison"] == "结果一致（仍有失败）"
    assert failed["project_key"] == "orders"
