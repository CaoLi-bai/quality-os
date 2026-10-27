import sys

from quality_os.cli import build_parser, main


def test_version_matches_release(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["quality-os", "--version"])
    try:
        main()
    except SystemExit as error:
        assert error.code == 0
    assert capsys.readouterr().out.strip() == "quality-os 0.2.0"


def test_run_defaults_to_real_kimi():
    args = build_parser().parse_args(["run"])
    assert args.provider == "kimi"


def test_guide_is_chinese_and_explains_real_project_entry(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["quality-os", "guide"])
    main()
    output = capsys.readouterr().out
    assert "中文使用导航" in output
    assert "真实 Agent 操作你的项目" in output
    assert "auto --url" in output


def test_empty_command_shows_guide_instead_of_english_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["quality-os"])
    main()
    output = capsys.readouterr()
    assert "主入口" in output.out
    assert output.err == ""
