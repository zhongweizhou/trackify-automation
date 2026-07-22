# Trackify 自動化 — 技術規範(TECHNICAL_SPEC.md)

> **受眾**:Codex / Claude Code(實施者)
> **目的**:定義如何建構 `README.md` 所描述的內容。
> **不要在此修改範圍** —— 範圍由 `README.md` 與 `Feature_Inventory.md` 定義。
> **本文件定義 HOW。**

---

## 1. 技術棧(鎖定版本)

| 元件 | 版本 | 原因 |
|-----------|---------|-----|
| Python | 3.11+ | 型別提示 + async/await |
| pytest | 8.x | BDD runner |
| pytest-bdd | 7.x | Gherkin → pytest steps |
| Appium | 3.x | 跨平台行動驅動 |
| Appium UiAutomator2 Driver | latest | Android 驅動 |
| Appium XCUITest Driver | latest | iOS(僅延伸) |
| Selenium-Python | 4.x | Appium 底層相依 |
| allure-pytest | 2.x | Allure 報告 |
| pyyaml | 6.x | Locator YAML 解析 |
| openpyxl | 3.x | Excel 同步引擎(Task 14) |
| watchdog | 4.x | 同步觸發的檔案系統事件(Task 14) |
| uv | latest | 快速 Python 套件管理 |
| Allure CLI | latest | 報告渲染器 |

> ❌ **不要新增**:Poetry、pipenv、conda、Docker、Flake8、Black、MyPy、Pylint、pre-commit 鉤子、**gherkin(Python 函式庫)**(同步 PoC 用正則,見 §11)。上表以外的任何內容都屬於範圍蔓延。

---

## 2. 目錄結構(不可變)

```
trackify-automation/
├── README.md                        # 公開範圍(給評估者)
├── TECHNICAL_SPEC.md                # 本檔(給 Codex)
├── pyproject.toml                   # uv 管理的 Python 相依
├── pytest.ini                       # BDD + markers 設定
├── conftest.py                      # 全域 fixtures(appium driver、db reset)
│
├── docs/
│   ├── Feature_Inventory.md         # 第 1 天手動探索
│   ├── DESIGN.md                    # 架構理由
│   ├── TECHNICAL_SPEC.md            # 本檔
│   ├── SCALING.md                   # Q1-Q6 策略路線圖(長期、非阻塞)
│   └── REFLECTION.md                # 覆盤(第 5 天)
│
├── app/                             # 不提交
│   ├── app-release.apk
│   └── Runner.app
│
├── tests/
│   ├── features/                    # Gherkin 檔(BDD)
│   │   ├── add_transaction.feature
│   │   └── transactions.feature
│   ├── step_defs/                   # pytest-bdd step 實作
│   │   ├── __init__.py
│   │   ├── add_transaction_steps.py
│   │   └── transactions_steps.py
│   └── __init__.py
│
├── locator/                         # YAML 檔(每頁一個)
│   ├── onboarding.yaml
│   ├── home.yaml
│   ├── add_transaction.yaml
│   └── transactions.yaml
│
├── page/                            # Page Object 模式
│   ├── __init__.py
│   ├── base_page.py                 # 抽象基底 —— 所有 Page 都繼承
│   ├── onboarding_page.py
│   ├── home_page.py
│   ├── add_transaction_page.py
│   └── transactions_page.py
│
├── flow/                            # 業務邏輯(呼叫 Page)
│   ├── __init__.py
│   ├── app_setup_flow.py
│   ├── add_transaction_flow.py
│   └── transactions_flow.py
│
├── utils/                           # 橫切工具
│   ├── __init__.py
│   ├── driver.py                    # Appium driver 工廠
│   ├── locator_loader.py            # YAML → dict
│   ├── system_dialogs.py            # 定向的 Android 權限處理
│   └── config.py                    # 自 pytest.ini 讀取 platform / device
│
├── ai/                              # AI 輔助模組(第 4 天)
│   ├── __init__.py
│   ├── gen_cases.py                 # LLM 起草的 BDD 案例構想
│   └── triage.py                    # 基於 LLM 的失敗分類器
│
├── data/
│   ├── test_cases.xlsx              # 手動案例登記冊(Task 14 同步來源)
│   ├── test_cases_template.xlsx     # 可重用的校正後七案例基準
│   └── .backup/                     # sync_engine.py 每次寫入前自動產生
│
├── scripts/
│   └── sync_engine.py               # Excel → .feature 檢查/套用(Task 14 PoC)
│
├── report/
│   ├── allure-results/              # 每次執行產生
│   ├── screenshots/                 # 失敗時產生
│
└── assets/
    └── run_demo.mp4                 # 一次成功執行的錄影
```

**規則**:
- ❌ 不要把測試檔放在專案根目錄。
- ❌ 不要把 Page / Flow / Driver 程式碼放在 `tests/`。
- ❌ 不要硬編碼路徑;使用 `pathlib.Path(__file__).parent`。

---

## 3. 編碼規範(嚴格)

### 3.1 型別提示(強制)

```python
# ✅ GOOD
def click_add_expense(self) -> None:
    self._driver.click(self._loc("add_expense_button"))

# ❌ BAD
def click_add_expense(self):
    self._driver.click(self._loc("add_expense_button"))
```

所有 public 方法必須具備:
- 參數型別
- 回傳型別

### 3.2 文件字串(Google 風格,public 類別/函式強制)

```python
def add_expense(amount: float, category: str, note: str = "") -> str:
    """新增一筆支出交易,並回傳新交易的 ID。

    Args:
        amount: 交易金額(正數;符號由型別隱含)。
        category: 類別名(必須已在設定中存在)。
        note: 選用自由文字備註。

    Returns:
        新建立交易的 ID。
    """
    ...
```

### 3.3 命名

| 元素 | 規範 | 範例 |
|---------|------------|---------|
| 類別 | PascalCase | `AddTransactionPage` |
| 函式 / 方法 | snake_case | `add_expense_transaction` |
| 常數 | UPPER_SNAKE | `DEFAULT_TIMEOUT = 10` |
| 私有(內部) | `_leading_underscore` | `_driver` |
| 檔案 | snake_case.py | `add_transaction_page.py` |
| YAML 鍵 | snake_case | `add_expense_button:` |

### 3.4 Imports

```python
# ✅ GOOD — 三組,標準庫在前,組間空行
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
# ❌ BAD — local 排在 third-party 之前,沒有空行,星號匯入
from page.base_page import BasePage
from appium.webdriver import *
import pytest
from utils.locator_loader import load_locator
```

**為什麼順序很重要**:
- isort / ruff 自動修復會把亂序 import 視為錯誤 —— 從一開始就手動保持順序可避免日後大規模整理。
- 星號匯入(`from X import *`)會讓 grep 無法定位,並隱藏未使用 import 的提示。

---

## 4. Locator 策略(僅 YAML)

### 4.1 格式

`locator/<page>.yaml` —— 每頁一個檔:

```yaml
# locator/add_transaction.yaml

add_expense_button:
  description: "Home 頁面上開啟 Add Transaction 互動視窗的按鈕"
  android:
    accessibility_id: "Add Expense"
  ios:
    accessibility_id: "Add Expense"

amount_input:
  description: "交易金額的數字輸入框"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

transaction_type_toggle:
  description: "在 Expense / Income / Transfer 之間切換的 Tabs"
  android:
    xpath: "//*[@resource-id='com.blixcode.trackify:id/transaction_type_toggle']"
  ios:
    predicate: "type == 'XCUIElementTypeOther' AND name == 'Transaction Type'"
```

**完整 yaml 範本**(作為每個新頁面的起點):

