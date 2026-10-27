# 架构与实现映射

## 当前主链路：真实测试 Agent

`agent_workflow.py` 是通用 Web 项目主入口，不依赖内置退款规格或预制测试答案。

- **工具层**：Kimi Code CLI + 官方 Playwright CLI + 工作区 Skill。选择 CLI 是因为当前 Kimi 0.43 会在未信任工作区禁用项目级 MCP；CLI 同样提供页面快照、操作、网络、Console、截图和 Trace，且更适合编码 Agent。
- **规划层**：Planner 必须留下真实页面和操作记录；独立 Challenger 使用另一模型会话反驳计划，输出风险挑战与 `coverage.json`。
- **交付层**：Generator 在隔离工作区生成 TypeScript Playwright 候选，自行执行并记录首次结果。
- **验证层**：QualityOS 不采信 Agent 自述，独立运行 `npx playwright test`，解析 JUnit；首次失败进入 Healer，最终再次独立执行。
- **故障证明**：`--fault-url` 将同一候选指向显式故障环境，只有真实测试失败才算抓到；未配置时标记 `not_configured`。
- **项目记忆**：`project_memory.py` 保存项目画像、计划、风险矩阵、候选和运行历史；`regress` 直接独立执行，不重复消耗生成 token。
- **治理边界**：无测试、无断言、Skip、无 JUnit、计划被 Healer 修改、故障逃逸均不得通过。候选最终仍是 `pending_human_approval`。

`auto` 输出位于 `artifacts/agent-runs/<run-id>/`，长期项目记忆位于 `artifacts/projects/<project-key>/`。原始 Agent 日志和独立执行证据分开保存，避免把模型总结当成测试执行。

## Legacy：内置退款演示的三条闭环

### 测试交付闭环

`requirements.json` 提供已批准业务预期。编排器先执行来源、Oracle、验收条件和高风险未决项校验，再生成测试计划与候选脚本。质量图谱把需求、风险、Oracle、用例、测试和运行关联起来。

### 可信执行闭环

`runner.py` 每次启动隔离应用和数据库，保存服务命令、pytest 命令、JUnit、标准输出、应用日志、故障开关、UI 版本和耗时。`proof.py` 分别运行 Good Build 与每种 Fault Build，防止“只执行、不验证”的弱测试。

### 自我进化闭环

`evals/workflow/tasks.json` 是工作流自身的回归资产。规格、Prompt、Skill、provider 或修复策略变化后，必须重新运行。线上生产回流不在本演示中伪造；实际接入点是把复核后的缺陷转成新规格、用例或黄金任务。

## 上下文工程

`context.py` 对每个输入记录路径、SHA-256 和可信级别。不可信材料先做注入模式检查，命中后只保留安全证据，不进入模型文档。每个 provider 阶段只接收该阶段需要的结构化上下文。

这是一套可运行的最小实现，不声称能识别所有提示词注入。生产环境还需要沙箱、网络 egress、工具权限和人工审批共同防御。

## Provider 边界

统一返回：provider、阶段、结构化输出、原始输出、耗时、是否真实 AI、命令和模型标识。

- `FixtureProvider`：读取可重复产物，`is_ai=false`，只有显式选择 `--provider fixture` 才使用。
- `CLIProvider("kimi")`：结构化任务提供方，调用当前 CLI 兼容的 `kimi -p`，按规划、生成、审查、项目接入和失败仲裁提供中文契约并解析 JSON；不与 `-p` 混用 `--plan`/`--auto`。
- `CLIProvider("claude")`：调用非交互 Claude，使用 JSON Schema、plan 权限和空工具集。

规划、测试生成、独立审查和 `onboard` 项目接入需要语义判断，使用真实 LLM；规格门禁、注入扫描、AST 检查、执行与统计使用确定性代码，不为了“用 AI”而替代确定性验证。审查上下文包含候选源码，而不是只给模型一个不可读的路径。模型输出不是门禁，即使模型返回 `pass`，确定性规格检查、AST 检查和真实执行仍必须独立通过。

`onboard` 可以读取任意项目的 PRD/接口文档，生成未批准候选规格和用例；它强制清空 `approved_by`，保留高风险未决项并标记测试未执行。完整 `run` 的应用启动和故障注入仍绑定内置退款演示，不声称支持任意项目一键闭环。

## 长任务状态

`progress.json` 保存阶段、状态、更新时间和产物路径，`feature_list.json` 保存每条用例的初始未通过状态与故障证明后的状态。失败阶段标为 blocked，报告不会因异常而消失。`run --resume` 复用已通过阶段的证据，只重跑未完成阶段；质量图谱和运行证据保存在磁盘，不依赖聊天上下文。

## 受控修复

`healing.py` 对原始与候选 Python AST 做规范化，只把受支持 locator 方法的参数替换为占位符。规范化后仍有任何差异，即说明变更超出 locator-only 范围，直接阻断。

合法候选也仅写入独立目录，状态为 `pending_human_review`。项目刻意不提供自动合并 API。

## 报告与职责

- AI：生成候选、查漏、分类和解释。
- 确定性代码：Schema、追溯、AST、执行、故障证明和统计。
- 人：业务规则、歧义、预期变化、高风险决策和最终批准。
- WorkBuddy：协作文档与报告展示，不替代 CI。
