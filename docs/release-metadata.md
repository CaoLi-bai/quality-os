# v0.2.0 发布元数据

## 版本定位

- 版本：**0.2.0**
- 标签：`v0.2.0`
- 发布名：**QualityOS v0.2.0 — 真实项目实战预览**
- 不是 v1.0 稳定版：真实项目仍有失败，外部工具对照和重复写故障证明未完成。

## GitHub 仓库描述

```text
Evidence-first AI agent testing with real browser exploration, independent challenge, controlled healing, and regression memory.
```

中文简介：

```text
真实 Agent 驱动的 AI 自动化测试工作流：浏览器探索、独立风险挑战、候选生成、独立验收、受控修复与项目记忆回归。
```

## 建议 Topics

```text
ai-testing, agentic-ai, playwright, llm-evaluation, quality-assurance, kimi, pytest, typescript, python, langgraph, langfuse
```

## 版本一致性

- `pyproject.toml`：`0.2.0`
- `quality_os/__init__.py`：`__version__ = "0.2.0"`
- CLI：`quality-os --version` 输出 `quality-os 0.2.0`
- 标签：`v0.2.0`
- 变更记录：`CHANGELOG.md`

## 发布说明

使用 `CHANGELOG.md` 的 0.2.0 章节作为 GitHub Release 正文，包含新增能力、实测数据、兼容修复和已知边界，不填入未经复核的指标。

## 验收命令

```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python -m quality_os.cli eval --trials 3
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id release-check
.venv/Scripts/python -m quality_os.cli --version
```

Linux/macOS 使用 `.venv/bin/python`。真实在线证据见 `docs/verification.md`，智能客服实战报告见 `artifacts/evals/customer-service/baseline-report.md`（本地生成，不进入 Git 历史）。