```yaml
# locator/add_transaction.yaml — 參考骨架

# ---- 類型切換(Expense / Income / Transfer) ----
type_toggle_expense:
  description: "選擇 Expense 類型的 Tab"
  android:
    accessibility_id: "Expense"
  ios:
    accessibility_id: "Expense"

type_toggle_income:
  description: "選擇 Income 類型的 Tab"
  android:
    accessibility_id: "Income"
  ios:
    accessibility_id: "Income"

type_toggle_transfer:
  description: "選擇 Transfer 類型的 Tab"
  android:
    accessibility_id: "Transfer"
  ios:
    accessibility_id: "Transfer"

# ---- 金額 ----
amount_input:
  description: "交易金額數字輸入框(支援小數)"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

# ---- 類別 ----
category_dropdown:
  description: "選擇現有類別的下拉選單"
  android:
    accessibility_id: "Category"
  ios:
    accessibility_id: "Category"

category_option_food:
  description: "下拉清單中標為 'Food' 的類別選項"
  android:
    xpath: "//*[contains(@content-desc, 'Food')]"
  ios:
    predicate: "label == 'Food'"

new_category_button:
  description: "橫向類別清單最右端的 New 圖塊"
  android:
    accessibility_id: "New"
  ios:
    accessibility_id: "New"

manage_categories_title:
  description: "由 New 圖塊開啟的 Manage Categories 頁面"
  android:
    accessibility_id: "Manage Categories"
  ios:
    accessibility_id: "Manage Categories"

add_category_button:
  description: "開啟 New Category 表單"
  android:
    accessibility_id: "Add Category"
  ios:
    accessibility_id: "Add Category"

custom_category_name_input:
  description: "自訂類別名的文字輸入"
  android:
    xpath: "//android.widget.EditText[@hint='Category Name']"
  ios:
    xpath: "//XCUIElementTypeTextField[@placeholderValue='Category Name']"

# ---- 日期 ----
date_picker_trigger:
  description: "點擊以開啟原生日期選擇器"
  android:
    accessibility_id: "Pick date"
  ios:
    accessibility_id: "Pick date"

# ---- 備註 / 標籤 ----
notes_input:
  description: "自由文字備註(也作為標籤,以逗號分隔)"
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
  description: "捨棄並關閉互動視窗"
  android:
    accessibility_id: "Cancel"
  ios:
    accessibility_id: "Cancel"

# ---- 驗證 ----
amount_error_message:
  description: "金額為空或非法時的內嵌錯誤"
  android:
    xpath: "//*[contains(@text, 'required') or contains(@text, 'invalid')]"
  ios:
    predicate: "type == 'XCUIElementTypeStaticText' AND (label CONTAINS 'required' OR label CONTAINS 'invalid')"
```

**規則**:
- ✅ 每個項目都必須有 `description`(人類可讀的用途說明)。
- ✅ 至少填 `android.accessibility_id`(Flutter 將語意 ID 渲染為 accessibility 標籤)。
- ⚠️ XPath 是兜底 —— 僅在不存在 accessibility_id 時使用。
- ❌ 永遠不要在 Python 檔中硬編碼 Locator。

### 4.2 Locator Loader(utils/locator_loader.py)

```python
"""含策略回退鏈的 Locator loader(見 §4.3)。"""

from pathlib import Path
import yaml

# 順序很關鍵 —— 第一個命中即勝出。參見 §4.3。
_STRATEGY_PRIORITY = ("accessibility_id", "id", "xpath", "predicate")

# 模組級快取:(page, key, platform) -> (strategy, value)
_cache: dict[tuple[str, str, str], tuple[str, str]] = {}


def load_locator(page: str, key: str, platform: str = "android") -> tuple[str, str]:
    """回傳所請求 locator 的 (strategy, value)。

    依序遍歷 §4.3 的優先鏈。若無符合策略則拋出 KeyError。

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
    """僅供測試使用:清空快取,讓 locator 自 YAML 重新讀取。"""
    _cache.clear()
```

**為什麼使用回退鏈而非嚴格的 `accessibility_id`**:
§4.1 的範例中,`transaction_type_toggle` 在 Android 上沒有 accessibility_id(只有 `xpath`)。嚴格的 `entry[platform]["accessibility_id"]` 查找會拋出 `KeyError`。遍歷 `_STRATEGY_PRIORITY` 讓 loader 在 YAML 增長時仍保持健壯。

### 4.3 嚴格的優先順序

1. `accessibility_id`(Flutter 語意標籤)—— **首選**
2. `id` / `resource-id`
3. `class` 鏈
4. `xpath`(最後手段)
5. `predicate`(僅 iOS)

---

## 5. 架構分層

```
┌─────────────────────────────────────────┐
│  tests/features/*.feature               │  Gherkin(人類語言)
└──────────────────┬──────────────────────┘
                   │ pytest-bdd 探索
                   ▼
┌─────────────────────────────────────────┐
│  tests/step_defs/*_steps.py             │  Step 實作
│  (Given/When/Then → 呼叫 Flow)          │
└──────────────────┬──────────────────────┘
                   │ 呼叫
                   ▼
┌─────────────────────────────────────────┐
│  flow/*_flow.py                         │  業務邏輯
│  (用例編排)                             │
└──────────────────┬──────────────────────┘
                   │ 使用
                   ▼
┌─────────────────────────────────────────┐
│  page/*_page.py                         │  Page Object
│  (UI 元素動作)                          │
└──────────────────┬──────────────────────┘
                   │ 繼承
                   ▼
┌─────────────────────────────────────────┐
│  page/base_page.py                      │  抽象基底
│  (click, input, swipe, wait, screenshot)│
└──────────────────┬──────────────────────┘
                   │ 使用
                   ▼
┌─────────────────────────────────────────┐
│  utils/driver.py                        │  Appium 封裝
│  (不允許外部使用裸 driver.find_element) │
└──────────────────┬──────────────────────┘
                   ▼
               Appium → Trackify App
```

**分層規則**:
- ❌ step def 不允許直接 import `page.*` —— 必須經過 Flow。
- ❌ Flow 不允許直接 import `utils.driver` —— 只呼叫 Page 方法。
- ❌ Page 之間不允許互相 import —— 保持彼此獨立。
- ✅ Base page 暴露基本操作:`click`、`input_text`、`swipe`、`wait_for`、`screenshot`、`is_visible`。

### 5.1 Fixture 接線(conftest.py)

driver 與每個 Page / Flow 實例都必須透過 pytest fixtures 注入 —— 不要在 step 本體中直接實例化。這樣可以讓 teardown 路徑單一來源。

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

PKG = "com.blixcode.trackify"  # Trackify Android 套件名


@pytest.fixture(scope="session")
def driver() -> WebElement:
    """Session 級 Appium driver —— 每次 pytest 執行一個連線。"""
    platform = os.getenv("PLATFORM", "android")
    factory = AppiumDriverFactory(platform=platform)
    d = factory.create()
    yield d
    d.quit()


@pytest.fixture(autouse=True)
def reset_app_state(driver):
    """每個測試前清空 Hive DB,以保證狀態確定性。

    為什麼用 `pm clear`(而非 seed 檔):
    - Trackify 將資料儲存在 Hive 的 /data/data/<pkg>/app_flutter/hive_box.db。
    - 透過設定 UI 清空不穩定且依賴順序。
    - `pm clear` 是一條 ADB 指令,<1s 完成,是官方重設路徑。
    """
    subprocess.run(["adb", "shell", "pm", "clear", PKG], check=True, timeout=10)
    driver.launch_app()  # 清空後重新啟動
    yield


# Page fixtures —— 薄包裝,按測試懶構造
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

# Flow fixtures —— 組合 Page
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

**為什麼 fixture 接線很重要**:
- 沒有它,step def 會自己呼叫 `HomePage(driver())` → 沒有 teardown,連線洩漏。
- `reset_app_state` 使用 `autouse=True`,因此每個測試都從一個乾淨的 Hive 開始。
- 重設後,每個 feature 的 `Background` 在業務動作開始前完成相同的三段首次執行階段:儲存名字 `Kimbal`;選擇 `$ US Dollar` 與月度預算 `30000`;啟用 Bank SMS Reader 並點擊 `Get Started`。
- 永遠不要把 onboarding 的 `Skip` 當作測試前置條件。Skip 會讓 profile、currency、budget 與追蹤偏好都處於未定義狀態。
- 每個 Page Object 的 wait 都會檢查 Android 系統彈窗 `Allow Trackify to send you notifications?` 並在繼續前點擊 `Allow`。handler 只比對通知文案,不接受 SMS 等其他權限彈窗。

