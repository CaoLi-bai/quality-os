from __future__ import annotations

import ast
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .context import compile_context
from .hub import QualityHub
from .models import dump_json, load_json, validate_cases, validate_spec
from .proof import prove_test_value
from .providers import create_provider
from .report import generate_report
from .runner import run_pytest
from .triage import triage_run


class GateFailure(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, root: Path, run_dir: Path, provider_name: str, resume: bool = False):
        self.root = root
        self.run_dir = run_dir
        self.provider = create_provider(provider_name, root)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        progress_path = self.run_dir / "progress.json"
        provider_path = self.run_dir / "provider-evidence.json"
        self.progress = load_json(progress_path) if resume and progress_path.exists() else {"run_id": run_dir.name, "status": "running", "stages": []}
        self.provider_evidence = load_json(provider_path) if resume and provider_path.exists() else []
        self.progress["status"] = "running"
        self.progress.pop("error", None)

    def completed(self, name: str) -> bool:
        return any(item["name"] == name and item["status"] == "passed" for item in self.progress["stages"])

    def stage(self, name: str, status: str, artifact: str = "") -> None:
        existing = next((item for item in self.progress["stages"] if item["name"] == name), None)
        value = {"name": name, "status": status, "artifact": artifact, "updated_at": datetime.now(timezone.utc).isoformat()}
        if existing:
            existing.update(value)
        else:
            self.progress["stages"].append(value)
        dump_json(self.run_dir / "progress.json", self.progress)

    def generate(self, stage: str, context: dict, schema: dict) -> dict:
        result = self.provider.generate(stage, context, schema)
        evidence_dir = self.run_dir / "agent" / stage
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "raw.txt").write_text(result.raw, encoding="utf-8")
        dump_json(evidence_dir / "output.json", result.output)
        dump_json(evidence_dir / "context.json", context)
        self.provider_evidence.append(result.evidence())
        dump_json(self.run_dir / "provider-evidence.json", self.provider_evidence)
        return result.output

    def run(self) -> dict:
        hub = QualityHub(self.run_dir / "quality-hub.db")
        try:
            self.stage("validate-spec", "running")
            policy = load_json(self.root / "policies" / "gates.json")
            spec = load_json(self.root / "specs" / "requirements.json")
            issues = validate_spec(spec, policy)
            context = compile_context(self.root, ["specs/refund-prd.md", "specs/untrusted-external.md"], trusted=False)
            dump_json(self.run_dir / "context-security.json", context["security_findings"])
            if issues:
                raise GateFailure(json.dumps(issues, ensure_ascii=False))
            if not context["security_findings"]:
                raise GateFailure("Prompt-injection fixture was not detected")
            self.stage("validate-spec", "passed", "context-security.json")

            if self.completed("plan"):
                plan = load_json(self.run_dir / "agent" / "plan" / "output.json")
            else:
                self.stage("plan", "running")
                planning_context = compile_context(self.root, ["specs/requirements.json", "specs/cases.json"], trusted=True)
                plan = self.generate("plan", planning_context, {
                    "type": "object", "required": ["strategy", "case_file", "human_review_required"],
                    "properties": {"strategy": {"type": "string"}, "case_file": {"type": "string"}, "human_review_required": {"type": "array"}},
                })
            cases = load_json(self.root / plan["case_file"])
            case_issues = validate_cases(cases, spec)
            if case_issues:
                raise GateFailure(json.dumps(case_issues, ensure_ascii=False))
            hub.load(spec, cases)
            feature_path = self.run_dir / "feature_list.json"
            if not feature_path.exists():
                dump_json(feature_path, [{"category": case["risk"], "description": case["id"], "test": case["test_nodeid"], "passes": False} for case in cases["cases"]])
            self.stage("plan", "passed", "agent/plan/output.json")

            candidate_dir = self.run_dir / "candidates"
            if self.completed("generate"):
                generated_files = sorted(candidate_dir.glob("*.py"))
            else:
                self.stage("generate", "running")
                generation = self.generate("generate", {
                    "spec": spec, "cases": cases, "constraints": ["Python pytest", "stdlib HTTP client", "verify persisted state"],
                }, {
                    "type": "object", "required": ["files"],
                    "properties": {"files": {"type": "array", "items": {"type": "object", "required": ["target", "content"]}}},
                })
                generated_files = []
                for item in generation["files"]:
                    target = candidate_dir / Path(item["target"]).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if "content" in item:
                        target.write_text(item["content"], encoding="utf-8")
                    else:
                        shutil.copyfile(self.root / item["source"], target)
                    generated_files.append(target)
            if not generated_files:
                raise GateFailure("No candidate tests generated")
            self.stage("generate", "passed", "candidates/")

            if self.completed("independent-review"):
                review = load_json(self.run_dir / "agent" / "review" / "output.json")
            else:
                self.stage("independent-review", "running")
                review = self.generate("review", {
                    "spec": spec, "cases": cases,
                    "candidate_paths": [str(path) for path in generated_files],
                }, {
                    "type": "object", "required": ["verdict", "unsupported_assertions", "missing_risks"],
                    "properties": {"verdict": {"type": "string"}, "unsupported_assertions": {"type": "array"}, "missing_risks": {"type": "array"}},
                })
            for path in generated_files:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                tests = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
                if not tests or any(not any(isinstance(child, ast.Assert) for child in ast.walk(test)) for test in tests):
                    raise GateFailure(f"Candidate has a test without assertions: {path}")
            if review["verdict"] != "pass" or review["unsupported_assertions"] or review["missing_risks"]:
                raise GateFailure(f"Independent review rejected candidate: {review}")
            self.stage("independent-review", "passed", "agent/review/output.json")

            if not self.completed("execute-good-build"):
                self.stage("execute-good-build", "running")
                baseline = run_pytest(self.root, generated_files[0], self.run_dir / "execution", "baseline")
                hub.record_run(baseline.run_id, baseline.to_dict(), [case["test_nodeid"] for case in cases["cases"]])
                triage_run(self.run_dir / "execution")
                if baseline.exit_code != 0:
                    raise GateFailure("Candidate failed on good build")
            self.stage("execute-good-build", "passed", "execution/run.json")

            if self.completed("fault-proof"):
                proof = load_json(self.run_dir / "proof" / "proof.json")
            else:
                self.stage("fault-proof", "running")
                proof = prove_test_value(self.root, generated_files[0], self.run_dir / "proof")
            if proof["status"] != "passed":
                raise GateFailure("Candidate did not catch every mapped fault")
            self.stage("fault-proof", "passed", "proof/proof.json")
            features = load_json(feature_path)
            for feature in features:
                feature["passes"] = True
            dump_json(feature_path, features)

            self.progress["status"] = "pending_human_approval"
            self.stage("human-approval", "pending", "report.md")
            report = generate_report(self.run_dir)
            return {"progress": self.progress, "report": report}
        except Exception as error:
            self.progress["status"] = "blocked"
            self.progress["error"] = str(error)
            current = next((item for item in reversed(self.progress["stages"]) if item["status"] == "running"), None)
            if current:
                current["status"] = "blocked"
            dump_json(self.run_dir / "progress.json", self.progress)
            generate_report(self.run_dir)
            raise
        finally:
            hub.close()
