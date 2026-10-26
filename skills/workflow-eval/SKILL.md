---
name: workflow-eval
description: 评测 QualityOS 工作流自身，覆盖规格歧义、提示词注入、故障证明、非法自愈、重复稳定性和人工升级；当用户要求工作流回归、模型或 Prompt 升级验证时使用。
---

# Workflow Eval

Prompt、Skill、provider 或模型变化后，先运行黄金任务，不得只挑几个成功案例演示。

```bash
python -m quality_os.cli eval --trials 3 --output-dir artifacts/evals
```

检查 `workflow-evals.json` 和 Markdown 报告。`pass@k` 表示至少一次成功，`pass^k` 表示每次都成功；稳定性门禁看后者。

代码评分器负责结构、来源、非法变更和门禁。模型 Rubric 负责开放质量判断，但必须与人工抽样校准；离线报告中的 `model_grader=not_run` 不得改写为已评测。