---

## 6. BDD 約定(pytest-bdd)

### 6.1 檔案命名

- 每頁/功能一個 `.feature` 檔。
- 每個 `.feature` 對應一個 `_steps.py`,檔名匹配。

### 6.2 場景 tags(pytest markers)

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

### 6.3 Step 函式重用

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

**規則**:
- ✅ 使用 `parsers.parse(...)` 參數化 —— 避免在 step 內硬編碼字串。
- ✅ 跨場景重用 step;不要複製邏輯。
- ❌ step 本體內不允許 inline 斷言 —— 只允許在 `Then` step 中斷言。

### 6.4 pytest markers(pytest.ini)

```ini
[pytest]
# ---- discovery ----
testpaths = tests
bdd_features_base_dir = tests/features
python_files = *_steps.py test_*.py
python_classes = Test*
python_functions = test_*

# ---- markers (v3 範圍) ----
markers =
    smoke: P0 critical path
    regression: P0 + P1 full coverage
    p0: critical priority
    p1: high priority
    custom_category: 自訂類別流程(在 Add Transaction 內新增 category)
    filter: 列表篩選(Transactions 按 type / category / 日期)
    grouping: 列表按日期分組(Transactions 列表展示)

# ---- output ----
addopts = -ra --strict-markers --tb=short
```

**逐欄位說明**:

| 欄位 | 原因 |
|-------|----------------|
| `testpaths` | 把蒐集範圍限制在 `tests/` —— 避免誤蒐集 `page/`、`flow/`、`utils/` |
| `bdd_features_base_dir` | pytest-bdd 需要知道 `.feature` 檔的位置;否則收集到的 ID 中 feature 路徑錯誤 |
| `python_files = *_steps.py` | pytest-bdd 要求 step 檔以 `_steps.py` 結尾;這個 glob 強制這點,即使有人命名為 `add_transaction.py` |
| `--strict-markers` | 像 `@smoek` 這樣的拼字錯誤會直接報錯而非默默忽略 —— 儘早發現 marker 錯誤 |
| `--tb=short` | traceback 截斷為每個失敗一幀 —— 讓 Allure 報告更易掃讀 |

**v3 範圍的 marker 對映**(7 個 BDD 場景):

| Marker | 場景 |
|--------|--------|
| `@smoke @p0` | Add Expense、Add Income、Add Transfer、Validation(空金額) |
| `@p1` | Custom Category、Filter by type、Group-by-date |

### 6.5 Gherkin 風格指南

若無這些規則,每個場景讀起來就像一次獨立的 AI 生成。Codex 必須遵守全部規則:

| 規則 | 原因 |
|------|-----|
| **第三人稱、現在式** —— "user taps Save",不要 "I tap Save" 或 "user tapped Save" | 與 pytest-bdd 的 step 正則預設一致;統一時態避免 step_defs 重複 |
| **使用 "user"(不用 "the user" / "users" / "I")** | 在所有 .feature 中只需 grep 一個 token |
| **同一動作 = 同一措辭** —— 若一個場景用 "user enters amount",所有場景都用 "user enters amount" | step 配對是精確字串;動詞漂移 = "step definition not found" |
| **資料驅動場景使用 `Scenario Outline` + `Examples`**;僅在場景真正唯一時才使用 `Scenario` | 減少 .feature 行數;一個 step_def 可驅動 N 個場景 |
| **共用 setup 放入 `Background`** —— 每個 feature 檔開頭都有一個 `Background:` 區塊;不要在每個 Scenario 中重複 "user is on X page" | DRY;一處修改即可改變前置條件 |
| **`Then` 必須同時包含**:(a) **具體的值斷言** AND (b) **否定斷言**("X did NOT happen") | 防止錯誤交易被儲存的迴歸;避免過於寬泛的配對 |
| **一個 feature = 一條使用者路徑** —— `add_transaction.feature` 涵蓋 3 種交易類型 + 驗證 + 自訂類別(5 個場景);`transactions.feature` 涵蓋 filter + grouping(2 個場景) | 每個 .feature 檔 = 一種審閱心智模型 |
| **使用 `And` / `But` 在同一子句中串接步驟** —— 不要重複 `Given` / `When` / `Then` | 符合 Gherkin 可讀性規範 |

**需要拒絕的反模式**:

```gherkin
# ❌ BAD — 第一人稱 + 過去式 + "the user"
Given I was on the Home page

# ❌ BAD — 同一動作在三個場景用不同動詞
# 場景 A:
When user enters amount "100"
# 場景 B:
When user inputs amount "200"
# 場景 C:
When user types amount "300"

# ❌ BAD — Then 模糊,缺少具體值或否定檢查
Then the transaction is saved

# ❌ BAD — 在每個 Scenario 中把 Background 當作 Given 重複
Scenario: Add expense
  Given app is launched with clean database
  And user is on the Home page
  When ...
Scenario: Add income
  Given app is launched with clean database
  And user is on the Home page
  When ...
```

### 6.6 Step 詞彙契約

**這是一份契約**:`step_defs/*_steps.py` 必須實作下面的每個短語,每個 `.feature` 檔必須只使用這些短語。新增一個短語,必須在同一次提交中同時新增 Gherkin 用法與 Python step。

#### Given 短語(3 個頁面上下文 + 4 個 Background 步驟)

```gherkin
# 在每個 .feature 的 Background: 區塊中使用一次
Given app is launched with a clean database
Given user enters name "<name:str>" and continues
Given user selects currency "<currency:str>" and sets monthly budget "<monthly_budget:int>"
Given user enables Bank SMS Reader and gets started

Given user is on the Home page
Given user is on the Add Transaction page
Given user is on the Transactions page
```

#### When 短語(14 個動作)

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

#### Then 短語(9 個斷言)

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

**解析規則**(用於 step_defs 中的 `parsers.parse(...)`):

| 占位符 | 型別 | 範例值 | 驗證 |
|-------------|------|---------------|------------|
| `<type:str>` | `str` | `"expense"` | 必須是 `expense`、`income`、`transfer` 之一(在 Flow 中驗證,而非 step) |
| `<amount:float>` | `float` | `100.0`、`9.99` | 必須 `> 0`(在 Flow 中驗證) |
| `<category:str>` | `str` | `"Food"`、`"Transport"` | 自由文字 |
| `<note:str>` | `str` | `"breakfast with Dinna"` | 自由文字 |
| `<tags:str>` | `str` | `"food,breakfast"` | 非空、逗號分隔的標籤文字 |
| `<name:str>` | `str` | `"baby cost"` | 自由文字 |
| `<currency:str>` | `str` | `"$ US Dollar"` | 完整的可見選項標籤 |
| `<monthly_budget:int>` | `int` | `30000` | 必須為正整數,且與顯示的滑桿值一致 |
| `<message:str>` | `str` | `"Amount is required"` | 對顯示文字做子字串比對 |
| `<date_time:str>` | `str` | `"20250506 9:00 AM"` | `YYYYMMDD h:mm AM/PM` 格式的本地日期/時間 |

**Add Transaction 儲存後斷言規則**:
- 在點 Save 之前先在 Add Transaction 上擷取顯示的日期與時間。Transactions 的斷言必須在對應日期下找到一列,該列包含同樣格式化的金額、類別與時間。
- Expense 與 Income 交易分別累加 Home 上既有 `This Month` 的 expense 與 income 值。Transfer 交易不改變任何一項。
- 大號的 `This Month` 值是 `income - expense`。
- 顯示的預算百分比為 `expense / budget * 100`,按 half-up 規則(`ROUND_HALF_UP`)取整。例如預算 `20000`:expense `125` 得 `0.625%`,顯示 `1%`;expense `1125` 得 `5.625%`,顯示 `6%`;expense `9500` 得 `47.5%`,顯示 `48%`。
- 空金額的驗證必須讓 Recent Transactions 與 Transactions 頁面同時為空,且所有 `This Month` 值保持不變。

