# 架构与实现映射

## 三条闭环

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

- `FixtureProvider`：读取可重复产物，`is_ai=false`。
- `CLIProvider("kimi")`：调用 `kimi --plan -p`，解析 JSON。
- `CLIProvider("claude")`：调用非交互 Claude，使用 JSON Schema、plan 权限和空工具集。

模型输出不是门禁。即使模型返回 `pass`，确定性规格检查、AST 检查和真实执行仍必须独立通过。

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
