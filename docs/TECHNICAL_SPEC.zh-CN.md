# Trackify 自动化 — 技术规范(TECHNICAL_SPEC.md)

> **受众**:Codex / Claude Code(实施者)
> **目的**:定义如何构建 `README.md` 所描述的内容。
> **不要在此修改范围** —— 范围由 `README.md` 与 `Feature_Inventory.md` 定义。
> **本文档定义 HOW。**

---

## 1. 技术栈(锁定版本)

| 组件 | 版本 | 理由 |
|-----------|---------|-----|
| Python | 3.11+ | 类型提示 + async/await |
| pytest | 8.x | BDD runner |
| pytest-bdd | 7.x | Gherkin → pytest steps |
| Appium | 3.x | 跨平台移动驱动 |
| Appium UiAutomator2 Driver | latest | Android 驱动 |
| Appium XCUITest Driver | latest | iOS(仅扩展) |
| Selenium-Python | 4.x | Appium 的底层依赖 |
| allure-pytest | 2.x | Allure 报告 |
| pyyaml | 6.x | Locator YAML 解析 |
| openpyxl | 3.x | Excel 同步引擎(Task 14) |
| watchdog | 4.x | 同步触发的文件系统事件(Task 14) |
| uv | latest | 快速 Python 包管理器 |
| Allure CLI | latest | 报告渲染器 |

> ❌ **不要新增**:Poetry、pipenv、conda、Docker、Flake8、Black、MyPy、Pylint、pre-commit 钩子、**gherkin(Python 库)**(同步 PoC 用正则,见 §11)。上表以外的任何内容都属于范围蔓延。

---

## 2. 目录结构(不可变)

```
trackify-automation/
├── README.md                        # 公开范围(给评估者)
├── TECHNICAL_SPEC.md                # 本文件(给 Codex)
├── pyproject.toml                   # uv 管理的 Python 依赖
├── pytest.ini                       # BDD + markers 配置
├── conftest.py                      # 全局 fixtures(appium driver、db reset)
│
├── docs/
│   ├── Feature_Inventory.md         # 第 1 天手动探索
│   ├── DESIGN.md                    # 架构理由
│   ├── TECHNICAL_SPEC.md            # 本文件
│   ├── SCALING.md                   # Q1-Q6 战略路线图(长期、非阻塞)
│   └── REFLECTION.md                # 复盘(第 5 天)
│
├── app/                             # 不提交
│   ├── app-release.apk
│   └── Runner.app
│
├── tests/
│   ├── features/                    # Gherkin 文件(BDD)
│   │   ├── add_transaction.feature
│   │   └── transactions.feature
│   ├── step_defs/                   # pytest-bdd step 实现
│   │   ├── __init__.py
│   │   ├── add_transaction_steps.py
│   │   └── transactions_steps.py
│   └── __init__.py
│
├── locator/                         # YAML 文件(每页一个)
│   ├── onboarding.yaml
│   ├── home.yaml
│   ├── add_transaction.yaml
│   └── transactions.yaml
│
├── page/                            # Page Object 模式
│   ├── __init__.py
│   ├── base_page.py                 # 抽象基类 —— 所有 Page 都继承
│   ├── onboarding_page.py
│   ├── home_page.py
│   ├── add_transaction_page.py
│   └── transactions_page.py
│
├── flow/                            # 业务逻辑(调用 Page)
│   ├── __init__.py
│   ├── app_setup_flow.py
│   ├── add_transaction_flow.py
│   └── transactions_flow.py
│
├── utils/                           # 横切工具
│   ├── __init__.py
│   ├── driver.py                    # Appium driver 工厂
│   ├── locator_loader.py            # YAML → dict
│   ├── system_dialogs.py            # 定向的 Android 权限处理
│   └── config.py                    # 从 pytest.ini 读取 platform / device
│
├── ai/                              # AI 辅助模块(第 4 天)
│   ├── __init__.py
│   ├── gen_cases.py                 # LLM 起草的 BDD 用例思路
│   └── triage.py                    # 基于 LLM 的失败分类器
│
├── data/
│   ├── test_cases.xlsx              # 手动用例登记册(Task 14 同步源)
│   ├── test_cases_template.xlsx     # 可复用的校正后七用例基线
│   └── .backup/                     # sync_engine.py 每次写入前自动生成
│
├── scripts/
│   └── sync_engine.py               # Excel → .feature 检查/应用(Task 14 PoC)
│
├── report/
│   ├── allure-results/              # 每次运行生成
│   ├── screenshots/                 # 失败时生成
│
└── assets/
    └── run_demo.mp4                 # 一次成功运行的录屏
```

**规则**:
- ❌ 不要把测试文件放在项目根目录。
- ❌ 不要把 Page / Flow / Driver 代码放在 `tests/`。
- ❌ 不要硬编码路径;使用 `pathlib.Path(__file__).parent`。

---

## 3. 编码规范(严格)

### 3.1 类型提示(强制)

```python
# ✅ GOOD
def click_add_expense(self) -> None:
    self._driver.click(self._loc("add_expense_button"))

# ❌ BAD
def click_add_expense(self):
    self._driver.click(self._loc("add_expense_button"))
```

所有 public 方法必须具备:
- 参数类型
- 返回类型

### 3.2 文档字符串(Google 风格,public 类/函数强制)

```python
def add_expense(amount: float, category: str, note: str = "") -> str:
    """添加一笔支出交易,并返回新交易的 ID。

    Args:
        amount: 交易金额(正数;符号由类型隐含)。
        category: 类别名(必须已在设置中存在)。
        note: 可选自由文本备注。

    Returns:
        新创建交易的 ID。
    """
    ...
```

### 3.3 命名

| 元素 | 规范 | 示例 |
|---------|------------|---------|
| 类 | PascalCase | `AddTransactionPage` |
| 函数 / 方法 | snake_case | `add_expense_transaction` |
| 常量 | UPPER_SNAKE | `DEFAULT_TIMEOUT = 10` |
| 私有(内部) | `_leading_underscore` | `_driver` |
| 文件 | snake_case.py | `add_transaction_page.py` |
| YAML 键 | snake_case | `add_expense_button:` |

### 3.4 Imports

```python
# ✅ GOOD — 三组,标准库在前,组间空行
# 1. stdlib
from pathlib import Path

# 2. third-party
import pytest
from appium.webdriver import WebElement

# 3. local
from page.base_page import BasePage
from utils.locator_loader import load_locator
```

```python
# ❌ BAD — local 排在 third-party 之前,没有空行,星号导入
from page.base_page import BasePage
from appium.webdriver import *
import pytest
from utils.locator_loader import load_locator
```

**为什么顺序很重要**:
- isort / ruff 自动修复会把乱序 import 视为错误 —— 从一开始就手动保持顺序可以避免日后大规模整理。
- 星号导入(`from X import *`)会让 grep 无法定位,并隐藏未使用 import 的提示。

---

## 4. Locator 策略(仅 YAML)

### 4.1 格式

`locator/<page>.yaml` —— 每页一个文件:

```yaml
# locator/add_transaction.yaml

add_expense_button:
  description: "Home 页面上打开 Add Transaction 模态框的按钮"
  android:
    accessibility_id: "Add Expense"
  ios:
    accessibility_id: "Add Expense"

amount_input:
  description: "交易金额的数字输入框"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

transaction_type_toggle:
  description: "在 Expense / Income / Transfer 之间切换的 Tabs"
  android:
    xpath: "//*[@resource-id='com.blixcode.trackify:id/transaction_type_toggle']"
  ios:
    predicate: "type == 'XCUIElementTypeOther' AND name == 'Transaction Type'"
```

**完整 yaml 模板**(用作每个新页面的起点):

