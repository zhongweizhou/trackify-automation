# 多环境 Profile 设计

[English](2026-07-18-multi-environment-profile-design.md) |
[简体中文](2026-07-18-multi-environment-profile-design.zh-CN.md) |
[繁體中文](2026-07-18-multi-environment-profile-design.zh-TW.md)

## 目标

将 `test`、`preprod` 和 `prod` 作为明确的执行环境。选中的环境负责提供
Trackify 共用的 onboarding Profile；交易金额、月度预算等决定业务行为的
测试值继续保留在 Excel 和 Gherkin 中。每一条 Allure 结果都必须标明执行
环境和被测 App 版本。

## 范围

本次变更包括：

- 三份经过校验且不包含敏感信息的 YAML 环境 Profile；
- 直接执行 pytest、设备矩阵和变更用例矩阵时，统一支持
  `--env test|preprod|prod`；
- Android 和 iOS 使用环境数据完成 onboarding；
- 在单条 Allure 元数据、`environment.properties`、合并报告和矩阵摘要中
  自动识别并展示 App 版本；
- 更新工作簿、Feature、README 和架构文档；
- 增加针对性单元测试，并执行现有收集与同步回归检查。

本次变更不增加按场景划分的数据 Profile、通用 `${...}` 模板替换、
Excel 到 YAML 同步、YAML 中的密钥、后端 Data Factory 或环境专属 Feature。

## 所有权边界

| 关注点 | 所有者 | 示例 |
|---|---|---|
| 场景和业务参数 | Excel managed blocks / Gherkin | 金额 `100`、预算 `30000`、预期校验文案 |
| 共用 onboarding Profile | 环境 YAML | 姓名、币种、Bank SMS Reader 设置 |
| 设备和 App 制品选择 | CLI/环境配置 | UDID、Appium URL、APK、`.app`、`.ipa` |
| 敏感信息 | CI Secret 或进程环境变量 | 将来的凭据或 Token |
| 运行时生成的后端实体 | 将来的 Data Factory | 不在本次范围内 |

Excel 继续作为 managed Scenario blocks 的权威来源。YAML 只对环境 Profile
数据负责。Sync Engine 继续保持单向 `Excel -> Feature`，永远不写入 YAML。

## 环境文件

新增以下文件：

```text
data/environments/
  test.yaml
  preprod.yaml
  prod.yaml
```

每个文件使用同一套严格 Schema：

```yaml
schema_version: 1
name: Rose
currency: "$ US Dollar"
bank_sms_reader_enabled: true
```

解析结果如下：

| 环境 | 姓名 | 币种 | Bank SMS Reader |
|---|---|---|---|
| `test` | `Rose` | `$ US Dollar` | 启用 |
| `preprod` | `Kimbal` | `$ US Dollar` | 启用 |
| `prod` | `Kimi` | `$ US Dollar` | 启用 |

`utils/environment_profile.py` 将指定文件加载为冻结的 dataclass。未知环境、
文件缺失、未知字段、无效 Schema 版本、空字符串或非布尔类型的 SMS 设置，
都必须在创建 Appium Session 前失败。环境之间不允许静默回退。

## 环境选择

只支持 `test`、`preprod` 和 `prod` 三个值。

直接执行 pytest 时，解析优先级为：

```text
pytest --env
  > TEST_ENV
  > preprod
```

支持的执行入口包括：

```bash
.venv/bin/python -m pytest --env test
.venv/bin/python scripts/run_device_matrix.py --env preprod
./scripts/run_changed_matrix.sh --env prod
```

`run_device_matrix.py` 和 `run_changed_matrix.sh` 在预检阶段拒绝不支持的环境。
矩阵 Worker 通过 `TEST_ENV` 接收已经校验的环境值。pytest 参数与环境变量
最终必须解析到同一个值；onboarding 和报告只能使用这一个最终结果。

## BDD 和 Flow 变更

两个 Feature 文件中由代码管理的 Background 改为环境驱动，同时保留明确的
业务预算：