→ **這些短語的實際使用位置**:見 §6.7 場景清單 v3。每個場景都是由這些短語的子集組合而成。若 §6.7 需要一個不在此處的短語,必須先在此處新增,然後在同一次提交中更新場景。

### 6.7 場景清單 v3(§7 任務 8 / 8b / 10 的唯一事實來源)

下面 7 個場景是**唯一的真相來源**。§7 任務 8 / 8b / 10 的驗收標準依準確標題引用本清單。

#### `tests/features/add_transaction.feature` —— 5 個場景

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

當前 Android 版本的實作說明:
- Gherkin 短語 `user taps "Add new category"` 對應於在橫向 Category 清單上向左滑動,然後依序 `New` → `Add Category`。
- `baby cost` 使用 New Category 表單的預設圖示與顏色。其固定寬度的交易 chip 只顯示截斷後的 `baby`,但 Manage Categories 與儲存後的 Home 交易保留全名。
- 空金額提交停留在 Add Transaction 上,欄位為空,不儲存任何內容。此版本不向 accessibility 暴露期望的驗證文案,因此斷言優先以可見文案為準,否則在校驗 Home 清單為空前先校驗表單被拒絕的狀態。
- 在預算 `30000` 下,expense `100` 與 `50` 產生的百分比低於 `0.5%`,按 half-up 取整後正確顯示為 `0%`。

#### `tests/features/transactions.feature` —— 2 個場景

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

> Transactions 場景重用了 `tests/step_defs/common_steps.py` 中的 setup 與交易登錄 step;feature 特定的 step 只負責導覽、篩選與清單行為斷言。

**為什麼這份清單放在這裡,而非只放在 Feature_Inventory.md**:
- `Feature_Inventory.md` 是 **what**(哪些功能、為什麼選)。
- `TECHNICAL_SPEC.md` §6.7 是 **how**(準確的場景標題、tags、Given/When/Then 行)。
- 如此區分,讓評估者可透過 `Feature_Inventory.md` 讀範圍理由,Codex 可透過 §6.7 讀實作細節。

---

## 7. 實作任務清單(13 個任務,每個一次提交)

> ⚠️ **在前置任務已提交且 `pytest` 執行乾淨(或還沒有測試)之前,不要執行任何任務。**

### 第 0 天 —— 手動前置(無提交,一次性)

這些步驟在開發機上執行一次,在 Task 1 之前。它們不產生提交。

```bash
# 1. Appium server 工具鏈
npm install -g appium                              # CLI
appium driver install uiautomator2                 # Android driver

# 2. 可選：手動啟動 Appium（矩陣 Runner 可以自動啟動）
appium --address 127.0.0.1 --port 4723           # 監聽 :4723

# 3. 手動啟動時驗證 server 在線
curl --noproxy '*' http://localhost:4723/status | jq . # 期望 ready=true

# 4. 驗證模擬器 + app 套件
adb devices                                        # 列出已連線裝置
adb install -r -t app/app-release.apk              # 安裝 Trackify
adb shell pm list packages | grep com.blixcode.trackify # 確認套件存在
```

**直接執行 pytest 前修復相關失敗。** 矩陣 Runner 會自動檢查或啟動本機
Appium；應用套件和驅動安裝失敗仍必須在執行前修復。

| # | 任務 | 涉及檔案 | 驗收標準 | 提交訊息 |
|---|------|---------------|---------------------|----------------|
| 1 | 專案腳手架 | `pyproject.toml`、`pytest.ini`、`conftest.py`、`.gitignore` | `pytest --collect-only` 退出 0;`conftest.py` 包含 §5.1 中的 `reset_app_state` autouse fixture(在每個測試前呼叫 `adb shell pm clear com.blixcode.trackify`) | `chore: bootstrap project` |
| 2 | Base page | `page/base_page.py` | 能成功 import `BasePage` | `feat(page): base page with click/wait/screenshot` |
| 3 | Driver 工廠 | `utils/driver.py`、`utils/config.py` | `AppiumDriverFactory(platform="android").create()` 回傳一個可用的 Appium 連線;類別名避免與 `selenium.webdriver.Driver` 衝突;被 §5.1 中的 `driver` fixture 使用 | `feat(utils): appium driver factory` |
| 4 | Locator loader | `utils/locator_loader.py`、`locator/home.yaml`(骨架) | `load_locator("home", "x", "android")` 回傳字串 | `feat(utils): yaml locator loader + skeleton` |
| 5 | Home page + Locator | `page/home_page.py`、`locator/home.yaml` | `home.click_add_expense()` 在手動 Appium 連線上能跑通 | `feat(page): home page (Add Transaction shortcut)` |
| 6 | Add Transaction page + Locator | `page/add_transaction_page.py`、`locator/add_transaction.yaml` | `add_tx.add_expense(amount=100, category="Food")` 能跑通 | `feat(page): add transaction page (all 3 types)` |
| 7 | Add Transaction flow | `flow/add_transaction_flow.py` | `flow.add_expense(...)` 編排 Page 並回傳新 ID | `feat(flow): add transaction business logic` |
| 8 | 第一個 BDD feature(Add Expense happy path) | `tests/features/add_transaction.feature`、`tests/step_defs/add_transaction_steps.py`、`conftest.py`(page/flow fixtures) | `pytest tests/features/add_transaction.feature -k "happy_path"` 僅收集並執行 §6.7 中的 "Add expense happy path" 場景。其他 4 個 Add Transaction 場景寫好但標記為 `@skip`(或僅保留 feature 級 Background)。本場景使用的 §6.6 短語全部實作。 | `test(case): add transaction bdd (expense happy path)` |
| 8a | 首次執行 setup 基準 | `locator/onboarding.yaml`、`page/onboarding_page.py`、`flow/app_setup_flow.py`、`conftest.py`、BDD `Background` 區塊 | 每個業務場景都完成 `Kimbal` → `$ US Dollar` + `30000` → Bank SMS Reader 啟用 + `Get Started`;沒有測試路徑點擊 onboarding `Skip`;業務動作開始前 Home 顯示 `Kimbal` 和 `$` | `feat(setup): complete required first-run configuration` |
| 8b | 其餘 Add Transaction 場景 | `tests/features/add_transaction.feature`、`tests/step_defs/add_transaction_steps.py` | 解除 §6.7 中其餘 **4 個場景** 的 skip(Add Income、Add Transfer、Validation、Custom Category)。實作新增的 §6.6 短語(`user selects type`、`user taps "Add new category"`、`user creates custom category`、`error message ... is shown for amount`、`no transaction appears ...`)。Custom Category 建立並選中 `baby cost`,圖示/顏色任意。**全部 5 個 Add Transaction 場景通過**。 | `test(case): add transaction bdd (4 more scenarios + custom category)` |
| 8c | 交易持久化與 Home 彙總斷言 | `locator/home.yaml`、`locator/transactions.yaml`、`page/base_page.py`、`page/home_page.py`、`page/transactions_page.py`、`page/add_transaction_page.py`、`flow/add_transaction_flow.py`、`utils/system_dialogs.py`、Add Transaction BDD 檔 | 每個 Add Transaction 場景都驗證 Transactions 中相符的日期/金額/類別/時間,以及 `This Month` 的收入、支出、結餘與 half-up 整數百分比。Transfer 對彙總無影響。通知權限彈窗全域接受。 | `test(case): verify transaction persistence and monthly summary` |
| 9 | Transactions page + flow | `page/transactions_page.py`、`flow/transactions_flow.py`、`locator/transactions.yaml`、Add Transaction 日期/時間 Page/Flow locators、`conftest.py` | 手動測試:filter 運作;`2025-05-06 9:00 AM` 的交易被分到 `06 May 2025` 組下 | `feat(page): transactions page + flow` |
| 10 | Transactions BDD | `tests/features/transactions.feature`、`tests/step_defs/transactions_steps.py` | §6.7 中的兩個 Transactions 場景都被收集並執行:按類型篩選(`@filter`)、按日期分組(`@grouping`)。實作新增的 §6.6 短語(`user filters transactions by type`、`only transactions of type ... are shown`、`transactions are grouped by date ...`)。**專案總計:5 個 Add Transaction + 2 個 Transactions = 7 個場景**。 | `test(case): transactions bdd (2 scenarios)` |
| 11 | Allure + 失敗時截圖 | `conftest.py`(新增 Allure metadata + `pytest_runtest_makereport` 鉤子) | `pytest --alluredir=./allure-results` 產出結果;`call` 失敗時,鉤子將 PNG 儲存到 `report/screenshots/<test_name>.png` 並附加到 Allure —— **不要**用 try/except 包住測試本體(見 §8 反模式)。鉤子樣板:`pytest.hookimpl(tryfirst=True, hookwrapper=True) def pytest_runtest_makereport(item, call)`,先 yield,再檢查 call report。 | `feat(report): allure + screenshot on fail` |
| 12 | CI + 覆盤 | `.github/workflows/ci.yml`、`docs/REFLECTION.md` | README 連結可用;所有提交乾淨 squash | `docs: reflection + ci + final polish` |