```yaml
# locator/add_transaction.yaml — 参考骨架

# ---- 类型切换(Expense / Income / Transfer) ----
type_toggle_expense:
  description: "选择 Expense 类型的 Tab"
  android:
    accessibility_id: "Expense"
  ios:
    accessibility_id: "Expense"

type_toggle_income:
  description: "选择 Income 类型的 Tab"
  android:
    accessibility_id: "Income"
  ios:
    accessibility_id: "Income"

type_toggle_transfer:
  description: "选择 Transfer 类型的 Tab"
  android:
    accessibility_id: "Transfer"
  ios:
    accessibility_id: "Transfer"

# ---- 金额 ----
amount_input:
  description: "交易金额数字输入框(支持小数)"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

# ---- 类别 ----
category_dropdown:
  description: "选择现有类别的下拉框"
  android:
    accessibility_id: "Category"
  ios:
    accessibility_id: "Category"

category_option_food:
  description: "下拉列表中标为 'Food' 的类别选项"
  android:
    xpath: "//*[contains(@content-desc, 'Food')]"
  ios:
    predicate: "label == 'Food'"

new_category_button:
  description: "横向类别列表最右端的 New 图块"
  android:
    accessibility_id: "New"
  ios:
    accessibility_id: "New"

manage_categories_title:
  description: "通过 New 图块打开的 Manage Categories 页面"
  android:
    accessibility_id: "Manage Categories"
  ios:
    accessibility_id: "Manage Categories"

add_category_button:
  description: "打开 New Category 表单"
  android:
    accessibility_id: "Add Category"
  ios:
    accessibility_id: "Add Category"

custom_category_name_input:
  description: "自定义类别名的文本输入"
  android:
    xpath: "//android.widget.EditText[@hint='Category Name']"
  ios:
    xpath: "//XCUIElementTypeTextField[@placeholderValue='Category Name']"

# ---- 日期 ----
date_picker_trigger:
  description: "点击以打开原生日期选择器"
  android:
    accessibility_id: "Pick date"
  ios:
    accessibility_id: "Pick date"

# ---- 备注 / 标签 ----
notes_input:
  description: "自由文本备注(也作为标签,逗号分隔)"
  android:
    accessibility_id: "Notes"
  ios:
    accessibility_id: "Notes"

# ---- 操作 ----
save_button:
  description: "提交交易"
  android:
    accessibility_id: "Save"
  ios:
    accessibility_id: "Save"

cancel_button:
  description: "丢弃并关闭模态框"
  android:
    accessibility_id: "Cancel"
  ios:
    accessibility_id: "Cancel"

# ---- 校验 ----
amount_error_message:
  description: "金额为空或非法时的内联错误"
  android:
    xpath: "//*[contains(@text, 'required') or contains(@text, 'invalid')]"
  ios:
    predicate: "type == 'XCUIElementTypeStaticText' AND (label CONTAINS 'required' OR label CONTAINS 'invalid')"
```

**规则**:
- ✅ 每个条目都必须有 `description`(人类可读的用途说明)。
- ✅ 至少填 `android.accessibility_id`(Flutter 把语义 ID 渲染为 accessibility 标签)。
- ⚠️ XPath 是兜底 —— 仅在不存在 accessibility_id 时使用。
- ❌ 永远不要在 Python 文件中硬编码 Locator。

### 4.2 Locator Loader(utils/locator_loader.py)

```python
"""带策略回退链的 Locator loader(见 §4.3)。"""

from pathlib import Path
import yaml

# 顺序很关键 —— 首个命中即胜出。参见 §4.3。
_STRATEGY_PRIORITY = ("accessibility_id", "id", "xpath", "predicate")

# 模块级缓存:(page, key, platform) -> (strategy, value)
_cache: dict[tuple[str, str, str], tuple[str, str]] = {}


def load_locator(page: str, key: str, platform: str = "android") -> tuple[str, str]:
    """返回请求 locator 的 (strategy, value)。

    遍历 §4.3 的优先级链。如果没有匹配策略则抛 KeyError。

    Page 中的用法:
        strategy, value = load_locator("add_transaction", "amount_input")
        by = AppiumBy[strategy.upper()]   # ACCESSIBILITY_ID / ID / XPATH / PREDICATE
        element = driver.find_element(by, value)
    """
    cache_key = (page, key, platform)
    if cache_key in _cache:
        return _cache[cache_key]

    yaml_path = Path(__file__).parent.parent / "locator" / f"{page}.yaml"
    data = yaml.safe_load(yaml_path.read_text())
    entry = data[key][platform]

    for strategy in _STRATEGY_PRIORITY:
        if strategy in entry and entry[strategy]:
            _cache[cache_key] = (strategy, entry[strategy])
            return _cache[cache_key]

    raise KeyError(
        f"No locator for {page}.{key} on {platform}. "
        f"Available keys: {list(entry.keys())}"
    )


def clear_cache() -> None:
    """仅供测试使用:清空缓存,让 locator 从 YAML 重新读取。"""
    _cache.clear()
```

**为什么使用回退链而不是严格的 `accessibility_id`**:
§4.1 的示例中,`transaction_type_toggle` 在 Android 上没有 accessibility_id(只有 `xpath`)。严格的 `entry[platform]["accessibility_id"]` 查找会抛 `KeyError`。遍历 `_STRATEGY_PRIORITY` 让 loader 在 YAML 增长时保持健壮。

### 4.3 严格的优先级顺序

1. `accessibility_id`(Flutter 语义标签)—— **首选**
2. `id` / `resource-id`
3. `class` 链
4. `xpath`(最后手段)
5. `predicate`(仅 iOS)

---

## 5. 架构分层

```
┌─────────────────────────────────────────┐
│  tests/features/*.feature               │  Gherkin(人类语言)
└──────────────────┬──────────────────────┘
                   │ pytest-bdd 发现
                   ▼
┌─────────────────────────────────────────┐
│  tests/step_defs/*_steps.py             │  Step 实现
│  (Given/When/Then → 调用 Flow)          │
└──────────────────┬──────────────────────┘
                   │ 调用
                   ▼
┌─────────────────────────────────────────┐
│  flow/*_flow.py                         │  业务逻辑
│  (用例编排)                             │
└──────────────────┬──────────────────────┘
                   │ 使用
                   ▼
┌─────────────────────────────────────────┐
│  page/*_page.py                         │  Page Object
│  (UI 元素动作)                          │
└──────────────────┬──────────────────────┘
                   │ 继承
                   ▼
┌─────────────────────────────────────────┐
│  page/base_page.py                      │  抽象基类
│  (click, input, swipe, wait, screenshot)│
└──────────────────┬──────────────────────┘
                   │ 使用
                   ▼
┌─────────────────────────────────────────┐
│  utils/driver.py                        │  Appium 封装
│  (不允许在外部使用裸 driver.find_element)│
└──────────────────┬──────────────────────┘
                   ▼
               Appium → Trackify App
```

**分层规则**:
- ❌ step def 不允许直接 import `page.*` —— 必须经过 Flow。
- ❌ Flow 不允许直接 import `utils.driver` —— 只调用 Page 方法。
- ❌ Page 之间不允许互相 import —— 保持彼此独立。
- ✅ Base page 暴露基本操作:`click`、`input_text`、`swipe`、`wait_for`、`screenshot`、`is_visible`。

### 5.1 Fixture 接线(conftest.py)

driver 与每个 Page / Flow 实例都必须通过 pytest fixtures 注入 —— 不要在 step 体里直接实例化。这样可以让 teardown 路径单一来源。

```python
# conftest.py
import os
import subprocess
from pathlib import Path

import allure
import pytest
from appium.webdriver import WebElement

from page.onboarding_page import OnboardingPage
from page.home_page import HomePage
from page.add_transaction_page import AddTransactionPage
from page.transactions_page import TransactionsPage
from flow.app_setup_flow import AppSetupFlow
from flow.add_transaction_flow import AddTransactionFlow
from flow.transactions_flow import TransactionsFlow
from utils.driver import AppiumDriverFactory

PKG = "com.blixcode.trackify"  # Trackify Android 包名


@pytest.fixture(scope="session")
def driver() -> WebElement:
    """Session 级 Appium driver —— 每次 pytest 运行一个会话。"""
    platform = os.getenv("PLATFORM", "android")
    factory = AppiumDriverFactory(platform=platform)
    d = factory.create()
    yield d
    d.quit()


@pytest.fixture(autouse=True)
def reset_app_state(driver):
    """每个测试前清空 Hive DB,以保证状态确定性。

    为什么用 `pm clear`(而不是 seed 文件):
    - Trackify 将数据存在 Hive 的 /data/data/<pkg>/app_flutter/hive_box.db。
    - 通过设置 UI 清空不稳定且依赖顺序。
    - `pm clear` 是一条 ADB 命令,<1s 完成,是官方重置路径。
    """
    subprocess.run(["adb", "shell", "pm", "clear", PKG], check=True, timeout=10)
    driver.launch_app()  # 清空后重新启动
    yield


# Page fixtures —— 薄包装,按测试懒构造
@pytest.fixture
def home_page(driver) -> HomePage:
    return HomePage(driver)

@pytest.fixture
def onboarding_page(driver) -> OnboardingPage:
    return OnboardingPage(driver)

@pytest.fixture
def add_transaction_page(driver) -> AddTransactionPage:
    return AddTransactionPage(driver)

@pytest.fixture
def transactions_page(driver) -> TransactionsPage:
    return TransactionsPage(driver)

# Flow fixtures —— 组合 Page
@pytest.fixture
def app_setup_flow(onboarding_page, home_page) -> AppSetupFlow:
    return AppSetupFlow(onboarding_page, home_page)

@pytest.fixture
def add_transaction_flow(home_page, add_transaction_page, transactions_page) -> AddTransactionFlow:
    return AddTransactionFlow(home_page, add_transaction_page, transactions_page)

@pytest.fixture
def transactions_flow(transactions_page) -> TransactionsFlow:
    return TransactionsFlow(transactions_page)
```

