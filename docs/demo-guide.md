# 演示脚本

以下命令使用 Windows Git Bash 路径。

## 主入口：真实 AI 自动化测试

先启动退款测试应用：

```bash
.venv/Scripts/python -m demo_app.server --port 8765
```

另开终端执行：

```bash
.venv/Scripts/python -m quality_os.cli auto \
  --url http://127.0.0.1:8765 \
  --document specs/refund-prd.md \
  --project-key refund --run-id agent-demo
```

这不是 fixture：Kimi 必须用 Playwright CLI 实际探索，独立 Challenger 补风险，Generator 写并执行测试，QualityOS 最后独立重跑。打开 `artifacts/agent-runs/agent-demo/report.html`，再检查 `workspace/evidence/` 和 `execution/`。

项目记忆回归：

```bash
.venv/Scripts/python -m quality_os.cli regress --project-key refund --run-id agent-regression
```

## Legacy 1. 规格不是形式，而是门禁

```bash
.venv/Scripts/python -m quality_os.cli validate-spec --spec specs/requirements.json
.venv/Scripts/python -m quality_os.cli validate-spec --spec specs/ambiguous-requirements.json
```

第一条通过；第二条因资金歧义、模型推测 Oracle、缺验收和缺批准而失败。

讲解：AI 可以指出“大额退款需审批”不清楚，但不能自行定义“大额”和审批规则。

## 2. 完整交付与故障证明

默认使用真实 Kimi（消耗 token）：

```bash
.venv/Scripts/python -m quality_os.cli run --run-id kimi-demo
```

只做可重复离线演示时：

```bash
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id demo
```

打开 `artifacts/runs/demo/report.html`，再查看：

- `execution/run.json`：Good Build 结果。
- `proof/proof.json`：四类故障是否被抓到。
- `proof/<fault>/junit.xml`：每类失败的原始证据。
- `provider-evidence.json`：fixture 与真实 AI 的区别。
- `quality-hub.db`：质量图谱。

讲解：通过率只说明正确版本能跑通；故障版本失败才证明测试能抓 Bug。

## 3. 越权故障

```bash
.venv/Scripts/python -m quality_os.cli run --run-id security-demo
```

打开 `proof/idor/pytest.stdout.log`。可以看到越权用例在故障版本上失败，而 Good Build 正常通过。

讲解：这里测的是最终权限和数据库状态，不是只看页面提示。

## 4. UI 漂移与受控修复

先在 v2 UI 上运行旧定位器，预期失败：

```bash
.venv/Scripts/python -m quality_os.cli browser \
  --test-path tests/candidates/test_refund_ui_candidate.py \
  --ui-version v2 --run-dir artifacts/healing/original
```

保存第一次失败后，生成候选：

```bash
.venv/Scripts/python -m quality_os.cli heal \
  --source tests/candidates/test_refund_ui_candidate.py \
  --output-dir artifacts/healing/proposal \
  --old refund-submit --new confirm-refund --mode propose
```

查看 `candidate.diff`：只有 test id 改变，断言仍要求“退款成功”。运行候选：

```bash
.venv/Scripts/python -m quality_os.cli browser \
  --test-path artifacts/healing/proposal/test_refund_ui_candidate.py \
  --ui-version v2 --run-dir artifacts/healing/targeted
```

合法候选通过执行后仍需人工审批，不会自动合并。

## 5. 阻断非法自愈

尝试把预期从“退款成功”改为“退款被拒绝”，或直接 Skip，可用 `inspect_candidate` 做单元级演示：

```bash
.venv/Scripts/python -m pytest tests/test_healing.py -q
```

讲解：如果 AI 能修改 Oracle，任何系统都能被做成绿色，所以意图必须不可变。

## 6. 评测工作流自己

```bash
.venv/Scripts/python -m quality_os.cli eval --trials 3
```

展示提示词注入、模糊资金规则、合法 locator 和非法断言变更黄金任务。`pass^k= true` 表示三次都符合预期，不是挑一次成功。