**選用的第 4 天任務**(時間允許時):
- **任務 13**:AI Triage —— 把每個測試的**第一個**失敗 pytest 階段分類為 {**Locator**、**App Bug**、**Env**、**Script**、**Data**、**Unknown**} 之一。判定僅為顧問式:它**絕不能**修改 pytest 結果、隱藏原始 traceback,或被當作已確認的根因。

  **結果契約**(`TriageResult`,凍結 dataclass):

  | 欄位 | 型別 | 規則 |
  |-------|------|------|
  | `category` | enum string | `Locator`、`App Bug`、`Env`、`Script`、`Data`、`Unknown` 之一 |
  | `confidence` | float | 截斷到 `0.0..1.0` |
  | `reasoning` | string | 簡潔,最長 500 字元;絕不含金鑰或完整 traceback |
  | `next_action` | string | 具體的工程師動作,最長 500 字元 |
  | `classifier` | string | `local`、`llm` 或 `disabled` |
  | `matched_signatures` | tuple/list | 僅本地特徵 ID;LLM/disabled 結果下為空 |

  Allure JSON 附件必須包含上述欄位,加上 `schema_version`、`test_name` 與失敗的 `phase`。序列化使用 `dataclasses.asdict()`;不序列化原始例外物件。

  **架構(2 個階段)**:

  1. **本地加權啟發式(始終啟用)** —— 在模組匯入時編譯一次 `LOCAL_SIGNATURES`,然後匹配正規化的 `error_msg + traceback`。每個特徵有各自的信心度。選擇最高信心度的匹配;並列時按 `Env > Locator > Data > App Bug > Script`。信心度 `>= 0.70` 時直接回傳。不要把弱匹配疊加:多個泛型字串不能拼出高信心度。該階段不進行任何檔案、環境或網絡 I/O。
  2. **Claude 相容回退(顯式 opt-in)** —— 僅在本地信心度低於 `0.70` 且 `AI_TRIAGE_LLM_ENABLED=1`、`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL` 都存在時執行。`ANTHROPIC_BASE_URL` 選用,預設 `https://api.anthropic.com`;如 `https://api.minimaxi.com/anthropic` 的閘道路徑會在附加 `/v1/messages` 之前被保留。透過 Python 標準函式庫(或測試中的可注入 callable)使用 Anthropic Messages 協定;不要在 §1 之外新增 SDK 相依。最多一次請求,無重試,總逾時 5 秒。任何逾時、HTTP 錯誤、設定缺失、JSON 格式錯誤、未知名稱或非法欄位都回傳 `Unknown / 0.0`,且不拋例外。

  **必需的本地特徵**(`re.IGNORECASE`;`re.DOTALL` 僅用於受限的上下文模式):

  | 類別 | 簽名 ID / 正則意圖 | 信心度 | 預設 `next_action` |
  |----------|-----------------------------|------------|-----------------------|
  | **Env** | `connection_refused`:`ConnectionRefused(?:Error)?`、`ECONNREFUSED`,或 `Failed to establish a new connection` 出現在 `4723`/Appium 附近 | `0.98` | 驗證 Appium 監聽在 `:4723`;檢查 `appium.log` |
  | **Env** | `device_unavailable`:`adb.*(?:not found\|No such file)`、`device (?:offline\|unauthorized)`,或 `no (?:Android )?devices?` | `0.95` | 執行 `adb devices`;重新連線或啟動目標裝置 |
  | **Locator** | `element_missing`:`NoSuchElement(?:Exception\|Error)` 或 `Unable to locate element` | `0.98` | 檢查命中的 locator YAML 條目與目前 Appium page source |
  | **Locator** | `locator_timeout`:在同時包含 `find_element`、`locator`、`accessibility_id` 或 `xpath`(任一順序)的受限內容中出現 `TimeoutException` | `0.85` | 確認頁面狀態,若元素變更則更新 locator/fallback |
  | **Data** | `test_data_missing`:在 `test_data`/`fixture`/`yaml` 附近出現 `KeyError`,或在 `missing`、`required`、`not found` 附近出現 test-data/YAML 文字 | `0.90` | 驗證 `data/` 中必要的鍵與行值 |
  | **Data** | `database_corrupt`:`HiveError` 或在 `data`/`database` 附近出現 corruption 文字 | `0.80` | 重設本地 app 資料庫並驗證 seed/setup 路徑 |
  | **App Bug** | `app_crash`:`ANR`、`App crashed`、`not responding`、`has stopped`,或 `java\.lang\.` | `0.98` | 在相同 build/device 上手動重現,如可重現則送出 app 缺陷 |
  | **App Bug** | `business_mismatch`:在 `expected` 與 `actual`/`got`/`displayed`/`missing` 附近出現 `validation`/`summary`/`saved transaction` | `0.82` | 比對顯示狀態與需求,並手動重現 |
  | **App Bug** | `element_disabled`:`element.*not enabled` | `0.60` | 模糊;蒐集頁面狀態,允許 LLM/Unknown,而非直接短路 |
  | **Script** | `python_structure`:`ImportError`、`ModuleNotFoundError`、`NameError`、`SyntaxError`,或 `IndentationError` | `0.98` | 直接修復 Python/匯入錯誤 |
  | **Script** | `python_contract`:`AttributeError` 或 `TypeError` | `0.90` | 閱讀頂層專案幀,修正 API/型別用法 |
  | **Script** | `generic_assertion`:裸 `AssertionError` | `0.40` | 本身模糊;沒有更強上下文時不應歸類為 Script |

  **輸入正規化與私隱**:
  - 輸入鍵:`error_msg`、`traceback`,可選 `test_name`、`phase`、`screenshot_path`。出於命令列/向後相容考量,缺失的 `test_name` 預設 `unknown`,缺失的 `phase` 預設 `call`。
  - 在送給 LLM 之前,`error_msg` 限制為 2,000 字元,traceback 限制為最後 12,000 字元。
  - 在附加或網絡使用前,對授權標頭、API key/token、URL query 字串做脫敏。
  - 多模態輸入超出範圍。僅傳送 `screenshot_available` 與截圖 basename;絕不傳送影像位元組或絕對本地路徑。
  - 將例外文字與 traceback 視為不可信的引用資料。系統提示明確要求忽略嵌入在失敗文字中的指令,且不暴露任何工具。
  - 僅請求一個 JSON 物件(`temperature=0`,小且受限的輸出)。驗證名稱白名單、數值信心度、非空受限字串,並忽略未知回應欄位。

  **pytest / Allure 整合**:
  - 在 `outcome = yield` 之後、報告建立之後,延伸 Task 11 的 `pytest_runtest_makereport` 鉤子。
  - 對 `setup`、`call`、`teardown` 失敗都做歸類;環境失敗常發生在 setup。使用 `item.stash` 鍵,使僅第一個失敗階段被歸類一次。
  - 對於 `call` 階段失敗,先擷取 Task 11 的截圖,並把回傳路徑傳給 triage。其他階段使用 `screenshot_path=None`。
  - 即使是 `Unknown`,也要附加 `AI Triage`,使用 `allure.attachment_type.JSON`,前提是 Allure 生命週期已啟用。
  - 在失敗階段結束後,透過 pytest 的 `terminalreporter.write_line()` 輸出 `[AI Triage] <Category> (<NN%>): <reasoning>`,以保證擷取設定不會隱藏它。僅在沒有 terminal reporter 時回退到 `print()`。
  - Triage 失敗會被捕獲並轉換為 `Unknown`;報告程式碼絕不能取代原始測試失敗。

  **執行展示**:
  - 通過的測試不會觸發 triage 呼叫或附件。僅對第一個失敗階段進行分類。
  - `classifier=local` 證明在沒有網絡 I/O 的情況下回傳了確定性特徵;`classifier=llm` 表示嘗試了一次相容模型呼叫;`classifier=disabled` 表示由於缺少必要的 opt-in 設定,模糊證據無法使用 LLM。
  - 終端行是快速訊號,Allure `AI Triage` JSON 是可稽核的記錄。兩者都是顧問式,必須與原始 traceback 與截圖一起閱讀。
  - 真實 key 只屬於被忽略的 `.env`;`.env.example` 只放占位符。專案從不自動載入 `.env`,並且不得為了閘道呼叫成功而關閉憑證校驗。
  - 執行時設定與驗證流程記錄在 [`docs/AI_TRIAGE.md`](AI_TRIAGE.md)。

  **單元測試隔離**:
  - 新增 `unit` marker。將 `reset_app_state` 重構為透過 `request.getfixturevalue("driver")` 懶取得 driver;對 `@pytest.mark.unit` 測試立即 yield,使純 triage 測試不會啟動 Appium 或呼叫 `adb pm clear`。
  - 注入 LLM callable。一個 spy/fake 必須證明,本地 `Locator` 命中時零 LLM 呼叫;不要在生產程式碼裡留 `print('local hit')` 這種插樁。

  **涉及檔案**:`ai/__init__.py`、`ai/triage.py`、`tests/unit/test_triage.py`、`conftest.py`、`pytest.ini`。

  **驗收標準**:
  - `uv run python -c "from ai.triage import triage_failure; print(triage_failure({'error_msg': 'NoSuchElementException: ...', 'traceback': ''}).category)"` 輸出 `Locator`。
  - `uv run pytest -m unit tests/unit/test_triage.py -q` 在沒有執行 Appium server 或連線裝置的情況下通過。
  - 單元案例涵蓋每個類別、優先順序、裸 `AssertionError -> Unknown`(無 LLM)、設定缺失、逾時/非法 LLM 輸出、信心度截斷、脫敏,以及本地命中時零網絡呼叫。
  - 受控的 setup 或 call 失敗恰好產生一份 `AI Triage` JSON 附件(滿足要求的 schema)和一行可見的主控台輸出;原始 pytest 失敗保持不變。
  - 缺少 `ANTHROPIC_API_KEY` 或 LLM 被停用時,回傳 `Unknown`、`confidence=0.0`、`classifier=disabled`,無例外,無網絡呼叫。
  - 本地分類無 I/O,且具確定性。可以出於資訊目的對執行時進行基準測試,但不需要硬體相關的 `<1 ms` 斷言。

  **PoC 範圍之外**:
  - 多模態截圖分析 / Claude Vision。
  - 基於工程師修正的自學習。
  - 跨執行快取或 flaky-test 歷史。
  - 自動重試、失敗抑制或缺陷送出。
  - 對非英文錯誤訊息分類。

  **提交訊息**:`feat(ai): failure triage with local heuristic + LLM fallback`

