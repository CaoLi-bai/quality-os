import json
from pathlib import Path

from quality_os.orchestrator import Orchestrator
from quality_os.providers.fixture import FixtureProvider

ROOT = Path(__file__).parents[1]


def test_complete_offline_workflow_has_real_proof_and_pending_human_gate(tmp_path, monkeypatch):
    observed = {}

    class RecordingProvider(FixtureProvider):
        def generate(self, stage, context, schema):
            if stage == "review":
                observed.update(context)
            return super().generate(stage, context, schema)

    monkeypatch.setattr("quality_os.orchestrator.create_provider", lambda name, root: RecordingProvider(root))
    result = Orchestrator(ROOT, tmp_path / "run", "fixture").run()
    assert "def test_over_refund_is_rejected_without_state_change" in observed["candidates"][0]["content"]
    summary = result["report"]["summary"]
    assert summary["provider"] == "fixture"
    assert summary["ai_generation_used"] is False
    assert summary["baseline"] == "passed"
    assert summary["faults_caught"] == "4/4"
    assert summary["workflow_status"] == "pending_human_approval"
    assert (tmp_path / "run" / "report.html").exists()
    assert (tmp_path / "run" / "quality-hub.db").exists()
    features = json.loads((tmp_path / "run" / "feature_list.json").read_text(encoding="utf-8"))
    assert len(features) == 5
    assert all(item["passes"] for item in features)


def test_resume_reuses_verified_artifacts_without_rerunning_fault_proof(tmp_path, monkeypatch):
    Orchestrator(ROOT, tmp_path / "run", "fixture").run()
    evidence_before = (tmp_path / "run" / "provider-evidence.json").read_text(encoding="utf-8")
    monkeypatch.setattr("quality_os.orchestrator.prove_test_value", lambda *args: (_ for _ in ()).throw(AssertionError("proof reran")))
    result = Orchestrator(ROOT, tmp_path / "run", "fixture", resume=True).run()
    assert result["report"]["summary"]["faults_caught"] == "4/4"
    assert (tmp_path / "run" / "provider-evidence.json").read_text(encoding="utf-8") == evidence_before
