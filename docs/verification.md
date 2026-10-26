# 本地验收记录

## 已实际执行

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 全部标准测试 | 26 passed | pytest 输出；包含单元、API、集成、完整工作流、断点续跑和真实浏览器 |
| 完整离线闭环 | Good Build 通过，4/4 注入故障被抓到 | `artifacts/runs/demo/proof/proof.json` |
| 断点续跑 | 已完成阶段产物复用，fault proof 不重复执行 | `tests/test_orchestrator.py` 与 `artifacts/runs/demo/progress.json` |
| Workflow Evals | 6 个黄金任务，每个重复 3 次，全部 pass^k；假绿信号 0 | `artifacts/evals/workflow-evals.json` |
| 真实浏览器 | Playwright 主链路通过，截图和 Trace 已检查 | `artifacts/browser/refund-success.png`、`playwright-trace.zip` |
| UI 漂移 | 旧 locator 在 v2 上真实超时失败，分类为 locator_drift | `artifacts/healing/original/` |
| 合法修复候选 | 仅 locator 改变；候选在 v2 上通过；仍待人工审批 | `artifacts/healing/proposal/`、`artifacts/healing/targeted/` |
| 非法修复 | 断言、Skip、删除等变化被测试阻断 | `tests/test_healing.py` |
| 模糊资金需求 | 未批准 Oracle、未决高风险等四项问题被阻断 | `specs/ambiguous-requirements.json` 与 validate-spec 输出 |
| 质量图谱追溯 | REQ-REFUND-001 可追溯至两条用例及对应测试 | `artifacts/runs/demo/quality-hub.db` |

## 浏览器环境

Playwright 官方 Chromium 下载在本机多次遇到 `ECONNRESET`。项目随后使用 Playwright 官方支持的系统 `msedge` 通道完成真实浏览器验收，没有跳过 E2E，也没有以静态图片代替执行证据。标准测试仍优先尝试 Playwright Chromium，Windows 上不可用时使用 Edge。

## 在线模型边界

- Kimi CLI 与 Claude CLI 可执行文件及非交互参数已检查。
- provider 子进程契约由单元测试 mock 验证。
- 本次未发起真实 Kimi／Claude 模型调用，未验证在线输出质量、账号配置、模型费用或在线端到端完成率。
- 因此，当前可以声称“在线适配器已实现”，不能声称“在线模型闭环已验收”。
- 离线完整闭环使用 `fixture`，报告明确记录 `ai_generation_used=false`。

## 未覆盖

生产部署、真实公司数据、完整变异测试、任意代码自愈、真实线上回流、组织级提效和人工正式批准均不在本次验收范围内。