**为什么 fixture 接线很重要**:
- 没有它,step def 会自己调用 `HomePage(driver())` → 没有 teardown,会话泄漏。
- `reset_app_state` 使用 `autouse=True`,因此每个测试都从一个干净的 Hive 开始。
- 重置后,每个 feature 的 `Background` 在业务动作开始前完成相同的三段首次运行阶段:保存名字 `Kimbal`;选择 `$ US Dollar` 与月度预算 `30000`;启用 Bank SMS Reader 并点击 `Get Started`。
- 永远不要把 onboarding 的 `Skip` 当作测试前置条件。Skip 会让 profile、currency、budget 与追踪偏好都处于未定义状态。
- 每个 Page Object 的 wait 都会检查 Android 系统弹窗 `Allow Trackify to send you notifications?` 并在继续前点击 `Allow`。handler 只匹配通知文案,不接受 SMS 等其它权限弹窗。

---

## 6. BDD 约定(pytest-bdd)

### 6.1 文件命名

- 每页/功能一个 `.feature` 文件。
- 每个 `.feature` 对应一个 `_steps.py`,文件名匹配。

### 6.2 场景 tags(pytest markers)

```gherkin
@smoke @p0
Scenario: Add expense with all fields
  Given User is on Home page
  When User adds expense "100" with category "Food" and note "breakfast with Dinna"
  Then New expense should appear in Recent transactions

@regression @p1
Scenario: Add a new custom category during transaction flow
  ...
```

### 6.3 Step 函数复用

```python
# tests/step_defs/add_transaction_steps.py

from pytest_bdd import given, when, then, parsers

@given("User is on Home page")
def on_home(home_page):
    home_page.verify_visible()

@when(parsers.parse('User adds {type:d} expense with category "{category}"'))
def add_expense(amount, category, ...):
    flow.add_expense_transaction(amount=amount, category=category, ...)
```

**规则**:
- ✅ 使用 `parsers.parse(...)` 参数化 —— 避免在 step 里硬编码字符串。
- ✅ 跨场景复用 step;不要复制逻辑。
- ❌ step 体里不允许 inline 断言 —— 只允许在 `Then` step 中断言。

### 6.4 pytest markers(pytest.ini)

```ini
[pytest]
# ---- discovery ----
testpaths = tests
bdd_features_base_dir = tests/features
python_files = *_steps.py test_*.py
python_classes = Test*
python_functions = test_*

# ---- markers (v3 范围) ----
markers =
    smoke: P0 critical path
    regression: P0 + P1 full coverage
    p0: critical priority
    p1: high priority
    custom_category: 自定义类别流程(在 Add Transaction 内新增 category)
    filter: 列表筛选(Transactions 按 type / category / 日期)
    grouping: 列表按日期分组(Transactions 列表展示)

# ---- output ----
addopts = -ra --strict-markers --tb=short
```

**逐字段解释**:

| 字段 | 原因 |
|-------|----------------|
| `testpaths` | 把收集范围限定在 `tests/` —— 避免误收集 `page/`、`flow/`、`utils/` |
| `bdd_features_base_dir` | pytest-bdd 需要知道 `.feature` 文件的位置;否则收集到的 ID 中 feature 路径错误 |
| `python_files = *_steps.py` | pytest-bdd 要求 step 文件以 `_steps.py` 结尾;这个 glob 强制这一点,即使有人起名 `add_transaction.py` |
| `--strict-markers` | 像 `@smoek` 这样的拼写错误会直接报错而不是被默默忽略 —— 尽早发现 marker 错误 |
| `--tb=short` | traceback 截断为每个失败一帧 —— 让 Allure 报告更易扫读 |

**v3 范围的 marker 映射**(7 个 BDD 场景):

| Marker | 场景 |
|--------|-----------|
| `@smoke @p0` | Add Expense、Add Income、Add Transfer、Validation(空金额) |
| `@p1` | Custom Category、Filter by type、Group-by-date |

### 6.5 Gherkin 风格指南

如果没有这些规则,每个场景读起来就像一次独立的 AI 生成。Codex 必须遵守全部规则:

| 规则 | 原因 |
|------|-----|
| **第三人称、现在时** —— "user taps Save",不要 "I tap Save" 或 "user tapped Save" | 与 pytest-bdd 的 step 正则默认一致;统一时态避免 step_defs 重复 |
| **使用 "user"(不用 "the user" / "users" / "I")** | 在所有 .feature 中只需 grep 一个 token |
| **同一动作 = 同一措辞** —— 如果一个场景用 "user enters amount",所有场景都用 "user enters amount" | step 匹配是精确字符串;动词漂移 = "step definition not found" |
| **数据驱动场景使用 `Scenario Outline` + `Examples`**;只在场景真正唯一时才使用 `Scenario` | 减少 .feature 行数;一个 step_def 可驱动 N 个场景 |
| **公共 setup 放入 `Background`** —— 每个 feature 文件开头都有一个 `Background:` 块;不要在每个 Scenario 中重复 "user is on X page" | DRY;一处修改即可改变前置条件 |
| **`Then` 必须同时包含**:(a) **具体的值断言** AND (b) **否定断言**("X did NOT happen") | 防止错误交易被保存的回归;避免过于宽泛的匹配 |
| **一个 feature = 一条用户路径** —— `add_transaction.feature` 覆盖 3 种交易类型 + 校验 + 自定义类别(5 个场景);`transactions.feature` 覆盖 filter + grouping(2 个场景) | 每个 .feature 文件 = 一种评审心智模型 |
| **使用 `And` / `But` 在同一子句中串联步骤** —— 不要重复 `Given` / `When` / `Then` | 符合 Gherkin 可读性规范 |

**需要拒绝的反模式**:

```gherkin
# ❌ BAD — 第一人称 + 过去时 + "the user"
Given I was on the Home page

# ❌ BAD — 同一动作在三个场景里用不同动词
# 场景 A:
When user enters amount "100"
# 场景 B:
When user inputs amount "200"
# 场景 C:
When user types amount "300"

# ❌ BAD — Then 模糊,缺少具体值或否定检查
Then the transaction is saved

# ❌ BAD — 在每个 Scenario 中把 Background 当作 Given 重复
Scenario: Add expense
  Given app is launched with clean database
  And user is on the Home page
  When ...
Scenario: Add income
  Given app is launched with clean database
  And user is on the Home page
  When ...
```

### 6.6 Step 词汇契约

**这是一份契约**:`step_defs/*_steps.py` 必须实现下面的每个短语,每个 `.feature` 文件必须只使用这些短语。新增一个短语,必须在同一次提交中同时添加 Gherkin 用法与 Python step。

#### Given 短语(3 个页面上下文 + 4 个 Background 步骤)

```gherkin
# 在每个 .feature 的 Background: 块中使用一次
Given app is launched with a clean database
Given user enters name "<name:str>" and continues
Given user selects currency "<currency:str>" and sets monthly budget "<monthly_budget:int>"
Given user enables Bank SMS Reader and gets started

Given user is on the Home page
Given user is on the Add Transaction page
Given user is on the Transactions page
```

#### When 短语(14 个动作)

```gherkin
When user taps "<shortcut_name:str>"
When user selects type "<type:str>"                  # type ∈ {expense, income, transfer}
When user enters amount "<amount:float>"
When user leaves amount empty
When user selects category "<category:str>"
When user enters note "<note:str>"
When user enters tags "<tags:str>"
When user selects transaction date and time "<date_time:str>"
When user taps Save
When user taps Cancel
When user taps "Add new category"
When user creates custom category "<name:str>"
When user navigates to the Transactions page
When user filters transactions by type "<type:str>"  # type ∈ {expense, income, transfer}
```

#### Then 短语(9 个断言)

```gherkin
Then transaction appears in Recent transactions with amount "<amount:float>"
Then error message "<message:str>" is shown for amount
Then no transaction appears in Recent transactions
Then no transaction appears in Recent transactions with category "<category:str>" missing
Then Transactions shows the saved transaction with matching date, amount, category, and time
Then Transactions contains no transactions
Then This Month summary is correct for budget "<monthly_budget:int>"
Then only transactions of type "<type:str>" are shown
Then transactions are grouped by date with section headers
```

**解析规则**(用于 step_defs 中的 `parsers.parse(...)`):

