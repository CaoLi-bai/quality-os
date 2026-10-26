from __future__ import annotations

from pathlib import Path

from .models import dump_json
from .runner import run_pytest

FAULT_TESTS = {
    "over_refund": "test_over_refund_is_rejected_without_state_change",
    "duplicate_refund": "test_idempotent_retry_creates_one_refund",
    "idor": "test_other_user_cannot_read_or_refund_order",
    "status_check": "test_cancelled_order_cannot_be_refunded",
}


def prove_test_value(root: Path, test_path: Path, output_dir: Path) -> dict:
    baseline = run_pytest(root, test_path, output_dir / "baseline", "proof-baseline")
    proofs = []
    for fault, test_name in FAULT_TESTS.items():
        result = run_pytest(
            root, test_path, output_dir / fault, f"proof-{fault}", {fault}
        )
        proofs.append({
            "fault": fault,
            "test": test_name,
            "caught": result.exit_code != 0,
            "run_id": result.run_id,
            "evidence_dir": result.evidence_dir,
        })
    report = {
        "status": "passed" if baseline.exit_code == 0 and all(item["caught"] for item in proofs) else "failed",
        "good_build": {"passed": baseline.exit_code == 0, "run_id": baseline.run_id},
        "faults": proofs,
        "rule": "Candidate must pass on the good build and catch every mapped injected fault.",
    }
    dump_json(output_dir / "proof.json", report)
    return report
