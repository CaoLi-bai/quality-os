import json
from pathlib import Path
from types import SimpleNamespace

from quality_os.providers.cli import CLIProvider, extract_json
from quality_os.providers.fixture import FixtureProvider

ROOT = Path(__file__).parents[1]


def test_extract_json_from_plain_and_wrapped_output():
    assert extract_json('{"verdict": "pass"}')["verdict"] == "pass"
    assert extract_json('```json\n{"verdict": "pass"}\n```')["verdict"] == "pass"
    assert extract_json('{"result": "{\\"verdict\\": \\"pass\\"}"}')["verdict"] == "pass"


def test_fixture_is_explicitly_not_ai():
    result = FixtureProvider(ROOT).generate("plan", {}, {})
    assert result.is_ai is False
    assert result.model == "deterministic-fixture-not-an-llm"


def test_claude_adapter_uses_bounded_noninteractive_command(monkeypatch):
    def fake_run(command, **kwargs):
        assert "-p" in command
        assert "--json-schema" in command
        assert "--permission-mode" in command
        prompt = command[command.index("-p") + 1]
        assert "独立测试资产审查员" in prompt
        assert "只返回一个" in prompt
        return SimpleNamespace(returncode=0, stdout='{"verdict":"pass"}', stderr="")
    monkeypatch.setattr("quality_os.providers.cli.subprocess.run", fake_run)
    result = CLIProvider("claude").generate("review", {"documents": []}, {"type": "object"})
    assert result.is_ai is True
    assert result.output["verdict"] == "pass"
    assert all("sk" not in " ".join(result.command).lower() for _ in [0])


def test_kimi_adapter_is_compatible_with_current_noninteractive_cli(monkeypatch):
    def fake_run(command, **kwargs):
        assert "--plan" not in command
        assert "--auto" not in command
        prompt = command[command.index("-p") + 1]
        assert "独立" in prompt
        return SimpleNamespace(returncode=0, stdout='{"cases":[],"summary":{}}', stderr="")

    monkeypatch.setattr("quality_os.providers.cli.subprocess.run", fake_run)
    result = CLIProvider("kimi").generate("adjudicate", {"cases": []}, {"type": "object"})
    assert result.is_ai is True
    assert result.command == ["kimi", "-p", "<bounded-prompt>"]