| 占位符 | 类型 | 示例值 | 校验 |
|-------------|------|---------------|------------|
| `<type:str>` | `str` | `"expense"` | 必须是 `expense`、`income`、`transfer` 之一(在 Flow 中校验,而非 step) |
| `<amount:float>` | `float` | `100.0`、`9.99` | 必须 `> 0`(在 Flow 中校验) |
| `<category:str>` | `str` | `"Food"`、`"Transport"` | 自由文本 |
| `<note:str>` | `str` | `"breakfast with Dinna"` | 自由文本 |
| `<tags:str>` | `str` | `"food,breakfast"` | 非空、逗号分隔的标签文本 |
| `<name:str>` | `str` | `"baby cost"` | 自由文本 |
| `<currency:str>` | `str` | `"$ US Dollar"` | 完整的可见选项标签 |
| `<monthly_budget:int>` | `int` | `30000` | 必须是正整数,且与展示的滑块值一致 |
| `<message:str>` | `str` | `"Amount is required"` | 对展示文本做子串匹配 |
| `<date_time:str>` | `str` | `"20250506 9:00 AM"` | `YYYYMMDD h:mm AM/PM` 格式的本地日期/时间 |

**Add Transaction 保存后断言规则**:
- 在点 Save 之前先在 Add Transaction 上捕获展示的日期与时间。Transactions 的断言必须在对应日期下找到一行,该行包含同样格式化的金额、类别与时间。
- Expense 与 Income 交易分别累加 Home 上既有的 `This Month` expense 与 income 值。Transfer 交易不改变任何一项。
- 大号的 `This Month` 值是 `income - expense`。
- 展示的预算百分比为 `expense / budget * 100`,按 half-up 规则(`ROUND_HALF_UP`)取整。例如预算 `20000`:expense `125` 得 `0.625%`,显示 `1%`;expense `1125` 得 `5.625%`,显示 `6%`;expense `9500` 得 `47.5%`,显示 `48%`。
- 空金额的校验必须让 Recent Transactions 与 Transactions 页面同时为空,并且所有 `This Month` 值保持不变。

→ **这些短语的实际使用位置**:见 §6.7 场景清单 v3。每个场景都是由这些短语的子集组合而成。如果 §6.7 需要一个不在此处的短语,必须先在此处添加,然后在同一次提交中更新场景。

### 6.7 场景清单 v3(§7 任务 8 / 8b / 10 的唯一事实来源)

下面 7 个场景是**唯一的真相来源**。§7 任务 8 / 8b / 10 的验收标准按准确标题引用本清单。

#### `tests/features/add_transaction.feature` —— 5 个场景

```gherkin
Feature: Add Transaction

  Background:
    Given app is launched with a clean database
    And user enters name "Kimbal" and continues
    And user selects currency "$ US Dollar" and sets monthly budget "30000"
    And user enables Bank SMS Reader and gets started
    And user is on the Home page

  @smoke @p0
  Scenario: Add expense happy path
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters note "breakfast"
    And user enters tags "food,breakfast"
    And user taps Save
    Then transaction appears in Recent transactions with amount "100.0"
    And Transactions shows the saved transaction with matching date, amount, category, and time
    And This Month summary is correct for budget "30000"

  @smoke @p0
  Scenario: Add income happy path
    When user taps "Add Income"
    And user enters amount "5000"
    And user selects category "Salary"
    And user enters tags "salary,work"
    And user taps Save
    Then transaction appears in Recent transactions with amount "5000.0"
    And Transactions shows the saved transaction with matching date, amount, category, and time
    And This Month summary is correct for budget "30000"

  @smoke @p0
  Scenario: Add transfer happy path
    When user taps "Add Transfer"
    And user enters amount "200"
    And user selects category "Food"
    And user enters tags "transfer"
    And user taps Save
    Then transaction appears in Recent transactions with amount "200.0"
    And Transactions shows the saved transaction with matching date, amount, category, and time
    And This Month summary is correct for budget "30000"

  @smoke @p0
  Scenario: Validation — empty amount shows error and does not save
    When user taps "Add Expense"
    And user leaves amount empty
    And user selects category "Food"
    And user taps Save
    Then error message "Amount is required" is shown for amount
    And no transaction appears in Recent transactions
    And Transactions contains no transactions
    And This Month summary is correct for budget "30000"

  @p1 @custom_category
  Scenario: Add expense with new custom category created in flow
    When user taps "Add Expense"
    And user enters amount "50"
    And user taps "Add new category"
    And user creates custom category "baby cost"
    And user enters tags "baby,family"
    And user taps Save
    Then transaction appears in Recent transactions with amount "50.0"
    And no transaction appears in Recent transactions with category "baby cost" missing
    And Transactions shows the saved transaction with matching date, amount, category, and time
    And This Month summary is correct for budget "30000"
```

当前 Android 版本的实现说明:
- Gherkin 短语 `user taps "Add new category"` 对应于在横向 Category 列表上向左滑动,然后依次 `New` → `Add Category`。
- `baby cost` 使用 New Category 表单的默认图标与颜色。其固定宽度的交易 chip 只显示截断后的 `baby`,但 Manage Categories 与保存后的 Home 交易保留全名。
- 空金额提交停留在 Add Transaction 上,字段为空,不保存任何内容。该版本不向 accessibility 暴露期望的校验文案,因此断言优先以可见文案为准,否则在校验 Home 列表为空前先校验表单被拒绝的状态。
- 在预算 `30000` 下,expense `100` 与 `50` 产生的百分比低于 `0.5%`,按 half-up 取整后正确显示为 `0%`。

#### `tests/features/transactions.feature` —— 2 个场景

```gherkin
Feature: Transactions List

  Background:
    Given app is launched with a clean database
    And user enters name "Kimbal" and continues
    And user selects currency "$ US Dollar" and sets monthly budget "30000"
    And user enables Bank SMS Reader and gets started
    And user is on the Home page

  @p1 @filter
  Scenario: Filter transactions by type shows only matching type
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters tags "filter,expense"
    And user taps Save
    And user taps "Add Income"
    And user enters amount "5000"
    And user selects category "Salary"
    And user enters tags "filter,income"
    And user taps Save
    And user navigates to the Transactions page
    And user filters transactions by type "expense"
    Then only transactions of type "expense" are shown

  @p1 @grouping
  Scenario: Transactions grouped by date with section headers
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters tags "history,expense"
    And user selects transaction date and time "20250506 9:00 AM"
    And user taps Save
    And user navigates to the Transactions page
    Then transactions are grouped by date with section headers
```

> Transactions 场景复用了 `tests/step_defs/common_steps.py` 中的 setup 与交易录入 step;feature 特定的 step 只负责导航、筛选与列表行为断言。

**为什么这份清单在这里,而不是只放在 Feature_Inventory.md**:
- `Feature_Inventory.md` 是 **what**(哪些功能、为什么选)。
- `TECHNICAL_SPEC.md` §6.7 是 **how**(准确的场景标题、tags、Given/When/Then 行)。
- 这样分开,让评估者通过 `Feature_Inventory.md` 读范围理由,Codex 通过 §6.7 读实现细节。

---

## 7. 实施任务清单(13 个任务,每个一次提交)

> ⚠️ **在前置任务已提交且 `pytest` 运行干净(或还没有测试)之前,不要执行任何任务。**

### 第 0 天 —— 手动前置(无提交,一次性)

这些步骤在开发机上执行一次,在 Task 1 之前。它们不产生提交。

```bash
# 1. Appium server 工具链
npm install -g appium                              # CLI
appium driver install uiautomator2                 # Android driver

# 2. 可选：手动启动 Appium（矩阵 Runner 可以自动启动）
appium --address 127.0.0.1 --port 4723           # 监听 :4723

# 3. 手动启动时验证 server 在线
curl --noproxy '*' http://localhost:4723/status | jq . # 期望 ready=true

# 4. 验证模拟器 + app 包
adb devices                                        # 列出已连接设备
adb install -r -t app/app-release.apk              # 安装 Trackify
adb shell pm list packages | grep com.blixcode.trackify # 确认包存在
```

**直接执行 pytest 前修复相关失败。** 矩阵 Runner 会自动检查或启动本机
Appium；应用包和驱动安装失败仍必须在执行前修复。

