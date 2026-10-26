---
name: controlled-healing
description: 在不改变测试意图的前提下生成定位器修复候选，并阻断断言、预期、Skip、删测试和产品代码变更；当用户要求测试自愈或 UI 漂移修复时使用。
---

# Controlled Healing

默认 `observe`，不修改源文件。`propose` 也只把候选写入独立证据目录，绝不自动合并。

```bash
python -m quality_os.cli heal \
  --source tests/candidates/test_refund_ui_candidate.py \
  --output-dir artifacts/healing \
  --old refund-submit --new confirm-refund --mode propose
```

检查 `healing.json` 和 `candidate.diff`，随后运行目标与关联回归。资金、权限、安全及语义不清场景只取证，不修复。命名审核人批准前，状态只能是 `pending_human_review`。
