# 调研到实现的映射

本文件区分“来源提出的原则”和“本项目的具体实现”，不把厂商结果当成本项目结果。

| 调研来源 | 吸收的原则 | QualityOS 实现 |
|---|---|---|
| [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) | 给 Agent 可验证条件、出示证据、独立上下文审查、Skills 与确定性 Hooks | 真实 pytest／浏览器执行、独立 review 阶段、六个 Skills、确定性门禁 |
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | 增量进度、持久状态、结束处于可交接状态、端到端验证 | `progress.json`、SQLite 质量图谱、每阶段产物、真实 UI 验证 |
| [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | 代码／模型／人工评分器，Outcome 与 Trace，多次试验，pass@k 与 pass^k | 三层评分边界、数据库最终状态、运行证据、Workflow Evals |
| [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | 技能按需加载，指令、脚本与资源组合 | 根目录六个独立 SKILL.md，分别引用真实 CLI 验证 |
| [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) | 规格是共享事实源，阶段检查点，小步可审查产物 | 已批准规格、G0—G5、候选目录和结构化追溯 |
| [Playwright Test Agents](https://playwright.dev/docs/test-agents) | planner／generator／healer 链路与可审计 specs/tests | 计划、生成、真实 Playwright 执行和受限 Healer；未声称直接调用官方 Agent 定义 |
| [Meta ACH](https://engineering.fb.com/2025/09/30/security/llms-are-the-key-to-mutation-testing-and-better-compliance/) | 变异思想用于证明测试能抓现实风险，而非只看行覆盖 | 资金、幂等、越权和状态四类故障注入证明；范围明确小于完整 ACH |
| [Atlassian Mutation Coverage AI Assistant](https://www.atlassian.com/blog/development/automating-mutation-coverage-with-ai) | 项目感知、生成后重新验证、Dev-in-the-loop | 遵循本项目测试契约、Good／Fault 重跑、人工候选审批 |
| [Self-Healing Test Automation Governance](https://qaskills.sh/blog/self-healing-test-automation-guide) | 测试意图不可变、保留第一次失败、候选 Diff、Unknown 停止 | AST 反漂移、原始 JUnit／Trace、observe/propose、分类停止规则 |
| [Anthropic multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system) | 多 Agent 只在独立可并行且价值足够时使用，关注成本 | 一个编排器加按需 Skills；独立审查而非堆叠 Agent 群聊 |
| [Claude Code auto mode](https://www.anthropic.com/research/claude-code-auto-mode) | 权限分类不能取代高风险人工审查，防范围升级与提示词注入 | 不可信材料隔离、只读在线适配器、无生产权限、人工高风险门禁 |

## 刻意没有照搬的内容

- 没有用多 Agent 数量作为先进性指标。
- 没有让模型自己评分、自己放行。
- 没有把 locator 修复包装成任意代码自愈。
- 没有把厂商报告的提效数字写进本项目。
- 没有为了“全自动”移除人工批准。
