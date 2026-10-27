# 本地与真实项目验收记录

## QualityOS 工程验证

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 全部标准测试 | **44 passed**；包含 Agent 工作区、会话复用、记忆路径、失败仲裁、版本契约和真实浏览器 | 本次 pytest 输出 |
| Workflow Evals | 6 个黄金任务，每个重复 3 次，全部 pass^k；假绿信号 0 | `artifacts/evals/workflow-evals.json` |
| Legacy 离线闭环 | Good Build 通过，4/4 注入故障被抓到；`ai_generation_used=false` | `artifacts/runs/demo-final-2/` |
| 项目记忆单元验收 | 候选复用、回归历史、正确根目录、无 JUnit 不通过 | `tests/test_project_memory.py`、`tests/test_agent_workflow.py` |
| 失败仲裁 | 分批强制逐条完整，漏一条即阻断 | `tests/test_adjudication.py` |

离线 mock 只证明工程逻辑，不证明模型效果或提效。

## 真实 Agent 链路

使用本机真实 Kimi 与官方 Playwright CLI + Skill，无 fixture 回退。

- Planner 对退款演示实际完成正常退款、同键重试、超额 400、取消单 409、跨用户 403，保存页面与请求证据：`artifacts/agent-runs/agent-smoke-4/workspace/`。
- 智能客服 Planner、独立 Challenger、Planner Revision、Generator 均产生真实模型记录。
- Generator 交付 8 个 Playwright 文件、15 条候选。最后自检阶段超过外层 30 分钟，系统未把它写成通过；随后通过 `verify` 复用候选独立验收。
- 独立结果：**11 通过、4 失败、0 跳过**。证据：`artifacts/agent-runs/customer-discovery-2/execution/independent/`。
- 项目记忆回归复用同一候选，未调用生成模型，结果仍为 **11 通过、4 失败且失败项一致**；`ai_generation_used=false`。证据：`artifacts/agent-runs/customer-regression-1/`。
- 中文报告：`artifacts/agent-runs/customer-discovery-2/report.html`。

本机 Kimi 0.43 的真实兼容处理：`-p` 不与 `--auto`/`--plan` 混用；会话通过 `kimi session list --cwd ... --json` 恢复；未信任工作区的项目 MCP 禁用，因此无人值守主链路采用官方 CLI + Skill。

## 智能客服真实项目

环境：真实启动 PostgreSQL、Redis、Langfuse、LangGraph 80 端口和 Vite 5173 前端。未修改业务代码。

### 构建与手工链路

- UI `pnpm build` 成功，Python `compileall` 成功。
- UI `pnpm lint`：0 error、6 warning，属于工程债，不冒充业务缺陷。
- 页面实际发送“K87 键盘多少钱？”，经过路由和 `search_product`，返回 ¥299 与检索来源。

### 38 条既有功能/RAG 评测

- 新 Langfuse 栈先同步 38 条数据集，再执行 `qualityos-baseline-v2`。
- 机械轮次通过率：31/43（72%）；LLM 相关性/准确性均 4.7。
- context_recall 0.94、context_precision 1.00（各 16 条）。
- 机械库外拒答红线 5/5 未命中，但不能等同“100% 已证明编造”。
- 独立 Kimi 高速模型结合答复、工具、检索和数据库证据逐条仲裁：4 条候选真实产品问题，7 条测试 Oracle/数据问题。完整证据：`artifacts/evals/customer-service/baseline-report.md`、`adjudicated-v2/adjudication.json`。

### 独立 Agent 新发现

- **确认产品缺陷**：`ZXQ-9000` 被拆为 `ZXQ - 9000`，ParadeDB 查询报错并向上传播，最终无答复。见 `artifacts/evals/customer-service/zxq-error.json` 和 Langfuse Trace `a413cd1b0295c185116d7d69be1e93da`。
- **需求冲突**：README 写后续直达专家，当前 `graph.py` 明确每轮重新路由；须先决定唯一预期，不能直接判产品或测试谁对谁错。
- **网络韧性证据**：合成 `runs/stream` HTTP 500 后，一次提交出现 5 次请求且页面无错误提示；仅证明重试与提示风险，尚未证明重复工单/退款。
- **订单数据漂移**：README 的 `DD100x`、旧评测的 `1/2/3` 与当前数据库整数订单不一致，已归为测试资产问题。

## 尚未完成/不能声称

- WorkBuddy + skill + Playwright 同项目对照尚未实际执行；协议已备于 `docs/workbuddy-benchmark.md`，**不能宣称打赢**。
- 网络失败下的重复写数据库证明尚未完成；需要带幂等键的工单写路径实验。
- 候选测试仍未获命名人工批准，不能自动晋级正式资产。
- 模型费用未完整统计，不填提效比例、ROI 或业务收益。
- 生产环境、真实客户数据、任意协议和完整变异测试不在本次范围。
