from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_workflow import AgentWorkflow
from .models import dump_json, load_json


class ProjectMemory:
    def __init__(self, root: Path, project_key: str):
        if not project_key or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in project_key):
            raise ValueError("project-key 只能包含字母、数字、横线和下划线。")
        self.directory = root / "artifacts" / "projects" / project_key
        self.project_key = project_key

    def record(self, run_dir: Path, report: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        profile_path = self.directory / "profile.json"
        previous = load_json(profile_path) if profile_path.exists() else {}
        runs = previous.get("runs", [])
        runs.append({
            "run_id": report["run_id"],
            "run_dir": str(run_dir),
            "status": report["status"],
            "tests": (report.get("final_execution") or {}).get("tests", 0),
            "failures": (report.get("final_execution") or {}).get("failures", 0),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        profile = {
            "project_key": self.project_key,
            "url": report["url"],
            "browser": report.get("browser", "msedge"),
            "latest_run_dir": str(run_dir),
            "latest_status": report["status"],
            "runs": runs,
            "failure_history": self.failure_history(runs),
        }
        dump_json(profile_path, profile)
        workspace = run_dir / "workspace"
        for name in ("tests", "specs"):
            source = workspace / name
            if source.exists():
                shutil.copytree(source, self.directory / "memory" / name, dirs_exist_ok=True)
        for name in ("package.json", "package-lock.json", "playwright.config.ts"):
            source = workspace / name
            if source.exists():
                target = self.directory / "memory" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        if (workspace / "inputs").exists():
            shutil.copytree(workspace / "inputs", self.directory / "memory" / "inputs", dirs_exist_ok=True)

    @staticmethod
    def failure_history(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"run_id": run["run_id"], "status": run["status"], "failures": run["failures"]} for run in runs if run["status"] != "pending_human_approval"]

    def regression(self, run_dir: Path, install_dependencies: bool = True) -> dict[str, Any]:
        profile = load_json(self.directory / "profile.json")
        memory = self.directory / "memory"
        if not (memory / "tests" / "candidates").exists():
            raise ValueError("项目记忆中还没有可回归的候选测试。")
        workflow = AgentWorkflow(run_dir, profile["url"], [], browser=profile.get("browser", "msedge"), install_dependencies=False)
        workflow.workspace.mkdir(parents=True)
        for item in memory.iterdir():
            target = workflow.workspace / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
        workflow.audit_candidates()
        if install_dependencies:
            workflow.run_command("setup-regression", ["npm", "install", "--no-audit", "--no-fund"], 300)
        previous_status = profile.get("latest_status")
        execution = workflow.run_tests("regression")
        status = "pending_human_approval" if execution["passed"] else "tests_failed"
        result = workflow.report(execution, execution, status, "" if execution["passed"] else "项目记忆回归仍有失败。", ai_generation_used=False)
        result.update({
            "project_key": self.project_key,
            "regression_from": profile.get("latest_run_dir"),
            "previous_status": previous_status,
            "comparison": ("持续通过" if status == "pending_human_approval" else "结果一致（仍有失败）") if previous_status == status else f"状态变化：{previous_status} → {status}",
        })
        dump_json(run_dir / "report.json", result)
        self.record(run_dir, result)
        return result
