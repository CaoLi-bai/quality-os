# QualityOS

**规格驱动、证据闭环、受控自治的 AI Native 测试工作流。**

这不是“让 AI 写一百条用例”的演示，而是一套可运行的质量系统：需求先变成带来源的规格，候选测试经过独立审查，在正确版本上通过，还必须抓到注入故障；失败可以归因，UI 修复只能提交候选，任何阶段都不能靠改断言、删测试或 Skip 获得假绿。

## 已实现

- 真实订单退款 Web／API 应用：SQLite 状态、金额边界、幂等、权限和订单状态。
- 四类可控故障：超额退款、重复退款、越权、非法状态。
- 质量图谱：`REQ → RISK → ORACLE → CASE → TEST → RUN`。
- 分阶段编排：规格、计划、生成、独立审查、执行、故障证明、报告。
- 三种 provider：明确标注的离线 fixture、Kimi CLI、Claude CLI。
- Good Build／Fault Build 双向证明，而不是只看通过率。
- 第一次失败保存、分类与自动修复资格判断。
- locator-only Healer：AST 规范化 Diff 检查，默认 observe，禁止自动合并。
- Playwright 真实浏览器、截图和 Trace。
- 工作流自身黄金评测：模糊需求、提示词注入、非法自愈和 pass^k。
- HTML／Markdown 证据报告、CI、六个 Agent Skills、WorkBuddy 文档接口。

## 架构

```text
PRD / 不可信外部材料
        │ 来源、脱敏、注入检查
        ▼
  已批准规格 ─────── 高风险歧义：停止
        │
        ▼
  风险计划 → 候选测试 → 独立审查
                          │
                          ▼
                  Good Build 必须通过
                          │
                          ▼
                  Fault Build 必须失败
                          │
                          ▼
              证据报告 + 人工审批（待处理）
```

质量中枢保存在 `quality-hub.db`、`progress.json` 和每次运行的证据目录中。AI 可以生成和审查，确定性代码掌握门禁，人掌握业务预期与高风险批准。

## 快速启动

需要 Python 3.12+。以下命令适用于 Windows Git Bash；Linux/macOS 使用 `.venv/bin/python`。

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m playwright install chromium
```

如果 Chromium 下载受网络限制，而 Windows 已安装 Edge，测试会使用 Playwright 官方 `msedge` 通道；也可通过 `QUALITY_OS_BROWSER_CHANNEL=msedge` 显式指定。不会因此跳过浏览器测试。

### 1. 运行完整离线闭环

```bash
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id demo
```

打开 `artifacts/runs/demo/report.html`。预期结果：基线通过、4/4 故障被抓到、`ai_generation_used=false`、`pending_human_approval`。

从中断点继续，复用已通过阶段的产物：

```bash
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id demo --resume
```

离线 fixture 是可重复的工程执行器，**不是大模型调用**。

### 2. 启动真实演示应用

```bash
.venv/Scripts/python -m demo_app.server --port 8765
```

浏览器访问 `http://127.0.0.1:8765`。测试用户为 `user-1`，订单 `order-1001` 实付 10000 分。

### 3. 运行真实浏览器测试

```bash
.venv/Scripts/python -m quality_os.cli browser --run-dir artifacts/browser
```

证据：`refund-success.png`、`playwright-trace.zip`、JUnit 和运行元数据。

### 4. 运行工作流自身评测

```bash
.venv/Scripts/python -m quality_os.cli eval --trials 3 --output-dir artifacts/evals
```

报告位于 `artifacts/evals/workflow-evals.json` 和 `.md`。

### 5. 运行全部测试

```bash
.venv/Scripts/python -m pytest
```

## 典型门禁命令

模糊资金需求应被阻断：

```bash
.venv/Scripts/python -m quality_os.cli validate-spec --spec specs/ambiguous-requirements.json
```

追溯需求到测试：

```bash
.venv/Scripts/python -m quality_os.cli trace \
  --run-dir artifacts/runs/demo --requirement REQ-REFUND-001
```

生成 locator-only 修复候选：

```bash
.venv/Scripts/python -m quality_os.cli heal \
  --source tests/candidates/test_refund_ui_candidate.py \
  --output-dir artifacts/healing/proposal \
  --old refund-submit --new confirm-refund --mode propose
```

命令不会修改源文件，也不会自动合并候选。完整攻击演示见 `docs/demo-guide.md`。

## Kimi Code／Claude Code

项目根目录的 `skills/` 包含六个可复用技能。

Kimi CLI 示例：

```bash
kimi --skills-dir ./skills --plan -p "使用 requirement-to-spec 审查 specs/refund-prd.md，列出高风险未决项，不修改文件。"
```

Claude CLI 示例：

```bash
claude -p "使用 controlled-healing 的原则审查 tests/candidates，不修改文件。" --permission-mode plan
```

在线 provider：

```bash
.venv/Scripts/python -m quality_os.cli run --provider kimi --run-id kimi-demo
.venv/Scripts/python -m quality_os.cli run --provider claude --run-id claude-demo
```

在线模式需要本机已有可用账号和模型配置，可能产生费用。它会调用真实 CLI，输出必须满足阶段 JSON 契约；失败会保留错误并阻断，不回退成 fixture 冒充成功。**在线适配器的验收状态以 `docs/verification.md` 为准。**

## 目录

```text
demo_app/                 真实退款应用与可控故障
quality_os/               编排、质量图谱、provider、门禁、证据与报告
specs/                    已批准规格、模糊规格、不可信材料
policies/                 确定性门禁与自愈策略
fixtures/                 明确标注的离线生成物
skills/                   六个测试 Agent Skills
tests/approved/           已登记 API 回归
tests/candidates/         用于受控修复演示的候选
tests/e2e/                真实浏览器测试
evals/workflow/           工作流黄金任务
integrations/workbuddy/   文档与定时交付接口
artifacts/                本地生成的证据，不进入版本控制
docs/                     架构、演示、研究和面试材料
```

## 真实边界

- 这是个人实践／作品集工程，不是生产质量平台，也不是公司项目经历。
- 故障注入只覆盖已登记风险，不等于完整变异测试或全部业务覆盖。
- 离线 fixture 证明工程闭环可运行，不证明任何模型效果或提效比例。
- 模型评分器离线不运行；主观 Rubric 仍需人工校准。
- Healer 当前仅支持 Python Playwright 定位器参数，不支持任意代码自愈。
- 没有自动审批或自动合并命令；这是刻意保留的安全边界。
