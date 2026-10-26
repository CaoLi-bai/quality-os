from pathlib import Path

from quality_os.workflow_eval import run_workflow_evals

ROOT = Path(__file__).parents[1]


def test_workflow_evals_are_stable_and_have_no_false_green(tmp_path):
    report = run_workflow_evals(ROOT, tmp_path, trials=3)
    assert report["passed"] is True
    assert report["false_green_count"] == 0
    assert all(item["pass_caret_k"] for item in report["results"])
    assert report["model_grader"]["status"] == "not_run"
