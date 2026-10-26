from __future__ import annotations

import ast
import difflib
import json
from pathlib import Path

from .models import dump_json

LOCATOR_METHODS = {"locator", "get_by_test_id", "wait_for_selector"}


class LocatorNormalizer(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        function_name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if function_name in LOCATOR_METHODS:
            node.args = [ast.Constant(value="<LOCATOR>") for _ in node.args]
            node.keywords = []
        return node


def normalized_ast(source: str) -> str:
    tree = ast.parse(source)
    return ast.dump(LocatorNormalizer().visit(tree), include_attributes=False)


def inspect_candidate(original: str, candidate: str) -> dict:
    try:
        changed = normalized_ast(original) != normalized_ast(candidate)
    except SyntaxError as error:
        return {"passed": False, "reason": f"Invalid Python: {error}"}
    if changed:
        return {
            "passed": False,
            "reason": "Change exceeds locator-only scope; assertions, expected data, control flow and skips are immutable.",
        }
    if original == candidate:
        return {"passed": False, "reason": "Candidate contains no change."}
    return {"passed": True, "reason": "Only supported locator arguments changed."}


def propose_healing(source_path: Path, output_dir: Path, old: str, new: str, mode: str = "observe") -> dict:
    original = source_path.read_text(encoding="utf-8")
    if old not in original:
        raise ValueError(f"Locator not found: {old}")
    candidate = original.replace(old, new)
    check = inspect_candidate(original, candidate)
    diff = "\n".join(difflib.unified_diff(
        original.splitlines(), candidate.splitlines(),
        fromfile=str(source_path), tofile=f"{source_path.name} (candidate)", lineterm=""
    )) + "\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "candidate.diff").write_text(diff, encoding="utf-8")
    candidate_path = output_dir / source_path.name
    if mode == "propose" and check["passed"]:
        candidate_path.write_text(candidate, encoding="utf-8")
    report = {
        "mode": mode,
        "status": "pending_human_review" if mode == "propose" and check["passed"] else "observed" if check["passed"] else "blocked",
        "policy_check": check,
        "source": str(source_path),
        "candidate": str(candidate_path) if candidate_path.exists() else None,
        "auto_merge": False,
        "immutable": ["assertions", "expected_data", "skip_status", "test_deletion", "product_code"],
        "required_next_steps": ["targeted_rerun", "regression_rerun", "named_human_approval"],
    }
    dump_json(output_dir / "healing.json", report)
    return report
