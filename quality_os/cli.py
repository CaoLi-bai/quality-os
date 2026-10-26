from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .healing import propose_healing
from .hub import QualityHub
from .models import load_json, validate_spec
from .orchestrator import Orchestrator
from .report import generate_report
from .runner import run_pytest
from .triage import triage_run

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(prog="quality-os", description="Spec-driven, evidence-first AI-native testing workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run the complete governed workflow")
    run.add_argument("--provider", choices=["fixture", "kimi", "claude"], default="fixture")
    run.add_argument("--run-id", default="demo")
    run.add_argument("--resume", action="store_true", help="Reuse passed stage artifacts and rerun incomplete stages")
    run.add_argument("--root", type=Path, default=ROOT)

    validate = subparsers.add_parser("validate-spec", help="Validate a specification against deterministic gates")
    validate.add_argument("--spec", type=Path, required=True)
    validate.add_argument("--policy", type=Path, default=ROOT / "policies" / "gates.json")

    triage = subparsers.add_parser("triage", help="Classify preserved first failures")
    triage.add_argument("--run-dir", type=Path, required=True)

    heal = subparsers.add_parser("heal", help="Observe or propose a locator-only test repair")
    heal.add_argument("--source", type=Path, required=True)
    heal.add_argument("--output-dir", type=Path, required=True)
    heal.add_argument("--old", required=True)
    heal.add_argument("--new", required=True)
    heal.add_argument("--mode", choices=["observe", "propose"], default="observe")

    report = subparsers.add_parser("report", help="Regenerate quality evidence reports")
    report.add_argument("--run-dir", type=Path, required=True)

    trace = subparsers.add_parser("trace", help="Trace a requirement through the quality graph")
    trace.add_argument("--run-dir", type=Path, required=True)
    trace.add_argument("--requirement", required=True)

    browser = subparsers.add_parser("browser", help="Run real browser tests with evidence")
    browser.add_argument("--test-path", type=Path, default=ROOT / "tests" / "e2e" / "test_refund_ui.py")
    browser.add_argument("--run-dir", type=Path, default=ROOT / "artifacts" / "browser")
    browser.add_argument("--faults", default="")
    browser.add_argument("--ui-version", choices=["v1", "v2"], default="v1")
    browser.add_argument("--root", type=Path, default=ROOT)

    evaluate = subparsers.add_parser("eval", help="Evaluate the workflow with deterministic golden tasks")
    evaluate.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "evals")
    evaluate.add_argument("--trials", type=int, default=3)
    evaluate.add_argument("--root", type=Path, default=ROOT)

    args = parser.parse_args()
    if args.command == "run":
        result = Orchestrator(args.root.resolve(), args.root.resolve() / "artifacts" / "runs" / args.run_id, args.provider, args.resume).run()
        print(json.dumps(result["report"]["summary"], ensure_ascii=False, indent=2))
        print(f"HTML report: {result['report']['html']}")
    elif args.command == "validate-spec":
        issues = validate_spec(load_json(args.spec), load_json(args.policy))
        print(json.dumps({"passed": not issues, "issues": issues}, ensure_ascii=False, indent=2))
        sys.exit(1 if issues else 0)
    elif args.command == "triage":
        print(json.dumps(triage_run(args.run_dir), ensure_ascii=False, indent=2))
    elif args.command == "heal":
        print(json.dumps(propose_healing(args.source, args.output_dir, args.old, args.new, args.mode), ensure_ascii=False, indent=2))
    elif args.command == "report":
        print(json.dumps(generate_report(args.run_dir), ensure_ascii=False, indent=2))
    elif args.command == "trace":
        hub = QualityHub(args.run_dir / "quality-hub.db")
        try:
            print(json.dumps(hub.trace_requirement(args.requirement), ensure_ascii=False, indent=2))
        finally:
            hub.close()
    elif args.command == "eval":
        from .workflow_eval import run_workflow_evals
        result = run_workflow_evals(args.root.resolve(), args.output_dir.resolve(), args.trials)
        print(json.dumps({key: value for key, value in result.items() if key != "results"}, ensure_ascii=False, indent=2))
        sys.exit(0 if result["passed"] else 1)
    elif args.command == "browser":
        result = run_pytest(args.root.resolve(), args.test_path.resolve(), args.run_dir.resolve(), "browser", set(filter(None, args.faults.split(","))), args.ui_version)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
