---
name: failure-triage
description: 根据第一次未修改失败、JUnit、Trace 和环境信息分类测试失败；当用户要求失败归因、缺陷草稿或自动修复资格判断时使用。
---

# Failure Triage

先保留第一次失败，禁止通过反复重试覆盖现场。分类仅限：产品／需求、脚本、数据、环境、稳定性、定位漂移、需求变化、未知。

```bash
python -m quality_os.cli triage --run-dir <包含 run.json 和 junit.xml 的目录>
```

只有证据明确的 `locator_drift` 可以进入受限修复候选。产品、需求、断言、高风险和 Unknown 一律停止自动修复。

缺陷草稿必须包含需求来源、预期、实际、最小复现、环境和证据路径；分类置信度不能替代证据。