**選用的第 5 天任務**(挑戰後延伸):
- **任務 14**:Excel → `.feature` 同步引擎 —— `data/test_cases.xlsx` 僅對由 `scenario_id` 識別的託管 Scenario 區塊是權威的;Feature 標頭與 Background 區塊仍由程式碼擁有。引擎依 Module 路由行,先完整校驗整個 workbook 再寫入,僅透過 backup/replace/rollback 事務套用 `added` / `modified` / 明確 `deprecated` 區塊,並保證未觸及的託管區塊保持位元一致。`data/test_cases_template.xlsx` 作為引導登記冊。完整契約見 §11。提交訊息:`feat(sync): excel-to-feature sync engine PoC`。

---

## 8. 反模式(不要做)

| 反模式 | 不好之處 | 正確做法 |
|--------------|--------------|----------------|
| 在測試程式碼中寫 `driver.find_element(...)` | 讓測試與裸 Appium 耦合 | 始終透過 `BasePage` / Page Object |
| 在 Page 中使用 `time.sleep(2)` | 在慢裝置上不穩定 | 使用 `wait_for(...)` 配明確條件 |
| 在 Python 中寫內嵌 XPath | 難以維護 | 移到 `locator/*.yaml` |
| 在另一個 Page 內 `from page.X import Y` | 緊耦合 | Page 之間不應互相依賴 |
| 在 BDD step 中使用 if/else 分支 | 難以除錯 | 拆成多個場景 |
| 在 Flow 裡直接呼叫 Appium | 跳過 Page 層 | Flow → Page → Driver |
| 使用 `pytest.fixture` 時不考慮 scope/cleanup | 資源洩漏 | 明確 `autouse=False` + teardown |
| 一次性寫出整個自動化 | 無法審閱/除錯 | 一次任務一個提交,見 §7 |
| 新增「額外」特性(Docker、MyPy、Black) | 範圍蔓延 | 僅使用 §1 技術棧 |

---

## 9. 參考文件

Codex 必須在開始 Task 1 之前閱讀以下文件:

1. `README.md` —— 範圍、AI 使用規則、面對評估者的故事(最高層)
2. `docs/Feature_Inventory.md` —— 存在哪些頁面 + 哪兩個在範圍內(共 7 個 BDD 案例)
3. `docs/TECHNICAL_SPEC.md` —— 本檔(如何建構)

Task 8 之後(第一個 BDD 場景通過),Codex **應該**重新閱讀 `README.md` 的「Test Coverage」章節與 `Feature_Inventory.md` §四,在繼續 Task 8b / 10 之前確認範圍一致。

### 內部交叉引用(TECHNICAL_SPEC.md 內部)

| 若你在撰寫… | 必須遵守… |
|---------------------|----------------|
| `.feature` 檔(Task 8 / 8b / 10) | §6.5 風格指南 + §6.6 step 詞彙 + §6.7 場景清單(精確標題) |
| `step_defs/*_steps.py` | §6.6 短語(與 `parsers.parse` 一一對應)+ §6.3 重用規則 |
| `page/*_page.py` | §3 規範 + §4 locator YAML 格式 + §4.3 優先鏈 |
| `flow/*_flow.py` | §5 分層規則(禁止 `utils.driver` import;只能呼叫 Page) |
| `conftest.py` | §5.1 fixture 接線樣板(driver + reset_app_state + 每頁 fixture) |
| Locator yaml | §4.1 格式 + §4.1 完整樣板 + §4.2 回退 loader |

---

## 10. Git 與提交規範

- **每個任務一次提交** —— 不要批次
- **提交訊息格式**:`<type>(<scope>): <subject>`
  - 類型:`chore`、`feat`、`test`、`docs`、`fix`、`refactor`
  - scope:`page`、`flow`、`utils`、`case`、`report`、`ai`
- **每次提交前**,執行 `pytest --collect-only` 確保沒有匯入錯誤
- **參考**:每條提交訊息應能對應到 §7 的一行

### Squash 策略(已修訂)

> ⚠️ **不要把 13 個任務提交 squash 成一個。** 每個提交都是一個可審閱單元;squash 會破壞「何時新增了什麼、為何」的軌跡。

當使用者/評估者想要乾淨的主分支歷史時,使用 **互動式 rebase 僅 squash 瑣碎的提交**(例如 8 與 8b 可以合併,因為它們涉及相同檔案並代表同一個 feature):

```bash
# 選用:把 8 與 8b 合併為單一 "add transaction bdd" 提交
git rebase -i HEAD~3            # 把 8b 標記為 "squash"
# 保留 1-7 與 9-13 為獨立提交 —— 它們是獨立的 feature
```

