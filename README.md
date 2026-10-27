# QualityOS

**当前版本：v0.2.1（真实项目实战预览）** · [项目展示页](docs/index.html) · [变更日志](CHANGELOG.md) · [验收记录](docs/verification.md) · [发布元数据](docs/release-metadata.md)

**会实际操作应用的 AI 自动化测试工作流，不是 fixture 生成器。**

真实 Kimi Agent 使用官方 Playwright CLI + Skill 探索目标应用，独立 Agent 反驳测试计划，生成并执行 Playwright 测试；QualityOS 再独立重跑、保存证据、验证故障检出，并沉淀项目质量记忆。Agent 自己说“成功”不算通过。

## 和普通 Chat Agent 有什么区别

- **真实探索**：浏览器页面、点击/输入、网络、Console、截图，不是只读文档写几段代码。
- **独立风险挑战**：另一个模型会话专挑资金、权限、幂等、状态和异常路径遗漏。
- **独立执行**：最终结论来自 QualityOS 启动的 Playwright 和 JUnit，不来自 Agent 自述。
- **故障检出证明**：可传入故障环境，候选测试必须在故障版本暴露问题；正确版本全绿不代表会抓 Bug。
- **项目质量记忆**：保存计划、风险覆盖、候选测试和运行历史，`regress` 一键复跑并比较状态。
- **受控自治**：禁止 Skip、空测试、修改产品、从当前行为反推 Oracle；候选仍需人工批准。

## 环境准备

需要 Python 3.12+、Node.js 20+、可用的 Kimi Code CLI，以及 Edge/Chrome。所有 `auto` 阶段都会真实调用模型并消耗 token。

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
kimi login
node --version
```

Linux/macOS 将 Python 路径换成 `.venv/bin/python`。首次运行会在独立工作区安装固定版本的 `@playwright/test` 和 `@playwright/cli`，不修改被测项目依赖。

## 测自己的项目

先启动**隔离测试环境**，准备 PRD、接口文档、权限规则和测试数据说明，然后：

```bash
.venv/Scripts/python -m quality_os.cli auto \
  --url http://127.0.0.1:8765 \
  --document /你的项目/docs/PRD.md \
  --document /你的项目/docs/api.md \
  --project-key my-project \
  --run-id discover-001
```

可选 `--project-dir /你的项目` 给 Agent 源码上下文。该目录只应作为只读输入；提示明确禁止修改产品，但生产环境、真实客户数据和生产密钥不在允许范围内。

### 工作流实际做什么

```text
读取需求并记录哈希
  → Planner 用 Playwright 探索应用
  → 独立 Challenger 找风险遗漏并生成覆盖矩阵
  → Planner 合并有依据的补充
  → Generator 验证定位器、生成并执行候选测试
  → QualityOS 独立执行，保存首次失败
  → 必要时 Healer 按证据修复测试实现
  → QualityOS 最终重跑
  → 可选故障环境检出证明
  → 中文报告 + 项目记忆 + 人工审批
```

### 看结果

```text
artifacts/agent-runs/discover-001/
├── report.html / report.json       中文结论与机器可读证据
├── agent/                          每阶段提示、原始输出、命令、耗时、会话
├── execution/                      独立执行、JUnit、截图、视频、Trace
└── workspace/
    ├── specs/test-plan.md           测试计划
    ├── specs/risk-challenge.md      独立风险挑战
    ├── specs/coverage.json          需求—风险—场景矩阵
    ├── evidence/exploration.json    真实页面与操作记录
    └── tests/candidates/            未批准的 Playwright 候选测试
```

只有 `pending_human_approval` 表示技术证据已准备好，仍需命名审核人批准；`tests_failed`、`fault_proof_failed` 和 `blocked` 都不能当成功。

Agent 阶段超时但已留下候选时，不必重新消耗生成 token，直接独立验收：

```bash
.venv/Scripts/python -m quality_os.cli verify --run-dir artifacts/agent-runs/discover-001
# 需要 Agent 按失败证据修复时：
.venv/Scripts/python -m quality_os.cli verify --run-dir artifacts/agent-runs/discover-001 --heal
```

## 项目记忆与回归

每次 `auto` 将项目画像、最新候选和运行历史保存到 `artifacts/projects/<project-key>/`。之后不必重新生成：

```bash
.venv/Scripts/python -m quality_os.cli regress \
  --project-key my-project --run-id regression-002
```

回归由确定性执行器完成，不浪费模型调用；`ai_generation_used=false`。候选不会因为重复通过就自动变成正式批准资产。

## 故障检出证明

如果你有可控故障环境，把它作为第二个 URL 传入：

```bash
.venv/Scripts/python -m quality_os.cli auto \
  --url http://127.0.0.1:8765 \
  --fault-url over-refund=http://127.0.0.1:8766 \
  --document /你的项目/PRD.md \
  --project-key my-project --run-id with-fault-proof
```

同一候选在正确环境必须通过，在故障环境必须产生真实测试失败。没有配置故障环境时，报告明确写 `not_configured`，不会把通过率冒充缺陷检出率。

## 与 WorkBuddy 组合对照

目标不是做一个“也能调 Playwright”的壳，而是验证项目记忆、独立风险挑战、独立验收、故障证明和可重复回归是否带来实际优势。

对照任务、指标和判定规则见 `docs/workbuddy-benchmark.md`。**没有同项目双方证据前，不宣称打赢 WorkBuddy。**

## 旧版内置退款演示

`run` 是 legacy 编排演示，只用于验证规格门禁、SQLite 故障注入和离线工程闭环，不是通用 Agent 主入口：

```bash
# 明确使用离线样本，不调用模型
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id demo

# 真实浏览器演示
.venv/Scripts/python -m demo_app.server --port 8765
.venv/Scripts/python -m quality_os.cli browser --run-dir artifacts/browser

# 工作流确定性黄金评测
.venv/Scripts/python -m quality_os.cli eval --trials 3

# 全部自动化测试
.venv/Scripts/python -m pytest
```

`onboard` 只生成静态规格/用例草案，不操作应用。需要真正自动测试时使用 `auto`。

## 方案依据与真实边界

主流程参考 Playwright 官方 [Test Agents](https://playwright.dev/docs/test-agents) 的 planner → generator → healer；浏览器执行采用官方推荐的 [Playwright CLI + Skills](https://playwright.dev/docs/getting-started-cli)。Kimi 0.43 在未信任工作区禁用项目 MCP，因此当前无人值守主链路不使用 MCP 冒充可用性。

- 当前主攻 Web UI、页面网络及 Playwright API 可观测行为，不宣称任意协议、任意平台或数据库直查。
- Agent 可以生成和修复候选，不能批准业务预期，不能自动合并正式资产。
- 离线单元测试里的 mock 只验证工程逻辑，不等于在线模型效果验收；实际在线结果以 `docs/verification.md` 为准。
- 不编造提效、业务收益、人工审批或 WorkBuddy 对照结论。