| # | 任务 | 涉及文件 | 验收标准 | 提交信息 |
|---|------|---------------|---------------------|----------------|
| 1 | 项目脚手架 | `pyproject.toml`、`pytest.ini`、`conftest.py`、`.gitignore` | `pytest --collect-only` 退出 0;`conftest.py` 包含 §5.1 中的 `reset_app_state` autouse fixture(在每个测试前调用 `adb shell pm clear com.blixcode.trackify`) | `chore: bootstrap project` |
| 2 | Base page | `page/base_page.py` | 能成功 import `BasePage` | `feat(page): base page with click/wait/screenshot` |
| 3 | Driver 工厂 | `utils/driver.py`、`utils/config.py` | `AppiumDriverFactory(platform="android").create()` 返回一个可用的 Appium 会话;类名避免与 `selenium.webdriver.Driver` 冲突;被 §5.1 中的 `driver` fixture 使用 | `feat(utils): appium driver factory` |
| 4 | Locator loader | `utils/locator_loader.py`、`locator/home.yaml`(骨架) | `load_locator("home", "x", "android")` 返回字符串 | `feat(utils): yaml locator loader + skeleton` |
| 5 | Home page + Locator | `page/home_page.py`、`locator/home.yaml` | `home.click_add_expense()` 在手动 Appium 会话上能跑通 | `feat(page): home page (Add Transaction shortcut)` |
| 6 | Add Transaction page + Locator | `page/add_transaction_page.py`、`locator/add_transaction.yaml` | `add_tx.add_expense(amount=100, category="Food")` 能跑通 | `feat(page): add transaction page (all 3 types)` |
| 7 | Add Transaction flow | `flow/add_transaction_flow.py` | `flow.add_expense(...)` 编排 Page 并返回新 ID | `feat(flow): add transaction business logic` |
| 8 | 第一个 BDD feature(Add Expense happy path) | `tests/features/add_transaction.feature`、`tests/step_defs/add_transaction_steps.py`、`conftest.py`(page/flow fixtures) | `pytest tests/features/add_transaction.feature -k "happy_path"` 仅收集并运行 §6.7 中的 "Add expense happy path" 场景。其他 4 个 Add Transaction 场景写好但标记为 `@skip`(或仅保留 feature 级 Background)。本场景使用的 §6.6 短语全部实现。 | `test(case): add transaction bdd (expense happy path)` |
| 8a | 首次运行 setup 基线 | `locator/onboarding.yaml`、`page/onboarding_page.py`、`flow/app_setup_flow.py`、`conftest.py`、BDD `Background` 块 | 每个业务场景都完成 `Kimbal` → `$ US Dollar` + `30000` → Bank SMS Reader 启用 + `Get Started`;没有测试路径点击 onboarding `Skip`;业务动作开始前 Home 显示 `Kimbal` 和 `$` | `feat(setup): complete required first-run configuration` |
| 8b | 其余 Add Transaction 场景 | `tests/features/add_transaction.feature`、`tests/step_defs/add_transaction_steps.py` | 解除 §6.7 中其余 **4 个场景** 的 skip(Add Income、Add Transfer、Validation、Custom Category)。实现新增的 §6.6 短语(`user selects type`、`user taps "Add new category"`、`user creates custom category`、`error message ... is shown for amount`、`no transaction appears ...`)。Custom Category 创建并选中 `baby cost`,图标/颜色任意。**全部 5 个 Add Transaction 场景通过**。 | `test(case): add transaction bdd (4 more scenarios + custom category)` |
| 8c | 事务持久化与 Home 汇总断言 | `locator/home.yaml`、`locator/transactions.yaml`、`page/base_page.py`、`page/home_page.py`、`page/transactions_page.py`、`page/add_transaction_page.py`、`flow/add_transaction_flow.py`、`utils/system_dialogs.py`、Add Transaction BDD 文件 | 每个 Add Transaction 场景都校验 Transactions 中匹配的日期/金额/类别/时间,以及 `This Month` 的收入、支出、结余和 half-up 整数百分比。Transfer 对汇总无影响。通知权限弹窗全局接受。 | `test(case): verify transaction persistence and monthly summary` |
| 9 | Transactions page + flow | `page/transactions_page.py`、`flow/transactions_flow.py`、`locator/transactions.yaml`、Add Transaction 日期/时间 Page/Flow locators、`conftest.py` | 手动测试:filter 工作;`2025-05-06 9:00 AM` 的交易被分到 `06 May 2025` 组下 | `feat(page): transactions page + flow` |
| 10 | Transactions BDD | `tests/features/transactions.feature`、`tests/step_defs/transactions_steps.py` | §6.7 中的两个 Transactions 场景都被收集并运行:按类型筛选(`@filter`)、按日期分组(`@grouping`)。实现新增的 §6.6 短语(`user filters transactions by type`、`only transactions of type ... are shown`、`transactions are grouped by date ...`)。**项目总计:5 个 Add Transaction + 2 个 Transactions = 7 个场景**。 | `test(case): transactions bdd (2 scenarios)` |
| 11 | Allure + 失败时截图 | `conftest.py`(添加 Allure metadata + `pytest_runtest_makereport` 钩子) | `pytest --alluredir=./allure-results` 产出结果;`call` 失败时,钩子把 PNG 保存到 `report/screenshots/<test_name>.png` 并附加到 Allure —— **不要**用 try/except 包裹测试体(见 §8 反模式)。钩子模板:`pytest.hookimpl(tryfirst=True, hookwrapper=True) def pytest_runtest_makereport(item, call)`,先 yield,再检查 call report。 | `feat(report): allure + screenshot on fail` |
| 12 | CI + 复盘 | `.github/workflows/ci.yml`、`docs/REFLECTION.md` | README 链接工作;所有提交干净 squash | `docs: reflection + ci + final polish` |