**保持獨立的提交**(不要 squash):
- 任務 1(腳手架)—— 奠定基礎
- 任務 11(Allure + 截圖)—— 正交關注點
- 任務 12(CI + 覆盤)—— 最終打磨
- 任何在原 feature 提交之後落地的 `fix:` 提交

**預設**:保留 13 個提交不變。僅在使用者要求時 squash。

---

## 11. 活文件:Excel → Feature 同步(第 5 天延伸)

> **本節對挑戰而言是選用的。** Tasks 1-12 先完成。Task 14 作為單獨的 `feat(sync): ...` 提交。箭頭刻意單向:PoC 永遠不把測試結果或場景編輯從 `.feature` 寫回 Excel。

### 11.1 所有權模型

同步契約是混合的,而不是「Excel 擁有每一個位元組」:

| 產物區域 | 擁有者 | 同步行為 |
|-----------------|-------|---------------|
| Excel 中託管案例的列 | Excel | 場景 metadata、tags、When/Then 步驟、生命周期狀態的來源 |
| 以 `# scenario_id:` 開頭的託管 Scenario 區塊 | Excel | 依 ID 新增、取代或明確棄用 |
| `Feature:` 行、檔案註解、`Background:` 區塊 | 程式碼 / 審閱者 | PoC 永不產生或重寫 |
| step 定義、Pages、Flows、locators | 程式碼 | 同步永不修改 |
| `Last Run Result` 與審閱 metadata | QA / 未來 CI | 對 PoC 唯讀;永不寫回 |

這個邊界把公共首次執行 setup 保留在程式碼審閱的 Background 中,同時允許 QA 維護單一場景的動作與斷言。「Excel 事實來源」意謂**僅就託管 Scenario 區塊而言為事實來源**。

### 11.2 規範託管區塊與場景 ID

Task 14 必須先使用 `data/test_cases_template.xlsx` 中已有的 ID,為所有 7 個現有場景新增 ID。託管區塊的標準順序為:

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

`# deprecated_in: <version>` 為選用,僅在填了值時出現在 `# introduced_in:` 之後。因此有**三條強制 metadata 註解**(`scenario_id`、`introduced_in`、`platforms`),以及一條選用的棄用註解;tags 不是註解行。

**目前清單的 ID 對映**:

| 場景 | ID | Module |
|----------|----|--------|
| Add expense happy path | `TC_ADD_TX_001` | `add_transaction` |
| Add income happy path | `TC_ADD_TX_002` | `add_transaction` |
| Add transfer happy path | `TC_ADD_TX_003` | `add_transaction` |
| Validation — empty amount shows error and does not save | `TC_ADD_TX_004` | `add_transaction` |
| Add expense with new custom category created in flow | `TC_ADD_TX_005` | `add_transaction` |
| Filter transactions by type shows only matching type | `TC_TXN_001` | `transactions` |
| Transactions grouped by date with section headers | `TC_TXN_002` | `transactions` |

**規則**:
- ID 格式:`^TC_[A-Z][A-Z0-9_]*_[0-9]{3}$`。
- ID 必須在 workbook 內以及跨所有 feature 檔中唯一。重複 ID 在任何寫入前都是硬錯誤。
- `Module` 使用白名單,而非路徑:`add_transaction -> tests/features/add_transaction.feature`,`transactions -> tests/features/transactions.feature`。未知值是錯誤;不要把不可信的 Module 文字拼接進路徑中。
- 託管區塊從精確以 `# scenario_id:` 開頭的行開始,在下一個託管區塊或 EOF 之前結束。第一個託管區塊之前的內容歸程式碼所有。
- Tags 在 metadata 之後、`Scenario:` 之前渲染。Excel 中逗號分隔的 tags 變成空格分隔的 Gherkin tags(`smoke,p0 -> @smoke @p0`)。優先級作為一種規範 tag 注入並去重。
- PoC 僅支援 `Scenario:`。`Scenario Outline` / `Examples` 同步不在範圍內。
- 初始七場景遷移之後,沒有 ID 的 feature 場景是驗證錯誤,而非隱式的新增/刪除候選。

### 11.3 Excel Schema(`data/test_cases_template.xlsx`)

實際範本包含 16 欄:11 個 L1 登記欄與 5 個 L2 自動化欄。每個標頭都是必需的。下文中的「可空」或「推薦」僅適用於行值,不適用於標頭是否存在。

| 欄 | 行值 | 用途 | PoC 行為 |
|--------|-----------|---------|--------------|
| **Test Case ID** | 必填 | 穩定錨點 | `# scenario_id:` |
| **Module** | 必填 | 安全路由 | 驗證白名單;選擇一個 feature 檔 |
| **Scenario Title** | 必填 | 人類可讀名 | `Scenario:` 文字 |
| **Priority** | 必填:`P0`、`P1`、`P2` | 選擇 | 規範化為一個小寫優先級 tag |
| **App Version Introduced** | 必填 | 版本選擇 | `# introduced_in:` |
| **App Version Deprecated** | 可空;`deprecated` 時必填 | 生命周期 | 選用 `# deprecated_in:` |
| **Platform** | 必填:`android`、`ios` 或 `both` | 平台選擇 | `both` 在 `# platforms:` 中渲染為 `android, ios` |
| **Automation Status** | 必填列舉 | 生命周期門控 | 見下方狀態規則 |
| **Author** | 必填登記 metadata | 擁有權 | 驗證非空;不渲染 |
| **Last Reviewed Date** | 必填 ISO 日期 | 可稽核性 | 驗證;不渲染 |
| **Last Run Result** | 必填登記 metadata | 執行可見性 | PoC 唯讀/忽略 |
| **Tags** | 推薦 | pytest markers | 逗號分隔,無前導 `@`;渲染時依優先級去重 |
| **Pre-conditions** | 推薦 metadata | 手動測試上下文 | PoC 不渲染;檔案 Background 仍歸程式碼所有 |
| **Test Steps** | `automated` 時必填 | 場景動作 | 每個換行一個詞彙短語;首行渲染為 `When`,其餘渲染為 `And` |
| **Expected Result** | `automated` 時必填 | 場景斷言 | 每個換行一個詞彙短語;首行渲染為 `Then`,其餘渲染為 `And` |
| **Estimated Runtime (s)** | 推薦正整數 | 規劃 | 存在時驗證;不渲染 |

不要按分號拆開步驟:備註和訊息中可能合理包含分號。Excel 儲存格使用換行分隔的短語,**不**含 `Given`/`When`/`Then`/`And` 關鍵字;渲染器會確定性地加上關鍵字和縮排。

**Automation Status 規則**:
- `manual` / `candidate`:當沒有託管 feature 區塊存在時忽略。如果該 ID 已經在 feature 中,直接報錯並要求明確轉換為 `deprecated`;絕不默默刪除可執行覆蓋。
- `automated`:新增或更新路由到的託管區塊。
- `deprecated`:要求 `App Version Deprecated` 與已有的託管區塊;棄用一個從未產生過的 ID 是錯誤。保留 metadata 註解的可解析性,但在確定性的 `DEPRECATED BEGIN/END <ID>` 標記之間把 tags、Scenario 行、body 註解掉。不要從缺失的行推斷棄用。
- workbook 中缺失的託管 feature ID 是硬錯誤。缺失的 Excel 行絕不意味著刪除。

規範的棄用形式:

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

**引導資料對齊(首次套用前的強制步驟)**:
- 把 `data/test_cases_template.xlsx` 複製為 `data/test_cases.xlsx`;工作登記冊是 Task 14 的輸入。
- 在產生 feature 前,先更新全部 7 列以與 §6.7 完全一致。原範本是早期草稿:它包含 `Coffee` 而非 `baby cost`、舊的複合 `user adds ...` 短語、缺失的 tag/date 動作,以及不完整的持久化/月度彙總斷言。校正後的基準使用 `Platform=both`,因為全部 7 個場景都已經在 Android 與 iOS 模擬器上通過。
- 保留範本作為可複用範例,但也把它更新為同一份校正後的七列基準,以便新的副本不會重新引入偏差。

