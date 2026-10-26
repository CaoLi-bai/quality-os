---
name: test-asset-review
description: 独立审查 AI 生成的测试资产，验证断言有依据、Good Build 通过且注入故障可被抓到；当用户要求测试准入、候选评审或反假绿验证时使用。
---

# Test Asset Review

## 审查顺序

1. 对照已批准规格，不接受从当前产品行为反推预期。
2. 检查每个测试有有效断言，禁止空断言、自我比较和无原因 Skip。
3. 执行 Good Build，保存命令、JUnit、日志、截图或 Trace。
4. 执行故障证明，要求对应故障版本失败。
5. 输出候选 Diff 和剩余风险，状态保持 `pending_human_approval`。

```bash
python -m quality_os.cli run --provider fixture --run-id review-demo
```

离线 fixture 只用于可重复工程演示，报告必须保留 `ai_generation_used=false`，不得声称使用了真实模型。