**可选的第 4 天任务**(时间允许时):
- **任务 13**:AI Triage —— 把每个测试的**首个**失败 pytest 阶段分类为 {**Locator**、**App Bug**、**Env**、**Script**、**Data**、**Unknown**} 之一。判定仅为顾问式:它**绝不能**修改 pytest 结果、隐藏原始 traceback,或被当作已确认的根因。

  **结果契约**(`TriageResult`,冻结 dataclass):

  | 字段 | 类型 | 规则 |
  |-------|------|------|
  | `category` | enum string | `Locator`、`App Bug`、`Env`、`Script`、`Data`、`Unknown` 之一 |
  | `confidence` | float | 截断到 `0.0..1.0` |
  | `reasoning` | string | 简洁,最长 500 字符;绝不包含密钥或完整 traceback |
  | `next_action` | string | 具体的工程师动作,最长 500 字符 |
  | `classifier` | string | `local`、`llm` 或 `disabled` |
  | `matched_signatures` | tuple/list | 仅本地特征 ID;LLM/disabled 结果下为空 |

  Allure JSON 附件必须包含上述字段,外加 `schema_version`、`test_name` 与失败的 `phase`。序列化使用 `dataclasses.asdict()`;不序列化原始异常对象。

  **架构(2 个阶段)**:

  1. **本地加权启发式(始终启用)** —— 在模块导入时编译一次 `LOCAL_SIGNATURES`,然后匹配归一化的 `error_msg + traceback`。每个特征有各自的置信度。选择最高置信度的匹配;并列时按 `Env > Locator > Data > App Bug > Script`。置信度 `>= 0.70` 时直接返回。不要把弱匹配叠加:多个泛型字符串不能拼出高置信度。该阶段不进行任何文件、环境或网络 I/O。
  2. **Claude 兼容回退(显式 opt-in)** —— 仅在本地置信度低于 `0.70` 且 `AI_TRIAGE_LLM_ENABLED=1`、`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL` 都存在时运行。`ANTHROPIC_BASE_URL` 可选,默认 `https://api.anthropic.com`;形如 `https://api.minimaxi.com/anthropic` 的网关路径会在追加 `/v1/messages` 之前被保留。通过 Python 标准库(或测试中的可注入 callable)使用 Anthropic Messages 协议;不要在 §1 之外添加 SDK 依赖。最多一次请求,无重试,总超时 5 秒。任何超时、HTTP 错误、配置缺失、JSON 格式错误、未知类别或非法字段都返回 `Unknown / 0.0`,且不抛异常。

  **必需的本地特征**(`re.IGNORECASE`;`re.DOTALL` 仅用于受限上下文模式):

  | 类别 | 签名 ID / 正则意图 | 置信度 | 默认 `next_action` |
  |----------|-----------------------------|------------|-----------------------|
  | **Env** | `connection_refused`:`ConnectionRefused(?:Error)?`、`ECONNREFUSED`,或 `Failed to establish a new connection` 出现在 `4723`/Appium 附近 | `0.98` | 验证 Appium 监听在 `:4723`;检查 `appium.log` |
  | **Env** | `device_unavailable`:`adb.*(?:not found\|No such file)`、`device (?:offline\|unauthorized)`,或 `no (?:Android )?devices?` | `0.95` | 运行 `adb devices`;重新连接或启动目标设备 |
  | **Locator** | `element_missing`:`NoSuchElement(?:Exception\|Error)` 或 `Unable to locate element` | `0.98` | 检查命中的 locator YAML 条目与当前 Appium page source |
  | **Locator** | `locator_timeout`:在同时包含 `find_element`、`locator`、`accessibility_id` 或 `xpath`(任一顺序)的受限上下文中出现 `TimeoutException` | `0.85` | 确认页面状态,若元素变更则更新 locator/fallback |
  | **Data** | `test_data_missing`:在 `test_data`/`fixture`/`yaml` 附近出现 `KeyError`,或在 `missing`、`required`、`not found` 附近出现 test-data/YAML 文本 | `0.90` | 校验 `data/` 中必需的键与行值 |
  | **Data** | `database_corrupt`:`HiveError` 或在 `data`/`database` 附近出现 corruption 文本 | `0.80` | 重置本地 app 数据库并验证 seed/setup 路径 |
  | **App Bug** | `app_crash`:`ANR`、`App crashed`、`not responding`、`has stopped`,或 `java\.lang\.` | `0.98` | 在相同 build/device 上手动复现,如可复现则提交 app 缺陷 |
  | **App Bug** | `business_mismatch`:在 `expected` 与 `actual`/`got`/`displayed`/`missing` 附近出现 `validation`/`summary`/`saved transaction` | `0.82` | 对比展示状态与需求,并手动复现 |
  | **App Bug** | `element_disabled`:`element.*not enabled` | `0.60` | 模糊;收集页面状态,允许 LLM/Unknown,而不是直接短路 |
  | **Script** | `python_structure`:`ImportError`、`ModuleNotFoundError`、`NameError`、`SyntaxError`,或 `IndentationError` | `0.98` | 直接修复 Python/导入错误 |
  | **Script** | `python_contract`:`AttributeError` 或 `TypeError` | `0.90` | 阅读顶层项目栈帧,修正 API/类型用法 |
  | **Script** | `generic_assertion`:裸 `AssertionError` | `0.40` | 自身模糊;没有更强上下文时不应归类为 Script |

  **输入归一化与隐私**:
  - 输入键:`error_msg`、`traceback`,可选 `test_name`、`phase`、`screenshot_path`。出于命令行/向后兼容考虑,缺失的 `test_name` 默认 `unknown`,缺失的 `phase` 默认 `call`。
  - 在送给 LLM 之前,`error_msg` 限制为 2,000 字符,traceback 限制为最后 12,000 字符。
  - 在附加或网络使用前,对授权头、API key/token、URL query 字符串做脱敏。
  - 多模态输入超出范围。仅发送 `screenshot_available` 与截图 basename;绝不发送图像字节或绝对本地路径。
  - 将异常文本与 traceback 视为不可信的引用数据。系统提示明确要求忽略嵌入在失败文本中的指令,且不暴露任何工具。
  - 仅请求一个 JSON 对象(`temperature=0`,小且受限的输出)。校验类别白名单、数值置信度、非空受限字符串,并忽略未知响应字段。

  **pytest / Allure 集成**:
  - 在 `outcome = yield` 之后、报告创建之后,扩展 Task 11 的 `pytest_runtest_makereport` 钩子。
  - 对 `setup`、`call`、`teardown` 失败都做归类;环境失败常发生在 setup。使用 `item.stash` 键,使仅首个失败阶段被归类一次。
  - 对于 `call` 阶段失败,先采集 Task 11 的截图,并把返回路径传给 triage。其他阶段使用 `screenshot_path=None`。
  - 即使是 `Unknown`,也要附加 `AI Triage`,使用 `allure.attachment_type.JSON`,前提是 Allure 生命周期已激活。
  - 在失败阶段结束后,通过 pytest 的 `terminalreporter.write_line()` 输出 `[AI Triage] <Category> (<NN%>): <reasoning>`,以保证捕获设置不会隐藏它。仅在没有 terminal reporter 时回退到 `print()`。
  - Triage 失败会被捕获并转换为 `Unknown`;报告代码绝不能取代原始测试失败。

  **运行展示**:
  - 通过的测试不会触发 triage 调用或附件。仅对首个失败阶段进行分类。
  - `classifier=local` 证明在没有网络 I/O 的情况下返回了确定性特征;`classifier=llm` 表示尝试了一次兼容模型调用;`classifier=disabled` 表示由于缺少必要的 opt-in 配置,模糊证据无法使用 LLM。
  - 终端行是快速信号,Allure `AI Triage` JSON 是可审计的记录。两者都是顾问式,必须与原始 traceback 与截图一起阅读。
  - 真实 key 只属于被忽略的 `.env`;`.env.example` 只放占位符。项目从不自动加载 `.env`,并且不得为了网关调用成功而关闭证书校验。
  - 运行时配置与验证流程记录在 [`docs/AI_TRIAGE.md`](AI_TRIAGE.md)。

  **单元测试隔离**:
  - 添加 `unit` marker。将 `reset_app_state` 重构为通过 `request.getfixturevalue("driver")` 懒获取 driver;对 `@pytest.mark.unit` 测试立即 yield,使纯 triage 测试不会启动 Appium 或调用 `adb pm clear`。
  - 注入 LLM callable。一个 spy/fake 必须证明,本地 `Locator` 命中时零 LLM 调用;不要在生产代码里留 `print('local hit')` 这种插桩。

  **涉及文件**:`ai/__init__.py`、`ai/triage.py`、`tests/unit/test_triage.py`、`conftest.py`、`pytest.ini`。

  **验收标准**:
  - `uv run python -c "from ai.triage import triage_failure; print(triage_failure({'error_msg': 'NoSuchElementException: ...', 'traceback': ''}).category)"` 输出 `Locator`。
  - `uv run pytest -m unit tests/unit/test_triage.py -q` 在没有运行 Appium server 或连接设备的情况下通过。
  - 单元用例覆盖每个类别、优先级、裸 `AssertionError -> Unknown`(无 LLM)、配置缺失、超时/非法 LLM 输出、置信度截断、脱敏、以及本地命中时零网络调用。
  - 受控的 setup 或 call 失败恰好产生一份 `AI Triage` JSON 附件(满足要求的 schema)和一行可见的控制台输出;原始 pytest 失败保持不变。
  - 缺失 `ANTHROPIC_API_KEY` 或 LLM 被禁用时,返回 `Unknown`、`confidence=0.0`、`classifier=disabled`,无异常,无网络调用。
  - 本地分类无 I/O,且具有确定性。可以出于信息目的对运行时进行基准测试,但不需要硬件相关的 `<1 ms` 断言。

  **PoC 范围之外**:
  - 多模态截图分析 / Claude Vision。
  - 基于工程师修正的自学习。
  - 跨运行缓存或 flaky-test 历史。
  - 自动重试、失败抑制或缺陷提交。
  - 对非英文错误信息分类。

  **提交信息**:`feat(ai): failure triage with local heuristic + LLM fallback`

**可选的第 5 天任务**(挑战后扩展):
- **任务 14**:Excel → `.feature` 同步引擎 —— `data/test_cases.xlsx` 仅对由 `scenario_id` 标识的托管 Scenario 块是权威的;Feature 头与 Background 块仍由代码所有。引擎按 Module 路由行,先完整校验整个 workbook 再写入,仅通过 backup/replace/rollback 事务应用 `added` / `modified` / 显式 `deprecated` 块,并保证未触及的托管块保持字节一致。`data/test_cases_template.xlsx` 作为引导登记册。完整契约见 §11。提交信息:`feat(sync): excel-to-feature sync engine PoC`。

---

## 8. 反模式(不要做)

| 反模式 | 不好之处 | 正确做法 |
|--------------|--------------|----------------|
| 在测试代码中写 `driver.find_element(...)` | 让测试与裸 Appium 耦合 | 始终通过 `BasePage` / Page Object |
| 在 Page 中使用 `time.sleep(2)` | 在慢设备上不稳定 | 使用 `wait_for(...)` 配显式条件 |
| 在 Python 中写内联 XPath | 难以维护 | 移到 `locator/*.yaml` |
| 在另一个 Page 内 `from page.X import Y` | 紧耦合 | Page 之间不应互相依赖 |
| 在 BDD step 中使用 if/else 分支 | 难以调试 | 拆成多个场景 |
| 在 Flow 里直接调用 Appium | 跳过 Page 层 | Flow → Page → Driver |
| 使用 `pytest.fixture` 时不考虑 scope/cleanup | 资源泄漏 | 显式 `autouse=False` + teardown |
| 一次性写出整个自动化 | 无法评审/调试 | 一次任务一个提交,见 §7 |
| 添加“额外”特性(Docker、MyPy、Black) | 范围蔓延 | 仅使用 §1 技术栈 |

---

## 9. 参考文档

Codex 必须在开始 Task 1 之前阅读以下文档:

1. `README.md` —— 范围、AI 使用规则、面对评估者的故事(最高层)
2. `docs/Feature_Inventory.md` —— 存在哪些页面 + 哪两个在范围内(共 7 个 BDD 用例)
3. `docs/TECHNICAL_SPEC.md` —— 本文件(如何构建)

Task 8 之后(第一个 BDD 场景通过),Codex **应该**重新阅读 `README.md` 的“Test Coverage”章节和 `Feature_Inventory.md` §四,在继续 Task 8b / 10 之前确认范围一致。

### 内部交叉引用(TECHNICAL_SPEC.md 内部)

