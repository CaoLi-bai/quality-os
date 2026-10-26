import json
from pathlib import Path

from quality_os.hub import QualityHub
from quality_os.models import load_json

ROOT = Path(__file__).parents[1]


def test_quality_graph_traces_requirement_to_test(tmp_path):
    hub = QualityHub(tmp_path / "hub.db")
    hub.load(load_json(ROOT / "specs" / "requirements.json"), load_json(ROOT / "specs" / "cases.json"))
    trace = hub.trace_requirement("REQ-REFUND-001")
    assert trace["requirement"]["risk"] == "money"
    assert len(trace["cases"]) == 2
    assert any("test_over_refund" in test for case in trace["cases"] for test in case["tests"])
    hub.close()
