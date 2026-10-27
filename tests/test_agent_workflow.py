import json
from types import SimpleNamespace

from quality_os.agent_workflow import AgentWorkflow, verify_existing


def make_workflow(tmp_path):
    document = tmp_path / "PRD.md"
    document.write_text("# 需求\n用户能查看自己的订单。", encoding="utf-8")
    return AgentWorkflow(tmp_path / "run", "http://127.0.0.1:8765", [document], install_dependencies=False)


def test_workspace_uses_real_playwright_cli_and_records_document_hash(tmp_path):
    workflow = make_workflow(tmp_path)
    sources = workflow.write_workspace()
    config = json.loads((workflow.workspace / ".playwright" / "cli.config.json").read_text(encoding="utf-8"))
    package = json.loads((workflow.workspace / "package.json").read_text(encoding="utf-8"))
    assert config["browser"]["launchOptions"]["channel"] == "msedge"
    assert package["devDependencies"]["@playwright/cli"] == "0.1.22"
    assert "trace: 'retain-on-failure'" in (workflow.workspace / "playwright.config.ts").read_text(encoding="utf-8")
    assert len(sources["documents"][0]["sha256"]) == 64


def test_candidate_audit_rejects_skip_and_empty_assertions(tmp_path):
    workflow = make_workflow(tmp_path)
    workflow.write_workspace()
    test_file = workflow.workspace / "tests" / "candidates" / "bad.spec.ts"
    test_file.write_text("import { test, expect } from '@playwright/test';\ntest.skip('bad', async ({ page }) => { expect(true).toBe(true); });", encoding="utf-8")
    result = workflow.report(None, None, "blocked", "非法 Skip")
    assert result["status"] == "blocked"
    assert "非法 Skip" in result["error"]


def test_agent_success_without_junit_is_not_a_pass(tmp_path, monkeypatch):
    workflow = make_workflow(tmp_path)
    workflow.write_workspace()
    monkeypatch.setattr("quality_os.agent_workflow.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Agent 说成功了", stderr=""))
    result = workflow.run_tests("first")
    assert result["passed"] is False
    assert result["tests"] == 0


def test_missing_real_exploration_blocks_and_preserves_report(tmp_path, monkeypatch):
    workflow = make_workflow(tmp_path)
    monkeypatch.setattr(workflow, "run_agent", lambda *args, **kwargs: None)
    result = workflow.run()
    assert result["status"] == "blocked"
    assert "test-plan.md" in result["error"]
    assert (tmp_path / "run" / "report.html").exists()


def test_kimi_session_is_created_then_reused(tmp_path, monkeypatch):
    workflow = make_workflow(tmp_path)
    commands = []

    def fake_run(stage, command, timeout):
        commands.append(command)
        stage_dir = workflow.run_dir / "agent" / stage
        stage_dir.mkdir(parents=True)
        (stage_dir / "stdout.log").write_text("To resume this session: kimi -r session_real", encoding="utf-8")
        return {"command": command}

    monkeypatch.setattr(workflow, "run_command", fake_run)
    workflow.run_agent("planner", "计划")
    workflow.run_agent("generator", "生成")
    assert "--session" not in commands[0]
    assert commands[1][1:3] == ["--session", "session_real"]
    assert workflow.session_id == "session_real"
    monkeypatch.setattr("quality_os.agent_workflow.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("kimi 不存在")))
    workflow.run_agent("review", "无 Kimi CLI 时使用文本会话证据")
    assert workflow.session_id == "session_real"


def test_fault_environment_must_fail_with_real_test_evidence(tmp_path, monkeypatch):
    workflow = AgentWorkflow(
        tmp_path / "run", "http://127.0.0.1:8765", [],
        install_dependencies=False, fault_targets={"over-refund": "http://127.0.0.1:8766"},
    )
    monkeypatch.setattr(workflow, "write_workspace", lambda: None)
    monkeypatch.setattr(workflow, "plan", lambda: None)
    monkeypatch.setattr(workflow, "challenge", lambda: None)
    monkeypatch.setattr(workflow, "generate", lambda: None)

    def fake_execution(label, target_url=None):
        failed = target_url is not None
        return {
            "label": label, "tests": 1, "failures": int(failed), "errors": 0, "skipped": 0,
            "exit_code": int(failed), "passed": not failed, "evidence_dir": label,
        }

    monkeypatch.setattr(workflow, "run_tests", fake_execution)
    result = workflow.run()
    assert result["status"] == "pending_human_approval"
    assert result["fault_proof"]["status"] == "passed"
    assert result["fault_proof"]["faults"][0]["caught"] is True


def test_verify_existing_reuses_candidates_without_regenerating(tmp_path, monkeypatch):
    workflow = make_workflow(tmp_path)
    workflow.write_workspace()
    candidate = workflow.workspace / "tests" / "candidates" / "orders.spec.ts"
    candidate.write_text("import { test, expect } from '@playwright/test';\ntest('订单', async ({page}) => { expect(1).toBe(1); });", encoding="utf-8")
    (tmp_path / "run" / "report.json").write_text(json.dumps({"url": workflow.url, "browser": "msedge", "events": []}), encoding="utf-8")
    monkeypatch.setattr(AgentWorkflow, "run_tests", lambda self, label: {"label": label, "tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": True, "evidence_dir": label})
    result = verify_existing(tmp_path / "run")
    assert result["status"] == "pending_human_approval"
    assert result["final_execution"]["label"] == "independent"


def test_report_records_project_memory_at_quality_root(tmp_path):
    document = tmp_path / "PRD.md"
    document.write_text("需求", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "agent-runs" / "run"
    workflow = AgentWorkflow(run_dir, "http://localhost:5173", [document], project_key="demo")
    workflow.write_workspace()
    execution = {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": True}
    workflow.report(execution, execution, "pending_human_approval")
    assert (tmp_path / "artifacts" / "projects" / "demo" / "profile.json").exists()
    assert not (tmp_path / "artifacts" / "artifacts" / "projects" / "demo").exists()
