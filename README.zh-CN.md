# Trackify 移动端 UI 自动化

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

> 面向 Trackify Flutter 个人财务应用的 AI 辅助端到端移动自动化框架。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/) [![Appium](https://img.shields.io/badge/Appium-3.x-green)](https://appium.io/) [![pytest-bdd](https://img.shields.io/badge/pytest--bdd-BDD-orange)](https://pytest-bdd.readthedocs.io/) [![Allure](https://img.shields.io/badge/Allure-Reporting-yellow)](https://allurereport.org/)

---

## 快速入口

这个仓库不仅包含 UI 操作脚本，还将移动自动化作为一个小型测试平台来
设计：架构边界明确、数据状态可重复、Android/iOS 共用业务用例、多设备
并发执行，并且每条结果都能追溯到具体环境和设备。

建议依次查看：

1. [Android + iOS 多设备测试报告示例](docs/reports/device-matrix-preprod-sample.md)
2. [技术规格](docs/TECHNICAL_SPEC.md)
3. [架构决策](docs/DESIGN.md)
4. [项目复盘](docs/REFLECTION.md)

| 工程亮点 | 仓库中的体现 |
|---|---|
| 契约驱动的 BDD | 7 个版本化场景、受控 Gherkin 词汇、可复用步骤、严格 pytest marker |
| 分层架构 | Gherkin → Step Definitions → Flow → Page Object → Appium Driver，各层职责单一 |
| 跨平台定位 | Android/iOS 定位器统一放在 YAML；优先语义化 `accessibility_id`，必要时使用受控 fallback |
| 确定性隔离 | 每条用例前清理应用数据，再完成一致的姓名、币种、月预算、Bank SMS Reader 初始化 |
| 多设备并发 | 一个命令发现全部可用 Android/iOS 设备，并通过独立 pytest 进程选择全量复制或用例分片 |
| Appium 端口隔离 | 为 Android `systemPort`、iOS WDA/MJPEG 端口和 derived-data 目录分配唯一值 |
| 可追溯报告 | 记录环境、平台、设备、系统版本、UDID、逐用例结果、JUnit、日志、截图和合并 Allure |
| 失败智能归因 | 首个失败阶段先使用确定性本地签名分类，歧义失败仅在显式开启后调用 Claude fallback |
| Excel 活用例库 | 经过校验的用例表只增量更新受管 Gherkin 块，保持未变化字节，并可只执行变化场景 |
| 可评审过程 | 技术规格明确分层规则、验收标准、反模式和按任务拆分的提交纪律 |

AI 失败归因和 Excel → Gherkin 同步都已经实现。同步边界只到受管 Scenario：
Step、Page、Flow 和 Locator 仍由代码维护。

---

## 从 Clone 到报告的执行手册

当本机 Android/iOS 工具链和模拟器已经准备好后，可以严格按下面步骤从
clone 代码执行到生成报告，无需先理解框架内部实现。

### 1. Clone 并安装依赖

```bash
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

# macOS 尚未安装 uv 时先执行
brew install uv
uv sync
npm install -g appium allure-commandline
appium driver install uiautomator2
appium driver install xcuitest
```

### 2. 放置待测应用包

应用二进制文件不会提交到 Git。请放到以下默认路径：

| 测试目标 | 应用包 | 默认路径 |
|---|---|---|
| Android 模拟器/真机 | APK | `app/app-release.apk` |
| iOS 模拟器 | 模拟器 `.app` | `app/Runner.app` |
| iOS 真机 | 已签名的真机 `.ipa` 或 `.app` | 执行时通过 `--ios-real-app` 指定 |

```bash
mkdir -p app
cp /path/to/app-release.apk app/app-release.apk
cp -R /path/to/Runner.app app/Runner.app
```

注意：iOS 模拟器不能安装仅为真机构建的应用，`Runner.app` 必须包含模拟器
架构。

### 3. 启动并确认测试设备

先在 Android Studio/Xcode 中启动需要执行的模拟器，再检查设备状态：

```bash
# Android 目标必须显示为 device，不能是 offline/unauthorized
adb devices -l

# iOS 模拟器必须显示为 Booted
xcrun simctl list devices booted
```

### 4. 在独立终端启动 Appium

Android SDK 环境变量必须在启动 Appium 的同一个终端中设置。启动后保持该
进程运行：

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium
```

### 5. 预检本次执行设备

另开一个终端，进入仓库根目录：

```bash
.venv/bin/python scripts/run_device_matrix.py --list

# 同时预览设备发现结果和具体用例分片，不执行测试
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list
```

确认列表中包含计划执行的每台设备、系统版本和 UDID。这个预检命令不会
安装应用，也不会执行用例。

### 6. 执行全部设备并打开报告

```bash
# 在发现的全部 Android + iOS 设备上并发执行 7 个场景
.venv/bin/python scripts/run_device_matrix.py --env preprod

# 将 7 个场景分摊到全部设备，每个场景只执行一次
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod
```

默认的 `replicate` 模式用于验证每台设备上的完整兼容性；需要缩短整套测试
执行时间时，使用 `split` 将互不重叠的用例子集分配给各设备。

执行结束后，终端会输出本次报告的准确路径：

```text
[matrix] Summary: .../report/device-matrix/preprod/<时间戳>/summary.md
[matrix] Allure:  .../report/device-matrix/preprod/<时间戳>/allure-report/index.html
```

`summary.md` 可以直接在编辑器中打开。macOS 打开 Allure HTML：

```bash
open "$(find report/device-matrix/preprod -path '*/allure-report/index.html' -print | sort | tail -1)"
```

如果本机只配置了一种平台，可以执行：

```bash
# 所有 Android 设备
.venv/bin/python scripts/run_device_matrix.py --platform android --env preprod

# 所有 iOS 设备
.venv/bin/python scripts/run_device_matrix.py --platform ios --env preprod
```

最终证据包括设备汇总、逐用例结果、每台设备的 pytest/JUnit 文件、合并的
Allure 报告，以及失败阶段截图。可以与仓库内提交的
[测试报告示例](docs/reports/device-matrix-preprod-sample.md)对照。

### 常见环境问题

| 现象 | 排查方式 |
|---|---|
| 没有发现设备 | 执行 `adb devices -l` 和 `xcrun simctl list devices booted`，启动或重连目标 |
| Appium connection refused | 确认独立终端中的 `appium` 仍在运行，并监听 `4723` |
| 找不到 Android SDK | 启动 Appium 前设置 `ANDROID_HOME`、`ANDROID_SDK_ROOT`，然后重启 Appium |
| 找不到应用包 | 从仓库根目录确认 `app/app-release.apk` 和/或 `app/Runner.app` 存在 |
| 缺少 XCUITest | 执行 `appium driver install xcuitest` |
| 检测到 iOS 真机但缺少应用 | 配对并解锁设备、启用开发者模式，再传入 `--ios-real-app <签名包>` |

---

## 项目概览

Trackify 是一个使用 Hive 本地数据库的离线 Flutter 个人财务应用。本项目
覆盖两个高价值用户旅程：

1. **首页 → 添加交易**：支出、收入、转账、校验和自定义类别
2. **交易列表**：按类型筛选和按日期分组

当前共有 7 个 BDD 场景：5 个 Add Transaction 场景和 2 个 Transactions
场景。同一套业务场景可以在 Android 和 iOS 上执行，平台差异收敛在 Driver、
Page 和 YAML Locator 层。

## 最常用命令

所有已启动/已连接的 Android 和 iOS 设备并发执行完整 7 个场景：

```bash
.venv/bin/python scripts/run_device_matrix.py --env preprod
```

如果希望整套 7 个场景只执行一次，并分摊到全部设备：

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod
```

运行器默认测试环境为 `preprod`，会自动发现：

- `adb devices` 中状态为 ready 的 Android 模拟器和真机；
- `xcrun simctl` 中已启动的 iOS 模拟器；
- `xcrun devicectl` 中已配对的 iOS 真机。

如果发现 iOS 真机，需要额外提供签名后的真机 `.ipa` 或 `.app`：

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

## 测试命令分类汇总

以下命令覆盖当前项目支持的主要执行方式。没有安装 `uv` 时，可将
`uv run pytest` 替换为 `.venv/bin/python -m pytest`。

### 1. 检查与收集

```bash
# 只校验 Python 导入、Gherkin、步骤绑定和 marker，不启动 Appium
uv run pytest -m "not unit" --collect-only -q

# 不需要 Appium/设备，验证矩阵分片算法
.venv/bin/python -m unittest discover -s unit_tests -v

# 不需要 Appium/设备/网络，验证 Task 13 失败归因
uv run pytest -m unit tests/unit/test_triage.py -q

# 不需要 Appium/设备，验证 Task 14 增量同步和回滚
uv run pytest -m unit tests/unit/test_sync_engine.py -q

# 检查 Excel 与 Feature 是否存在 drift，不写文件
uv run python scripts/sync_engine.py --check

# 增量更新并只执行变化用例
uv run python scripts/sync_engine.py --apply --run-changed

# 一条命令完成检查、同步，并在所有 Android/iOS 设备执行全部变化用例
./scripts/run_changed_matrix.sh
```

### 2. 单设备完整执行

```bash
# 默认 Android 设备，执行全部 7 个场景
uv run pytest -m "not unit"

# 指定一台 Android 设备
PLATFORM=android \
DEVICE_UDID=emulator-5554 \
DEVICE_NAME="Android Emulator" \
APP_PATH="$PWD/app/app-release.apk" \
uv run pytest -m "not unit"

# 指定一台 iOS 模拟器
PLATFORM=ios \
DEVICE_UDID=BFE1DE67-0F95-47B7-A02A-D25EE83CD999 \
DEVICE_NAME="iPhone 17" \
APP_PATH="$PWD/app/Runner.app" \
uv run pytest -m "not unit"
```

### 3. 按 Feature 执行

```bash
# 5 个 Add Transaction 场景
uv run pytest tests/features/add_transaction.feature -q

# 2 个 Transactions 场景
uv run pytest tests/features/transactions.feature -q
```

### 4. 按优先级或功能标签执行

```bash
# P0 冒烟场景
uv run pytest -m smoke -q
uv run pytest -m p0 -q

# P1 场景
uv run pytest -m p1 -q

# 按功能选择
uv run pytest -m custom_category -q
uv run pytest -m filter -q
uv run pytest -m grouping -q

# 当前全部优先级
uv run pytest -m "p0 or p1" -q
```

`regression` 已在 `pytest.ini` 注册，但当前场景没有 `@regression` 标签，
所以 `uv run pytest -m regression` 会收集到 0 条用例。

### 5. 执行单个场景

```bash
uv run pytest -k "add_expense_happy_path" -q
```

可用名称：

```text
add_expense_happy_path
add_income_happy_path
add_transfer_happy_path
validation__empty_amount_shows_error_and_does_not_save
add_expense_with_new_custom_category_created_in_flow
filter_transactions_by_type_shows_only_matching_type
transactions_grouped_by_date_with_section_headers
```

### 6. 多设备矩阵执行

两种分发模式：

| 模式 | 7 条用例、2 台设备时的行为 | 适用场景 |
|---|---|---|
| `replicate`（默认） | A 跑 7 条，B 跑 7 条，共 14 次设备维度执行 | 验证不同平台/设备兼容性 |
| `split` | A 跑 4 条，B 跑 3 条，共 7 次设备维度执行 | 缩短一整套测试的反馈时间 |

```bash
# 仅发现并列出设备，不执行测试
.venv/bin/python scripts/run_device_matrix.py --list

# 预览每台设备分到的具体用例，不启动 Appium 会话
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list

# 全部 Android + iOS 设备，执行完整 7 个场景
.venv/bin/python scripts/run_device_matrix.py --env preprod

# 将完整 7 个场景分摊到全部设备，每条只执行一次
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod

# 仅全部 Android 设备
.venv/bin/python scripts/run_device_matrix.py \
  --platform android \
  --env preprod

# 仅全部 iOS 设备
.venv/bin/python scripts/run_device_matrix.py \
  --platform ios \
  --env preprod

# 指定一台设备
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --device emulator-5554

# 指定多台设备；--device 可以重复
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  --device emulator-5554 \
  --device BFE1DE67-0F95-47B7-A02A-D25EE83CD999

# 在所有设备上只运行 smoke 场景；-- 后参数会透传给 pytest
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  -- \
  -m smoke
```

### 7. Allure 报告

```bash
uv run pytest \
  -m "not unit" \
  --alluredir=./allure-results \
  --clean-alluredir

# 临时启动报告服务
allure serve ./allure-results

# 生成静态报告
allure generate ./allure-results --clean -o ./allure-report
open ./allure-report/index.html
```

### 8. 失败定位和调试

```bash
# 第一次失败立即停止
uv run pytest -m "not unit" -x -vv

# 只重新执行上次失败的用例
uv run pytest -m "not unit" --lf -vv

# 调试时关闭输出捕获
uv run pytest -m "not unit" -s -vv
```

## 多设备能力亮点

`scripts/run_device_matrix.py` 不是简单循环执行命令，而是解决了真实并发
移动测试中的资源冲突和报告归属问题：

1. 自动发现 Android、iOS 模拟器和已配对 iOS 真机；
2. 为每台设备启动独立 pytest 子进程，实现并发执行；
3. 支持 `replicate` 全量复制和 `split` 互斥分片两种策略；
4. 为每个 Android 会话分配独立 `systemPort`；
5. 为每个 iOS 会话分配独立 WDA、MJPEG 端口和 derived-data 目录；
6. 每台设备拥有独立日志、JUnit、Allure 原始结果和失败截图目录；
7. 执行结束后合并 Allure 结果，并生成 Markdown 和 JSON 总结；
8. 每条报告附带环境、分片策略、测试 node ID、设备名、系统版本和 UDID；
9. Android 使用 `pm clear`、iOS 模拟器使用 `mobile: clearApp`，iOS 真机
   通过卸载重装签名应用保证场景隔离。

输出目录：

```text
report/device-matrix/<环境>/<时间戳>/
├── summary.md
├── summary.json
├── allure-results/
├── allure-report/index.html
├── android-<设备>-<udid>/
│   ├── pytest.log
│   ├── junit.xml
│   ├── allure-results/
│   └── screenshots/
└── ios-<设备>-<udid>/
    ├── pytest.log
    ├── junit.xml
    ├── allure-results/
    └── screenshots/
```

查看真实的完整执行结果：
[preprod Android + iOS 矩阵报告示例](docs/reports/device-matrix-preprod-sample.md)。

## 技术规格提炼

[`docs/TECHNICAL_SPEC.md`](docs/TECHNICAL_SPEC.md) 将实现方式定义成可评审的
工程契约，主要价值包括：

- **架构边界**：Step 不直接操作 Appium，Flow 只编排业务，Page 负责 UI，
  Driver 负责平台会话；
- **定位器治理**：定位值只能放在 YAML 中，按 accessibility id、平台原生
  策略和受控 XPath fallback 的优先级解析；
- **Fixture 注入**：Driver、Page、Flow 统一由 pytest fixture 创建，生命周期
  和 teardown 只有一个来源；
- **BDD 词汇契约**：同一动作只能使用同一套 Gherkin 表达，场景清单是测试
  范围和实现验收的共同事实源；
- **业务级断言**：不只验证点击成功，还校验交易持久化、首页月度汇总、转账
  不影响收支以及非法输入不产生数据；
- **稳定性规范**：禁止 Page 中使用固定 `sleep`，统一采用显式等待；每条场景
  从清洁状态启动；
- **失败证据**：失败时通过 pytest hook 自动截图并附加到 Allure，原始异常
  不被包装或吞掉；
- **实现纪律**：每个任务都有文件范围、验收标准、测试门槛和对应提交，便于
  评审及回溯。

## AI 失败归因

pytest 的首个失败阶段（`setup`、`call` 或 `teardown`）会生成一次建议性质
的归因结果。该结果不会改变 pytest 状态、隐藏原始 traceback、自动重试或
自动提交缺陷。

```text
[AI Triage] Locator (98%): Matched local failure signature 'element_missing'.
```

始终开启的本地阶段使用确定性签名识别 `Locator`、`App Bug`、`Env`、
`Script` 和 `Data`。弱信号不会累加置信度，无法可靠判断时返回 `Unknown`。
Allure 中会附加名为 `AI Triage` 的 JSON，包含 schema 版本、测试名称、失败
阶段、分类、置信度、原因、建议动作、分类器和命中的本地签名 ID。

Claude fallback 默认关闭。只有主动配置以下三个变量时才会启用：

```bash
export AI_TRIAGE_LLM_ENABLED=1
export ANTHROPIC_API_KEY="<key>"
export ANTHROPIC_MODEL="<model>"
```

只有本地置信度低于 `0.70` 时才允许一次请求，不重试，总超时 5 秒。错误文本
在网络调用前会被截断和脱敏，Authorization、Token、API Key 和 URL query
都会移除。截图不会上传，只允许传入“是否存在”和文件名。配置缺失、超时、
HTTP 错误或响应不合法时都安全降级为 `Unknown`。

无需 Appium、设备或网络即可执行完整 Task 13 测试：

```bash
uv run pytest -m unit tests/unit/test_triage.py -q
```

## Excel 管理的 BDD 同步

[`data/test_cases.xlsx`](data/test_cases.xlsx) 已将现有 7 条用例整理成 16 列的
可维护用例库。Excel 负责元数据及受管 `Scenario` 的动作和断言；Feature 的
标题、注释和 `Background` 仍由代码维护。Step Definition、Page、Flow、测试
数据和 YAML Locator 不会被同步引擎生成或覆盖。

```bash
# 校验 schema 并显示 added/modified/deprecated/unchanged，不写文件
uv run python scripts/sync_engine.py --check

# 只应用通过全量校验的 Scenario 变化，并执行 pytest collection
uv run python scripts/sync_engine.py --apply

# 应用后只执行新增/修改的 active 场景
uv run python scripts/sync_engine.py --apply --run-changed

# 一键检查、同步并在所有 Android/iOS 设备执行变化用例
./scripts/run_changed_matrix.sh

# 本地监听，连续写入停止 5 秒后触发
uv run python scripts/sync_engine.py --watch --apply
```

`run_changed_matrix.sh` 是推荐的跨设备变化健康门禁。它读取机器可解析的变化
清单，在写入前发现设备并检查 Appium，原子应用通过校验的 Feature 变化，然后
固定使用矩阵 `replicate` 模式：每条新增/修改的 active 用例都会在每台选中
设备执行，而不是被拆分到不同设备。

```bash
# 默认：preprod，所有已发现的 Android + iOS 设备
./scripts/run_changed_matrix.sh

# 只在全部 Android 设备执行
./scripts/run_changed_matrix.sh --platform android

# 只选择两台设备，--device 可以重复
./scripts/run_changed_matrix.sh \
  --device <Android设备UDID> \
  --device <iOS设备UDID>

# iOS 真机需要签名包
./scripts/run_changed_matrix.sh \
  --platform ios \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

退出码 `0` 表示没有待执行变化，或全部变化用例在每台设备都通过；`1` 表示
至少一条变化用例在至少一台设备失败；`2` 表示校验、collection、设备、
Appium、应用包、锁或 I/O 导致流程无法完成。报告位于
`report/changed-device-matrix/<环境>/<时间戳>/`：`summary.md` 按用例 ID ×
设备展示 Changed Case Health，`summary.json` 保存相同的机器可读变化清单和
结果，同时包含每台设备的日志、JUnit、截图及合并 Allure 证据。

引擎会在第一次写入前校验完整工作簿和两个 Feature，并使用 Module 白名单、
稳定 `scenario_id`、带微秒的备份、同目录临时文件、`os.replace` 和并发锁。
写入后的 pytest collection 失败时，会恢复本次修改的全部 Feature。未变化的
受管块直接复用原始文本切片，即使相邻场景新增、修改或弃用也保持字节一致。

`--run-changed` 用于针对性的实现和调试：通过时返回变化用例数量和 Allure
路径；运行失败时保留已经通过 collection 的 Feature 变更，通过 Task 13、
失败截图和 Allure 提供诊断，并打印准确的 pytest 重试命令，提示检查 Step、
Page/Flow 和 YAML Locator。如果新增 Gherkin 词汇还没有 Step 实现，collection
会失败并回滚 Feature，然后明确反馈缺少的实现。

同步引擎不会猜测或自动修复 Locator。定位器必须根据 Appium 页面结构和截图
证据修改并接受代码评审，否则“自愈”很容易掩盖产品缺陷。引擎也不会写回
Excel；删除一行不代表删除用例，需要使用 `Automation Status=deprecated` 和
明确的弃用版本。

### 完整操作与验收步骤

下面用“只修改一条 Excel 用例”为例，验证同步器是否只生成并执行对应场景。
最后的恢复命令只适用于演练数据，真实用例修改不要恢复。

1. 确认提交态基线：

   ```bash
   git status --short
   uv run python scripts/sync_engine.py --check
   echo $?
   ```

   正常基线应显示 `add_transaction` 5 条 unchanged、`transactions` 2 条
   unchanged，退出码为 `0`。

2. 打开 `data/test_cases.xlsx`，进入 `Test Cases` 工作表，找到
   `TC_ADD_TX_001`。演练时可将金额 `100` 改成 `101`，需要同时修改：

   - `Test Steps` 中的 `user enters amount "100"`；
   - `Expected Result` 中所有对应的金额断言。

   保存并关闭 Excel，避免 Excel 继续写临时文件。

3. 只预览增量，不写 Feature：

   ```bash
   uv run python scripts/sync_engine.py --check
   echo $?
   git status --short
   ```

   预期只显示一条 `modified: TC_ADD_TX_001`，`transactions` 模块 0 变化，
   退出码为 `1`。这里的 `1` 表示“数据合法但存在 drift”，不是同步异常。

4. 选择一种应用方式。只验证生成和 collection、不启动设备时执行：

   ```bash
   uv run python scripts/sync_engine.py --apply
   ```

   如果需要应用后立即在 Android 上只执行变化用例，则直接执行：

   ```bash
   PLATFORM=android \
   DEVICE_UDID=<Android设备UDID> \
   APP_PATH="$PWD/app/app-release.apk" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   Android UDID 可通过 `adb devices` 获取。已启动 iOS 模拟器时执行：

   ```bash
   PLATFORM=ios \
   DEVICE_UDID=<iOS模拟器UDID> \
   APP_PATH="$PWD/app/Runner.app" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   iOS UDID 可通过 `xcrun simctl list devices booted` 获取。如果目标是执行
   变化用例，不要先单独运行 `--apply`：apply 成功后已经没有 drift，随后再加
   `--run-changed` 不会重复执行。已经 apply 时，需要再修改一次 Excel。

5. 确认修改范围和最终状态：

   ```bash
   git diff -- tests/features/add_transaction.feature
   git diff -- tests/features/transactions.feature
   uv run python scripts/sync_engine.py --check
   ```

   预期只有 `TC_ADD_TX_001` 的受管块变化，最终检查退出 `0`。设备执行成功时
   会输出用例 ID、准确 pytest node ID、执行数量和
   `report/sync/<时间>/allure-results` 路径。

6. 变化用例运行失败时，已经通过 collection 的 Feature 修改会保留，控制台
   会给出准确重跑命令，并提示查看 Task 13 分类、失败截图、Allure、Step、
   Page/Flow 和 YAML Locator。同步器不会自动修改 Locator。

7. 可选回滚测试：只在 Excel 修改 Scenario Title，但不更新 Python 中对应的
   `@scenario` 绑定，然后执行 `--apply`。预期 collection 失败并退出 `2`，
   Feature 从备份恢复且锁文件被清理。Excel 不会回滚，因此修正标题前
   `--check` 仍会报告 drift。

8. 演练完成后恢复提交态基线：

   ```bash
   git restore data/test_cases.xlsx
   uv run python scripts/sync_engine.py --apply
   uv run python scripts/sync_engine.py --check
   git status --short
   ```

   真实用例修改不要执行 `git restore`。`git status --short` 中，`M` 表示已跟踪
   文件发生修改，`??` 表示未跟踪的新文件。`uv` 可能生成 `uv.lock`；它是依赖
   锁文件，不是同步器产物，建议检查后与用例修改分开提交。

命令退出码：`0` 表示零漂移或执行成功；`1` 表示 check 发现 drift，或者变化
用例运行失败；`2` 表示校验、collection、锁或 I/O 异常。

无需 Appium 或设备即可执行 Task 14 单元测试：

```bash
uv run pytest -m unit tests/unit/test_sync_engine.py -q
```

## 测试覆盖

| 功能 | P0 | P1 | 合计 | 覆盖内容 |
|---|---:|---:|---:|---|
| 首页 → 添加交易 | 4 | 1 | 5 | 支出、收入、转账、空金额校验、自定义类别、持久化和月度汇总 |
| 交易列表 | 0 | 2 | 2 | 按类型筛选、按日期分组 |
| **合计** | **4** | **3** | **7** | Android/iOS 共用业务场景 |

## 分层架构

```text
需求
  ↓
Feature Files（Gherkin）
  ↓
Step Definitions（pytest-bdd）
  ↓
Flow（业务编排和业务断言）
  ↓
Page Object（页面交互）
  ↓
Driver Wrapper（Appium）
  ↓
UiAutomator2 / XCUITest
  ↓
Trackify App
```

核心原则：

- Step Definition 不直接调用 Appium；
- Flow 组合 Page 并表达业务预期；
- Page 使用显式等待，不使用固定睡眠；
- 平台差异留在 Locator、Page 和 Driver 层；
- 每条场景都从清洁数据库和一致 onboarding 基线开始。

## 快速开始

### 前置条件

- Python 3.11+
- Node.js LTS
- Android SDK / Platform Tools
- Xcode 和 Command Line Tools（执行 iOS 时）
- 已启动的 Android/iOS 设备
- Android APK：`app/app-release.apk`
- iOS 模拟器应用：`app/Runner.app`

### 安装

```bash
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

brew install uv
uv sync
npm install -g appium allure-commandline
appium driver install uiautomator2
appium driver install xcuitest
```

启动 Appium 的终端必须能读取 Android SDK 环境变量：

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium
```

## CI

`.github/workflows/ci.yml` 提供两层校验：

- push 到 `test`、Pull Request 和手动触发时，安装依赖、运行无需设备的矩阵
  分片、失败归因和同步单元测试，拒绝 Excel drift，并收集全部 7 个 BDD
  场景；
- 配置 `TRACKIFY_APK_URL` 后，在 Android API 34 模拟器中执行完整 E2E；
- 上传 Allure 原始结果、HTML 报告、失败截图和 Appium 日志；
- 未配置 APK secret 时只跳过移动 E2E，测试收集仍然作为合并门禁。

## 已验证结果

真实矩阵执行结果：

```text
环境：preprod
Android 17：7 passed / 0 failed
iOS 26.5：   7 passed / 0 failed
总计：       14 次设备维度用例执行全部通过
```

详细数据见[测试报告示例](docs/reports/device-matrix-preprod-sample.md)。

## 更多文档

- [完整技术规格](docs/TECHNICAL_SPEC.md)
- [架构和取舍](docs/DESIGN.md)
- [功能探索记录](docs/Feature_Inventory.md)
- [扩展路线](docs/SCALING.md)
- [项目复盘](docs/REFLECTION.md)
