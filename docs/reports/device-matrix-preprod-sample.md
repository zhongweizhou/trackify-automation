# Device Matrix Test Report Example

[English](#english) | [中文](#中文)

This committed example was captured from an actual full-suite matrix run. It
keeps the environment, device identity, operating-system version, case result,
and duration visible to reviewers without requiring access to generated local
artifacts.

## English

### Run Summary

- Environment: `preprod`
- Overall status: **PASSED**
- Started: `2026-07-16 07:17:17 +08:00`
- Completed: `2026-07-16 07:21:35 +08:00`
- Unique scenarios: `7`
- Devices: `2`
- Total device-case executions: `14`
- Command: `.venv/bin/python scripts/run_device_matrix.py --env preprod`

| Platform | Type | Device | OS | UDID | Passed | Failed | Errors | Skipped | Duration | Status |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| Android | Emulator | sdk_gphone16k_arm64 | 17 | `emulator-5554` | 7 | 0 | 0 | 0 | 256.5s | PASSED |
| iOS | Simulator | iPhone 17 | 26.5 | `BFE1DE67-0F95-47B7-A02A-D25EE83CD999` | 7 | 0 | 0 | 0 | 256.5s | PASSED |

### Android 17 - sdk_gphone16k_arm64

| Test case | Result | Duration |
|---|---|---:|
| Add expense happy path | PASSED | 40.067s |
| Add income happy path | PASSED | 29.711s |
| Add transfer happy path | PASSED | 29.678s |
| Empty amount validation does not save | PASSED | 23.794s |
| Add expense with a custom category | PASSED | 50.949s |
| Filter transactions by type | PASSED | 40.911s |
| Group transactions by date | PASSED | 40.971s |

### iOS 26.5 - iPhone 17

| Test case | Result | Duration |
|---|---|---:|
| Add expense happy path | PASSED | 35.794s |
| Add income happy path | PASSED | 29.830s |
| Add transfer happy path | PASSED | 29.077s |
| Empty amount validation does not save | PASSED | 22.022s |
| Add expense with a custom category | PASSED | 52.606s |
| Filter transactions by type | PASSED | 40.791s |
| Group transactions by date | PASSED | 38.992s |

### Generated Artifacts

Every new matrix run creates the following local artifacts under
`report/device-matrix/<environment>/<timestamp>/`:

```text
summary.md                  human-readable environment/device/case summary
summary.json                machine-readable result
allure-report/index.html    merged interactive report
allure-results/             merged raw Allure results
<device>/pytest.log         per-device execution log
<device>/junit.xml          per-device JUnit result
<device>/screenshots/       failure evidence
```

Generated artifacts are intentionally ignored by Git. This sanitized Markdown
snapshot is committed as stable reviewer evidence.

## 中文

### 执行摘要

- 测试环境：`preprod`
- 总体结果：**通过**
- 开始时间：`2026-07-16 07:17:17 +08:00`
- 完成时间：`2026-07-16 07:21:35 +08:00`
- 唯一测试场景：`7`
- 设备数量：`2`
- 设备维度用例执行次数：`14`
- 执行命令：`.venv/bin/python scripts/run_device_matrix.py --env preprod`

| 平台 | 类型 | 设备 | 系统版本 | UDID | 通过 | 失败 | 错误 | 跳过 | 耗时 | 状态 |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| Android | 模拟器 | sdk_gphone16k_arm64 | 17 | `emulator-5554` | 7 | 0 | 0 | 0 | 256.5s | 通过 |
| iOS | 模拟器 | iPhone 17 | 26.5 | `BFE1DE67-0F95-47B7-A02A-D25EE83CD999` | 7 | 0 | 0 | 0 | 256.5s | 通过 |

两个设备上的 7 个场景均通过。每次矩阵执行都会生成按设备隔离的
pytest 日志、JUnit、Allure 原始结果和失败截图，并生成合并后的 Allure
HTML 报告。环境、平台、设备名称、系统版本和 UDID 会同时写入报告，便于
定位某条结果来自哪一台设备。

> 说明：本页来自真实执行结果，并已移除只在作者电脑上有效的绝对路径。