### 11.4 同步引擎介面(`scripts/sync_engine.py`)

已實作的引擎透過 Module 白名單路由列,並只更新對應的託管 feature 區塊。

安全的執行模式:

```bash
# 預設:僅校驗 + diff;不寫入。當存在 drift 時退出碼 1。
uv run python scripts/sync_engine.py --check

# 完整校驗後明確變更
uv run python scripts/sync_engine.py --apply

# 套用,然後僅執行新增/修改的活動場景
uv run python scripts/sync_engine.py --apply --run-changed

# 跨裝置健康門控:檢查、套用,然後把變更複製到所有裝置
./scripts/run_changed_matrix.sh

# 僅本地監聽;變更仍需要 --apply
uv run python scripts/sync_engine.py --watch --apply

# 用於測試/本地實驗的選用非預設登記冊路徑
uv run python scripts/sync_engine.py --check --input /path/to/test_cases.xlsx
```

未提供 `--check` 或 `--apply` 時,預設使用 `--check`。`--check`、`--apply` 與機器可讀的 `--list-changed` 互斥。`--run-changed` 需要 `--apply`;它在成功收集後,執行新增/修改活動場景的精確 pytest node ID。`scripts/run_changed_matrix.sh` 消費 `--list-changed`,預覽裝置並套用一次變化,再由矩陣 Runner 負責檢查/啟動 Appium，並在矩陣 `replicate` 模式下執行精確的變更子集,使每個被選裝置都校驗每個變更案例。`--watch` 在沒有 `--apply` 時僅報告 drift。Diff 類別為 `added`、`modified`、`deprecated`、`unchanged` 與 `errors`;沒有隱式的 `deleted` 類別。

退出碼:
- `0`:合法且無 drift(`--check`),或套用成功且寫入後收集通過。
- `1`:合法但 `--check` 模式下存在 drift。
- `2`:schema、重複、路由、解析、I/O、鎖、渲染或寫入後收集錯誤。

### 11.5 校驗、事務安全與回滾

引擎必須在首次寫入前完成所有 workbook 與 feature 校驗:

- 必需的標頭與必需的行值;
- ID 格式/唯一性與 feature ID 唯一性;
- 允許的 Module、status、priority、platform 與 tag 語法;
- 對 `automated` 列,Test Steps / Expected Result 非空且按換行分隔;
- 每個 `automated`/`deprecated` 列恰好路由到一個 feature;
- workbook 中不缺少任何託管 feature ID;
- 初始 ID 遷移之後沒有未託管的 `Scenario:`;
- 同一 module 內場景標題不重複;
- UTF-8 feature 解碼與每個檔僅偵測一種換行風格。

Apply 是一次盡力而為的跨所有受影響 feature 檔的事務(Python/OS 無法在一次操作中原子地取代多個檔):

1. 原子地取得 `data/.backup/sync.lock`;儲存 PID/時間戳,若存在並發 apply/watch 寫入器則失敗。僅在確認 PID 不再執行後,手動移除陳舊的鎖。
2. 在記憶體中完整渲染每個目標檔案。透過精確的字串切片,保留原始 UTF-8 編碼、換行風格、程式碼擁有的前綴,以及每一個未變更的託管區塊。
3. 在**每次**變更型 apply 之前,把帶微秒時間戳的備份寫到 `data/.backup/<feature>.<YYYYMMDDTHHMMSSffffff>.bak`。絕不重用「每天一次」的備份名。
4. 把每個渲染後的檔寫到同一目錄下的暫存檔,flush 後使用 `os.replace()`;不允許直接對目標執行 `Path.write_text()`。
5. 在所有取代完成後,執行一次 `[sys.executable, "-m", "pytest", "--collect-only", "-q"]`。
6. 若任何取代或收集失敗,從該次執行的備份還原所有受影響檔案,報告原始錯誤與回滾狀態,然後以 `2` 退出。
7. 始終在 `finally` 中刪除暫存檔並釋放鎖。在多個 `os.replace()` 呼叫之間發生的進程被殺/斷電日誌不在範圍內。

引擎永不編輯任一 workbook。`data/.backup/` 仍被 gitignore。Watch 模式使用 `watchdog`,debounce 5 秒,呼叫相同的已校驗事務;它不是一條獨立的寫入路徑。

**位元一致保證**意謂,在成功 apply 前後,每個 `unchanged` 託管區塊的編碼位元切片具有相同的 SHA-256。它並不意謂修改過的區塊或其周圍必要的分隔符保持不變。

### 11.6 測試與驗收標準

**涉及檔案**:`scripts/sync_engine.py`、`scripts/run_changed_matrix.sh`、`scripts/run_device_matrix.py`、`data/test_cases.xlsx`、`data/test_cases_template.xlsx`、兩個 feature 檔(初始 ID/metadata)、`tests/unit/test_sync_engine.py`、`unit_tests/test_run_device_matrix.py`、`.github/workflows/ci.yml`,以及僅在 Task 13 的 `unit` 隔離 marker 尚未存在時的 `conftest.py` / `pytest.ini`。

所有同步測試都使用暫存 workbook/feature 副本。它們**絕不能**修改倉庫的 feature 檔或登記冊。

驗收標準:

- 解析校正後的登記冊,精確回傳 7 條 `automated` 列,路由為 5 條 `add_transaction` 與 2 條 `transactions` 案例。
- 初始 Task 14 feature 檔包含 §11.2 中的 7 個唯一 ID,仍能收集到同樣的 7 個 BDD 場景。
- 在已提交的狀態上,`uv run python scripts/sync_engine.py --check` 退出 `0` 且零寫入。
- 在暫存副本中修改 Excel 的某個金額/標題/步驟,會精確報告正確 module 中的 1 個 `modified` 區塊;另一個 feature 檔保持位元一致。
- 執行兩次 `--apply` 是冪等的:第二次執行報告無 drift,兩個 feature 檔的雜湊保持不變。
- 單元測試涵蓋重複 ID(Excel 內與跨 feature)、未知 Module、非法列舉/必填欄位、tag 規範化、狀態轉換、缺失的 workbook ID、不支援的 Scenario Outline,以及換行保留。
- 強制產生的寫入後收集失敗會還原所有受影響檔案,且不留下鎖/暫存檔。
- SHA-256 斷言證明,在相鄰的 add/modify/deprecate 操作之後,未觸及的託管區塊位元一致。
- Workbook 雜湊在所有模式下都保持不變,包括 `--apply` 與 `--watch`。
- `--apply --run-changed` 僅執行新增/修改的活動場景,報告它們的 ID 與 Allure 路徑,並在執行失敗時列印一條精確的重試命令以及程式碼/locator 除錯範圍。
- `scripts/run_changed_matrix.sh` 僅在無可執行的 drift 或每個變更案例在每個被選裝置上都通過時才回傳 `0`;矩陣彙總保留變更種類、穩定案例 ID、環境、裝置、OS、UDID 與每個裝置的健康狀況。
- Task 14 落地後,CI 的 `validate` 任務在 pytest 收集之前執行 `uv run python scripts/sync_engine.py --check`。
- 完整驗證通過:同步單元測試、7 個 BDD 場景被收集,以及 `git diff --check` 乾淨。

### 11.7 PoC 範圍之外

- 雙向同步或將 `Last Run Result` 寫回 Excel。
- 基於缺失行的自動刪除。
- 自動建立 PR/分支或由腳本提交。
- 多 workbook 合併與衝突解決。
- Scenario Outline / Examples 產生。
- LLM 產生列提議(見 `docs/SCALING.md` §4)。
- 在 CI 中監聽檔案;`--watch` 僅用於本地開發。

### 11.8 參考

更廣的 Q1-Q6 路線圖、版本感知迴歸與文件驅動測試上下文,見 [`docs/SCALING.md`](SCALING.md)。在 Task 14 實作時閱讀;它不阻塞 Tasks 1-12。

---

*TECHNICAL_SPEC.md 完 —— 在撰寫任何程式碼之前,先通讀本文件。*