| 如果你在编写… | 必须遵守… |
|---------------------|----------------|
| `.feature` 文件(Task 8 / 8b / 10) | §6.5 风格指南 + §6.6 step 词汇 + §6.7 场景清单(精确标题) |
| `step_defs/*_steps.py` | §6.6 短语(与 `parsers.parse` 一一对应)+ §6.3 复用规则 |
| `page/*_page.py` | §3 规范 + §4 locator YAML 格式 + §4.3 优先级链 |
| `flow/*_flow.py` | §5 分层规则(禁止 `utils.driver` import;只能调用 Page) |
| `conftest.py` | §5.1 fixture 接线模板(driver + reset_app_state + 每页 fixture) |
| Locator yaml | §4.1 格式 + §4.1 完整模板 + §4.2 回退 loader |

---

## 10. Git 与提交规范

- **每个任务一次提交** —— 不要批量
- **提交信息格式**:`<type>(<scope>): <subject>`
  - 类型:`chore`、`feat`、`test`、`docs`、`fix`、`refactor`
  - scope:`page`、`flow`、`utils`、`case`、`report`、`ai`
- **每次提交前**,运行 `pytest --collect-only` 确保没有导入错误
- **参考**:每条提交信息应能映射到 §7 的一行

### Squash 策略(已修订)

> ⚠️ **不要把 13 个任务提交 squash 成一个。** 每个提交都是一个可评审单元;squash 会破坏“何时添加了什么、为什么”的轨迹。

当用户/评估者想要干净的主分支历史时,使用 **交互式 rebase 仅 squash 琐碎的提交**(例如 8 和 8b 可以合并,因为它们触及相同文件并代表同一个 feature):

```bash
# 可选:把 8 和 8b 合并为单个 "add transaction bdd" 提交
git rebase -i HEAD~3            # 把 8b 标记为 "squash"
# 保留 1-7 和 9-13 为独立提交 —— 它们是独立的 feature
```

**保持独立的提交**(不要 squash):
- 任务 1(脚手架)—— 奠定基础
- 任务 11(Allure + 截图)—— 正交关注点
- 任务 12(CI + 复盘)—— 最终打磨
- 任何在原 feature 提交之后落地的 `fix:` 提交

**默认**:保留 13 个提交不变。仅在用户要求时 squash。

---

## 11. 活文档:Excel → Feature 同步(第 5 天扩展)

> **本节对挑战是可选的。** Tasks 1-12 先完成。Task 14 作为单独的 `feat(sync): ...` 提交。箭头刻意单向:PoC 永远不把测试结果或场景编辑从 `.feature` 写回 Excel。

### 11.1 所有权模型

同步契约是混合的,而不是“Excel 拥有每一个字节”:

| 产物区域 | 所有者 | 同步行为 |
|-----------------|-------|---------------|
| Excel 中托管用例的行 | Excel | 场景 metadata、tags、When/Then 步骤、生命周期状态的源 |
| 以 `# scenario_id:` 开头的托管 Scenario 块 | Excel | 按 ID 添加、替换或显式弃用 |
| `Feature:` 行、文件注释、`Background:` 块 | 代码 / 评审者 | PoC 永不生成或重写 |
| step 定义、Pages、Flows、locators | 代码 | 同步永不修改 |
| `Last Run Result` 与评审 metadata | QA / 未来 CI | 对 PoC 只读;永不写回 |

这种边界把公共首次运行 setup 保留在代码评审的 Background 中,同时允许 QA 维护单个场景的动作与断言。“Excel 事实来源”意味着**仅对托管 Scenario 块而言是事实来源**。

### 11.2 规范托管块与场景 ID

Task 14 必须先使用 `data/test_cases_template.xlsx` 中已有的 ID,为所有 7 个现有场景添加 ID。托管块的标准顺序为:

```gherkin
# scenario_id: TC_ADD_TX_001
# introduced_in: 1.0.0
# platforms: android
@smoke @p0
Scenario: Add expense happy path
  When user taps "Add Expense"
  And user enters amount "100"
  ...
```

`# deprecated_in: <version>` 是可选的,仅在填了值时出现在 `# introduced_in:` 之后。因此有**三条强制 metadata 注释**(`scenario_id`、`introduced_in`、`platforms`),以及一条可选的弃用注释;tags 不是注释行。

**当前清单的 ID 映射**:

| 场景 | ID | Module |
|----------|----|--------|
| Add expense happy path | `TC_ADD_TX_001` | `add_transaction` |
| Add income happy path | `TC_ADD_TX_002` | `add_transaction` |
| Add transfer happy path | `TC_ADD_TX_003` | `add_transaction` |
| Validation — empty amount shows error and does not save | `TC_ADD_TX_004` | `add_transaction` |
| Add expense with new custom category created in flow | `TC_ADD_TX_005` | `add_transaction` |
| Filter transactions by type shows only matching type | `TC_TXN_001` | `transactions` |
| Transactions grouped by date with section headers | `TC_TXN_002` | `transactions` |

**规则**:
- ID 格式:`^TC_[A-Z][A-Z0-9_]*_[0-9]{3}$`。
- ID 必须在 workbook 内以及跨所有 feature 文件中唯一。重复 ID 在任何写入前都是硬错误。
- `Module` 使用白名单,而不是路径:`add_transaction -> tests/features/add_transaction.feature`,`transactions -> tests/features/transactions.feature`。未知值是错误;不要把不可信的 Module 文本拼接到路径中。
- 托管块从精确以 `# scenario_id:` 开头的行开始,在下一个托管块或 EOF 之前结束。第一个托管块之前的内容归代码所有。
- Tags 在 metadata 之后、`Scenario:` 之前渲染。Excel 中逗号分隔的 tags 变成空格分隔的 Gherkin tags(`smoke,p0 -> @smoke @p0`)。优先级作为一种规范 tag 注入并去重。
- PoC 仅支持 `Scenario:`。`Scenario Outline` / `Examples` 同步不在范围内。
- 初始七场景迁移之后,没有 ID 的 feature 场景是校验错误,而不是隐式的添加/删除候选。

### 11.3 Excel Schema(`data/test_cases_template.xlsx`)

实际模板包含 16 列:11 个 L1 登记列和 5 个 L2 自动化列。每个表头都是必需的。下文中的“可空”或“推荐”只适用于行值,不适用于表头是否存在。

| 列 | 行值 | 用途 | PoC 行为 |
|--------|-----------|---------|--------------|
| **Test Case ID** | 必填 | 稳定锚点 | `# scenario_id:` |
| **Module** | 必填 | 安全路由 | 校验白名单;选择一个 feature 文件 |
| **Scenario Title** | 必填 | 人类可读名 | `Scenario:` 文本 |
| **Priority** | 必填:`P0`、`P1`、`P2` | 选择 | 规范化为一个小写优先级 tag |
| **App Version Introduced** | 必填 | 版本选择 | `# introduced_in:` |
| **App Version Deprecated** | 可空;`deprecated` 时必填 | 生命周期 | 可选 `# deprecated_in:` |
| **Platform** | 必填:`android`、`ios` 或 `both` | 平台选择 | `both` 在 `# platforms:` 中渲染为 `android, ios` |
| **Automation Status** | 必填枚举 | 生命周期门控 | 见下方状态规则 |
| **Author** | 必填登记 metadata | 所有权 | 校验非空;不渲染 |
| **Last Reviewed Date** | 必填 ISO 日期 | 可审计性 | 校验;不渲染 |
| **Last Run Result** | 必填登记 metadata | 执行可见性 | PoC 只读/忽略 |
| **Tags** | 推荐 | pytest markers | 逗号分隔,无前导 `@`;渲染时按优先级去重 |
| **Pre-conditions** | 推荐 metadata | 手动测试上下文 | PoC 不渲染;文件 Background 仍归代码所有 |
| **Test Steps** | `automated` 时必填 | 场景动作 | 每个换行一个词汇短语;首行渲染为 `When`,其余渲染为 `And` |
| **Expected Result** | `automated` 时必填 | 场景断言 | 每个换行一个词汇短语;首行渲染为 `Then`,其余渲染为 `And` |
| **Estimated Runtime (s)** | 推荐正整数 | 规划 | 存在时校验;不渲染 |

不要按分号拆分步骤:备注和消息中可能合理包含分号。Excel 单元格使用换行分隔的短语,**不**带 `Given`/`When`/`Then`/`And` 关键字;渲染器会确定性地加上关键字和缩进。

**Automation Status 规则**:
- `manual` / `candidate`:当没有托管 feature 块存在时忽略。如果该 ID 已经在 feature 中,直接报错并要求显式过渡到 `deprecated`;绝不静默删除可执行覆盖。
- `automated`:添加或更新路由到的托管块。
- `deprecated`:要求 `App Version Deprecated` 与已有的托管块;弃用一个从未生成过的 ID 是错误。保留 metadata 注释的可解析性,但在确定性的 `DEPRECATED BEGIN/END <ID>` 标记之间把 tags、Scenario 行、body 注释掉。不要从缺失的行推断弃用。
- workbook 中缺失的托管 feature ID 是硬错误。缺失的 Excel 行绝不意味着删除。

