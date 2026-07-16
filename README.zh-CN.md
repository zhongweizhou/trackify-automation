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
| 可评审过程 | 技术规格明确分层规则、验收标准、反模式和按任务拆分的提交纪律 |

技术规格中的 AI 失败归因和 Excel → Gherkin 同步属于后续扩展契约，本文不把
它们描述为当前已经交付的运行时能力。

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
uv run pytest --collect-only -q

# 不需要 Appium/设备，验证矩阵分片算法
.venv/bin/python -m unittest discover -s unit_tests -v
```

### 2. 单设备完整执行

```bash
# 默认 Android 设备，执行全部 7 个场景
uv run pytest

# 指定一台 Android 设备
PLATFORM=android \
DEVICE_UDID=emulator-5554 \
DEVICE_NAME="Android Emulator" \
APP_PATH="$PWD/app/app-release.apk" \
uv run pytest

# 指定一台 iOS 模拟器
PLATFORM=ios \
DEVICE_UDID=BFE1DE67-0F95-47B7-A02A-D25EE83CD999 \
DEVICE_NAME="iPhone 17" \
APP_PATH="$PWD/app/Runner.app" \
uv run pytest
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
uv run pytest -x -vv

# 只重新执行上次失败的用例
uv run pytest --lf -vv

# 调试时关闭输出捕获
uv run pytest -s -vv
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
  分片单元测试，并收集全部 7 个 BDD 场景；
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
