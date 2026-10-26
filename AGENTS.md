# QualityOS 协作规范

## 项目定位

这是一个规格驱动、证据闭环、受控自治的 AI Native 测试工作流演示。所有业务数据均为合成数据，不连接真实资金、客户或生产系统。

## 不可变规则

- `specs/requirements.json` 是演示业务预期的唯一事实源，不得从产品当前行为反推预期。
- 金额、权限、安全和合规需求存在未决项时，必须阻断。
- fixture provider 不是 LLM；报告必须保留 `is_ai=false`。
- Healer 只能修改受支持的定位器参数，不能修改断言、预期数据、Skip、测试数量或产品代码。
- 候选测试只能进入独立候选目录，命名审核人批准前不得合并到 `tests/approved/`。
- 不得编造模型调用、人工审批、业务收益、提效比例或历史项目时间。

## 常用命令

```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python -m quality_os.cli eval --trials 3
.venv/Scripts/python -m quality_os.cli run --provider fixture --run-id demo
.venv/Scripts/python -m quality_os.cli browser --run-dir artifacts/browser
```

Linux/macOS 将 Python 路径替换为 `.venv/bin/python`。

## 修改后验证

- 修改规格、门禁或编排：运行全部 pytest、Workflow Evals 和完整离线 run。
- 修改演示应用：运行 API、故障证明和真实浏览器测试。
- 修改 Healer：必须验证合法 locator 候选与断言／Skip／删除攻击样例。
- 修改文档：核对命令、路径、实现状态和在线适配器验证边界。