规范的弃用形式:

```gherkin
# scenario_id: TC_ADD_TX_005
# introduced_in: 1.0.0
# deprecated_in: 2.0.0
# platforms: android
# DEPRECATED BEGIN TC_ADD_TX_005
# @p1 @custom_category
# Scenario: Add expense with new custom category created in flow
#   When ...
#   Then ...
# DEPRECATED END TC_ADD_TX_005
```

**引导数据对齐(首次应用前的强制步骤)**:
- 把 `data/test_cases_template.xlsx` 复制为 `data/test_cases.xlsx`;工作登记册是 Task 14 的输入。
- 在生成 feature 前,先更新全部 7 行以与 §6.7 完全一致。原模板是早期草稿:它包含 `Coffee` 而不是 `baby cost`、旧的复合 `user adds ...` 短语、缺失的 tag/date 动作,以及不完整的持久化/月度汇总断言。校正后的基线使用 `Platform=both`,因为全部 7 个场景都已经在 Android 与 iOS 模拟器上通过。
- 保留模板作为可复用示例,但也把它更新为同一份校正后的七行基线,以便新的副本不会重新引入偏差。

### 11.4 同步引擎接口(`scripts/sync_engine.py`)

已实现的引擎通过 Module 白名单路由行,并只更新对应的托管 feature 块。

安全的运行模式:

```bash
# 默认:仅校验 + diff;不写入。当存在 drift 时退出码 1。
uv run python scripts/sync_engine.py --check

# 完整校验后显式变更
uv run python scripts/sync_engine.py --apply

# 应用,然后仅执行新增/修改的活动场景
uv run python scripts/sync_engine.py --apply --run-changed

# 跨设备健康门控:检查、应用,然后把变更复制到所有设备
./scripts/run_changed_matrix.sh

# 仅本地监听;变更仍需要 --apply
uv run python scripts/sync_engine.py --watch --apply

# 用于测试/本地实验的可选非默认登记册路径
uv run python scripts/sync_engine.py --check --input /path/to/test_cases.xlsx
```

未提供 `--check` 或 `--apply` 时,默认使用 `--check`。`--check`、`--apply` 与机器可读的 `--list-changed` 互斥。`--run-changed` 需要 `--apply`;它在成功收集后,运行新增/修改活动场景的精确 pytest node ID。`scripts/run_changed_matrix.sh` 消费 `--list-changed`,预览设备并应用一次变化,再由矩阵 Runner 负责检查/启动 Appium，并在矩阵 `replicate` 模式下运行精确的变更子集,使每个被选设备都校验每个变更用例。`--watch` 在没有 `--apply` 时仅报告 drift。Diff 类别为 `added`、`modified`、`deprecated`、`unchanged` 和 `errors`;没有隐式的 `deleted` 类别。

退出码:
- `0`:合法且无 drift(`--check`),或应用成功且写入后收集通过。
- `1`:合法但 `--check` 模式下存在 drift。
- `2`:schema、重复、路由、解析、I/O、锁、渲染或写入后收集错误。

### 11.5 校验、事务安全与回滚

引擎必须在首次写入前完成所有 workbook 与 feature 校验:

- 必需的表头与必需的行值;
- ID 格式/唯一性与 feature ID 唯一性;
- 允许的 Module、status、priority、platform 与 tag 语法;
- 对 `automated` 行,Test Steps / Expected Result 非空且按换行分隔;
- 每个 `automated`/`deprecated` 行恰好路由到一个 feature;
- workbook 中不缺失任何托管 feature ID;
- 初始 ID 迁移之后没有未托管的 `Scenario:`;
- 同一 module 内场景标题不重复;
- UTF-8 feature 解码与每个文件仅检测一种换行风格。

Apply 是一次尽力而为的跨所有受影响 feature 文件的事务(Python/OS 无法在一次操作中原子地替换多个文件):

1. 原子地获取 `data/.backup/sync.lock`;存储 PID/时间戳,如果存在并发 apply/watch 写入器则失败。仅在确认 PID 不再运行后,手动移除陈旧的锁。
2. 在内存中完整渲染每个目标文件。通过精确的字符串切片,保留原始 UTF-8 编码、换行风格、代码拥有的前缀,以及每一个未变更的托管块。
3. 在**每次**变更型 apply 之前,把带微秒时间戳的备份写到 `data/.backup/<feature>.<YYYYMMDDTHHMMSSffffff>.bak`。绝不重用“每天一次”的备份名。
4. 把每个渲染后的文件写到同一目录下的临时文件,flush 后使用 `os.replace()`;不允许直接对目标执行 `Path.write_text()`。
5. 在所有替换完成后,运行一次 `[sys.executable, "-m", "pytest", "--collect-only", "-q"]`。
6. 如果任何替换或收集失败,从该次运行的备份还原所有受影响文件,报告原始错误与回滚状态,然后以 `2` 退出。
7. 始终在 `finally` 中删除临时文件并释放锁。在多个 `os.replace()` 调用之间发生的进程被杀/断电日志不在范围内。

引擎永不编辑任一 workbook。`data/.backup/` 仍被 gitignore。Watch 模式使用 `watchdog`,debounce 5 秒,调用相同的已校验事务;它不是一条独立的写路径。

**字节一致保证**意味着,在成功 apply 前后,每个 `unchanged` 托管块的编码字节切片具有相同的 SHA-256。它并不意味着修改过的块或它周围必要的分隔符保持不变。

### 11.6 测试与验收标准

**涉及文件**:`scripts/sync_engine.py`、`scripts/run_changed_matrix.sh`、`scripts/run_device_matrix.py`、`data/test_cases.xlsx`、`data/test_cases_template.xlsx`、两个 feature 文件(初始 ID/metadata)、`tests/unit/test_sync_engine.py`、`unit_tests/test_run_device_matrix.py`、`.github/workflows/ci.yml`,以及仅在 Task 13 的 `unit` 隔离 marker 尚未存在时的 `conftest.py` / `pytest.ini`。

所有同步测试都使用临时 workbook/feature 副本。它们**绝不能**修改仓库的 feature 文件或登记册。

验收标准:

- 解析校正后的登记册,精确返回 7 条 `automated` 行,路由为 5 条 `add_transaction` 与 2 条 `transactions` 用例。
- 初始 Task 14 feature 文件包含 §11.2 中的 7 个唯一 ID,仍能收集到同样的 7 个 BDD 场景。
- 在已提交的状态上,`uv run python scripts/sync_engine.py --check` 退出 `0` 且零写入。
- 在临时副本中修改 Excel 的某个金额/标题/步骤,会精确报告正确 module 中的 1 个 `modified` 块;另一个 feature 文件保持字节一致。
- 运行两次 `--apply` 是幂等的:第二次运行报告无 drift,两个 feature 文件的哈希保持不变。
- 单元测试覆盖重复 ID(Excel 内与跨 feature)、未知 Module、非法枚举/必填字段、tag 规范化、状态转换、缺失的 workbook ID、不支持的 Scenario Outline,以及换行保留。
- 强制产生的写入后收集失败会还原所有受影响文件,且不留下锁/临时文件。
- SHA-256 断言证明,在相邻的 add/modify/deprecate 操作之后,未触及的托管块字节一致。
- Workbook 哈希在所有模式下都保持不变,包括 `--apply` 与 `--watch`。
- `--apply --run-changed` 仅执行新增/修改的活动场景,报告它们的 ID 与 Allure 路径,并在运行失败时打印一条精确的重试命令以及代码/locator 调试范围。
- `scripts/run_changed_matrix.sh` 仅在无可运行的 drift 或每个变更用例在每个被选设备上都通过时才返回 `0`;矩阵汇总保留变更种类、稳定用例 ID、环境、设备、OS、UDID 与每个设备的健康状况。
- Task 14 落地后,CI 的 `validate` 任务在 pytest 收集之前运行 `uv run python scripts/sync_engine.py --check`。
- 完整验证通过:同步单元测试、7 个 BDD 场景被收集,以及 `git diff --check` 干净。

### 11.7 PoC 范围之外

- 双向同步或将 `Last Run Result` 写回 Excel。
- 基于缺失行的自动删除。
- 自动创建 PR/分支或由脚本提交。
- 多 workbook 合并与冲突解决。
- Scenario Outline / Examples 生成。
- LLM 生成行提议(见 `docs/SCALING.md` §4)。
- 在 CI 中监听文件;`--watch` 仅用于本地开发。

### 11.8 参考

更广的 Q1-Q6 路线图、版本感知回归与文档驱动测试上下文,见 [`docs/SCALING.md`](SCALING.md)。在 Task 14 实施时阅读;它不阻塞 Tasks 1-12。

---

*TECHNICAL_SPEC.md 完 —— 在编写任何代码之前,先通读本文档。*