```gherkin
Background:
  Given app is launched with a clean database
  And user enters the configured environment name and continues
  And user selects the configured environment currency and sets monthly budget "30000"
  And user applies the configured Bank SMS Reader setting and gets started
  And user is on the Home page
```

Step Definition 使用 session scope 的 `environment_profile` fixture，并把解析
后的值传给 `AppSetupFlow`。Flow 继续保证设置顺序，并验证姓名、币种符号和
SMS Reader 的目标状态。Page Object 不感知环境名称或 YAML。

工作簿中全部七条 Preconditions 改为描述环境 Profile onboarding，不再硬编码
`Kimbal`。不新增工作簿列，managed Scenario 的步骤和预期结果保持不变。

## App 版本解析

App 版本按以下优先级解析：

1. 显式设置的进程变量 `APP_VERSION`；
2. Driver 提供的 Appium capability；
3. 指定 Android UDID 上已安装 Package 的 `versionName`；
4. 指定 iOS `.app` 或 `.ipa` 中的 `CFBundleShortVersionString`；
5. 抛出配置错误，并提示调用者设置 `APP_VERSION`。

`utils/app_metadata.py` 负责平台相关的解析。它必须返回非空版本号，否则抛出
边界清晰的错误；正常完成的执行不能静默显示 `unknown`。

直接执行 pytest 时，在 Driver 创建后解析版本。矩阵 Worker 把解析结果写入
各自的 Allure 结果；矩阵汇总器读取这些属性，而不是假设 Android 和 iOS
制品一定具有相同版本。

## 报告

每条测试结果都包含以下 Allure 参数：

- Environment
- App Version
- Platform
- Device
- OS Version
- UDID

每个 Worker 的 `environment.properties` 包含：

```properties
Test.Environment=test
App.Version=1.2.3
Device.Platform=Android
Device.Name=...
Device.UDID=...
Device.OS.Version=...
```

合并后的 Allure properties 和 `summary.md` 按设备保留 App 版本。如果 Android
与 iOS 制品版本不同，报告同时展示两个版本；汇总器不能把它们合并成一个
误导性的版本。

如果 setup 在版本解析前失败，报告仍保留环境和设备身份。版本解析失败本身
属于 setup 配置失败，必须保留 Task 13 诊断证据；不能生成缺少版本信息的
成功报告。

## 生产环境安全边界

当前 Trackify 用例只清理和修改本地 App 存储，因此允许使用已有的本地
onboarding Profile 执行 `--env prod`。如果以后这些场景连接到共享生产后端，
在添加凭据或后端数据前必须重新评估破坏性 prod 执行。本设计不授权修改
生产环境后端数据。

## 错误处理

- CLI 在设备发现或同步前拒绝不支持的环境。
- Profile 校验显示环境、文件和无效字段，但不暴露敏感值。
- YAML 解析错误在 Appium setup 前终止执行。
- App 版本解析错误说明尝试的数据源，并提示 `APP_VERSION` 覆盖方式。
- 报告错误不能替换原始 pytest 失败，与现有截图和 AI Triage 行为保持一致。

## 验证

增加以下单元测试：

- 三份环境文件及其准确解析结果；
- CLI 参数优先于环境变量、环境变量优先于默认值；
- 未知环境和无效 YAML、Schema、字段失败；
- 直接 pytest 参数注册和收集隔离；
- Android、iOS `.app`、iOS `.ipa`、capability 和显式覆盖的版本解析；
- Allure properties 包含环境和 App 版本；
- 矩阵参数校验、Worker 透传、汇总和摘要输出；
- changed-matrix 环境校验；
- 环境驱动的 onboarding Flow 行为。

回归验证还必须证明：

- 所有现有单元测试通过；
- 七个 BDD 场景全部可以收集；
- Excel 与 managed Feature blocks 零漂移；
- 除 Preconditions 外，工作簿保持可读且视觉样式不变；
- `--env test`、`--env preprod` 和 `--env prod` 分别解析到正确 Profile；
- 一次受控 Allure 执行同时展示环境和 App 版本。

真实设备执行范围取决于本地可用的制品和设备。单元测试必须在不依赖 Appium
的情况下覆盖各平台元数据回退路径。
