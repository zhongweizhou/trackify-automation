# Trackify Automation — Technical Specification (TECHNICAL_SPEC.md)

> **Audience**: Codex / Claude Code (the implementer)
> **Purpose**: Define **how** to build what `README.md` describes.
> **Do NOT change scope here** — scope lives in `README.md` and `Feature_Inventory.md`.
> **This document defines HOW.**

---

## 1. Tech Stack (pinned versions)

| Component | Version | Why |
|-----------|---------|-----|
| Python | 3.11+ | Type hints + async/await |
| pytest | 8.x | BDD runner |
| pytest-bdd | 7.x | Gherkin → pytest steps |
| Appium | 3.x | Cross-platform mobile driver |
| Appium UiAutomator2 Driver | latest | Android driver |
| Appium XCUITest Driver | latest | iOS (extension only) |
| Selenium-Python | 4.x | Underlying Appium dependency |
| allure-pytest | 2.x | Allure reporter |
| pyyaml | 6.x | Locator YAML parser |
| openpyxl | 3.x | Excel sync engine (Task 14) |
| watchdog | 4.x | File-system events for sync trigger (Task 14) |
| uv | latest | Fast Python package manager |
| Allure CLI | latest | Report renderer |

> ❌ **Do NOT add**: Poetry, pipenv, conda, Docker, Flake8, Black, MyPy, Pylint, Pre-commit hooks, **gherkin (Python lib)** (use regex for the sync PoC — see §11). Anything outside the list above is scope creep.

---

## 2. Directory Structure (immutable)

```
trackify-automation/
├── README.md                        # Public scope (for evaluator)
├── TECHNICAL_SPEC.md                # This file (for Codex)
├── pyproject.toml                   # uv-managed Python deps
├── pytest.ini                       # BDD + markers config
├── conftest.py                      # Global fixtures (appium driver, db reset)
│
├── docs/
│   ├── Feature_Inventory.md         # Day 1 manual exploration
│   ├── DESIGN.md                    # Architecture rationale
│   ├── TECHNICAL_SPEC.md            # This file
│   ├── SCALING.md                   # Q1-Q6 strategic roadmap (long-term, non-blocking)
│   └── REFLECTION.md                # Post-mortem (Day 5)
│
├── app/                             # NOT committed
│   ├── app-release.apk
│   └── Runner.app
│
├── tests/
│   ├── features/                    # Gherkin files (BDD)
│   │   ├── add_transaction.feature
│   │   └── transactions.feature
│   ├── step_defs/                   # pytest-bdd step implementations
│   │   ├── __init__.py
│   │   ├── add_transaction_steps.py
│   │   └── transactions_steps.py
│   └── __init__.py
│
├── locator/                         # YAML files (one per page)
│   ├── onboarding.yaml
│   ├── home.yaml
│   ├── add_transaction.yaml
│   └── transactions.yaml
│
├── page/                            # Page Object Pattern
│   ├── __init__.py
│   ├── base_page.py                 # Abstract — all pages extend
│   ├── onboarding_page.py
│   ├── home_page.py
│   ├── add_transaction_page.py
│   └── transactions_page.py
│
├── flow/                            # Business logic (calls Page)
│   ├── __init__.py
│   ├── app_setup_flow.py
│   ├── add_transaction_flow.py
│   └── transactions_flow.py
│
├── utils/                           # Cross-cutting helpers
│   ├── __init__.py
│   ├── driver.py                    # Appium driver factory
│   ├── locator_loader.py            # YAML → dict
│   └── config.py                    # Reads platform / device from pytest.ini
│
├── ai/                              # AI-assisted modules (Day 4)
│   ├── __init__.py
│   ├── gen_cases.py                 # LLM-drafted BDD case ideas
│   └── triage.py                    # LLM-based failure categorizer
│
├── data/
│   ├── test_data.yaml               # Fixture rows for tags / notes / categories
│   ├── test_cases.xlsx              # Manual test case registry (Task 14 — sync source)
│   └── .backup/                     # Auto-created by sync_engine.py before each write
│
├── scripts/
│   └── sync_engine.py               # Excel ↔ .feature diff/apply (Task 14 PoC)
│
├── report/
│   ├── allure-results/              # Generated each run
│   ├── screenshots/                 # Generated on failure
│   └── summary.xlsx                 # One-glance pass/fail
│
└── assets/
    └── run_demo.mp4                 # Screen recording of a successful run
```

**Rules**:
- ❌ Never put test files in the project root.
- ❌ Never put Page / Flow / Driver code in `tests/`.
- ❌ Never hardcode paths; use `pathlib.Path(__file__).parent`.

---

## 3. Coding Conventions (strict)

### 3.1 Type Hints (mandatory)

```python
# ✅ GOOD
def click_add_expense(self) -> None:
    self._driver.click(self._loc("add_expense_button"))

# ❌ BAD
def click_add_expense(self):
    self._driver.click(self._loc("add_expense_button"))
```

All public methods MUST have:
- Parameter types
- Return type

### 3.2 Docstrings (Google style, mandatory on public classes/functions)

```python
def add_expense(amount: float, category: str, note: str = "") -> str:
    """Add an expense transaction and return the new transaction ID.

    Args:
        amount: The transaction amount (positive value; sign is implied by type).
        category: Category name (must exist in settings).
        note: Optional free-text note.

    Returns:
        The ID of the newly created transaction.
    """
    ...
```

### 3.3 Naming

| Element | Convention | Example |
|---------|------------|---------|
| Class | PascalCase | `AddTransactionPage` |
| Function / method | snake_case | `add_expense_transaction` |
| Constant | UPPER_SNAKE | `DEFAULT_TIMEOUT = 10` |
| Private (internal) | `_leading_underscore` | `_driver` |
| File | snake_case.py | `add_transaction_page.py` |
| YAML key | snake_case | `add_expense_button:` |

### 3.4 Imports

```python
# ✅ GOOD — three groups, stdlib first, blank lines between
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
# ❌ BAD — local imports before third-party, no blank lines, star import
from page.base_page import BasePage
from appium.webdriver import *
import pytest
from utils.locator_loader import load_locator
```

**Why order matters here**:
- isort / ruff auto-fix tools flag out-of-order imports as errors — keeping the order manual from day 0 prevents churn later.
- Star imports (`from X import *`) break grep-ability and hide unused-import lints.

---

## 4. Locator Strategy (YAML-only)

### 4.1 Format

`locator/<page>.yaml` — one file per page:

```yaml
# locator/add_transaction.yaml

add_expense_button:
  description: "Button on Home page to open Add Transaction modal"
  android:
    accessibility_id: "Add Expense"
  ios:
    accessibility_id: "Add Expense"

amount_input:
  description: "Numeric input for transaction amount"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

transaction_type_toggle:
  description: "Tabs to switch between Expense / Income / Transfer"
  android:
    xpath: "//*[@resource-id='com.blixcode.trackify:id/transaction_type_toggle']"
  ios:
    predicate: "type == 'XCUIElementTypeOther' AND name == 'Transaction Type'"
```

**Full yaml template** (use as starting point for each new page):

```yaml
# locator/add_transaction.yaml — reference skeleton

# ---- Type toggle (Expense / Income / Transfer) ----
type_toggle_expense:
  description: "Tab to select Expense type"
  android:
    accessibility_id: "Expense"
  ios:
    accessibility_id: "Expense"

type_toggle_income:
  description: "Tab to select Income type"
  android:
    accessibility_id: "Income"
  ios:
    accessibility_id: "Income"

type_toggle_transfer:
  description: "Tab to select Transfer type"
  android:
    accessibility_id: "Transfer"
  ios:
    accessibility_id: "Transfer"

# ---- Amount ----
amount_input:
  description: "Numeric input for transaction amount (supports decimals)"
  android:
    accessibility_id: "Amount"
  ios:
    accessibility_id: "Amount"

# ---- Category ----
category_dropdown:
  description: "Dropdown to pick an existing category"
  android:
    accessibility_id: "Category"
  ios:
    accessibility_id: "Category"

category_option_food:
  description: "Category option labelled 'Food' in dropdown list"
  android:
    xpath: "//*[contains(@content-desc, 'Food')]"
  ios:
    predicate: "label == 'Food'"

new_category_button:
  description: "New tile at the far right of the horizontal category list"
  android:
    accessibility_id: "New"
  ios:
    accessibility_id: "New"

manage_categories_title:
  description: "Manage Categories page opened from the New tile"
  android:
    accessibility_id: "Manage Categories"
  ios:
    accessibility_id: "Manage Categories"

add_category_button:
  description: "Open the New Category form"
  android:
    accessibility_id: "Add Category"
  ios:
    accessibility_id: "Add Category"

custom_category_name_input:
  description: "Text input for the custom category name"
  android:
    xpath: "//android.widget.EditText[@hint='Category Name']"
  ios:
    xpath: "//XCUIElementTypeTextField[@placeholderValue='Category Name']"

# ---- Date ----
date_picker_trigger:
  description: "Tap to open native date picker"
  android:
    accessibility_id: "Pick date"
  ios:
    accessibility_id: "Pick date"

# ---- Notes / Tags ----
notes_input:
  description: "Free-text notes (also serves as tags, comma-separated)"
  android:
    accessibility_id: "Notes"
  ios:
    accessibility_id: "Notes"

# ---- Actions ----
save_button:
  description: "Submit the transaction"
  android:
    accessibility_id: "Save"
  ios:
    accessibility_id: "Save"

cancel_button:
  description: "Discard and close the modal"
  android:
    accessibility_id: "Cancel"
  ios:
    accessibility_id: "Cancel"

# ---- Validation ----
amount_error_message:
  description: "Inline error when amount is empty or invalid"
  android:
    xpath: "//*[contains(@text, 'required') or contains(@text, 'invalid')]"
  ios:
    predicate: "type == 'XCUIElementTypeStaticText' AND (label CONTAINS 'required' OR label CONTAINS 'invalid')"
```

**Rules**:
- ✅ Each entry MUST have `description` (human-readable purpose).
- ✅ At minimum, populate `android.accessibility_id` (Flutter renders semantic IDs as accessibility labels).
- ⚠️ XPath is fallback — only use if no accessibility_id exists.
- ❌ Never hardcode Locators in Python files.

### 4.2 Locator Loader (utils/locator_loader.py)

```python
"""Locator loader with strategy fallback chain (§4.3)."""

from pathlib import Path
import yaml

# Order matters — first match wins. See §4.3.
_STRATEGY_PRIORITY = ("accessibility_id", "id", "xpath", "predicate")

# Module-level cache: (page, key, platform) -> (strategy, value)
_cache: dict[tuple[str, str, str], tuple[str, str]] = {}


def load_locator(page: str, key: str, platform: str = "android") -> tuple[str, str]:
    """Return (strategy, value) for the requested locator.

    Walks the priority chain in §4.3. Raises KeyError if no strategy matches.

    Usage in Page:
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
    """Test-only: drop the cache so locators are re-read from YAML."""
    _cache.clear()
```

**Why a fallback chain, not strict `accessibility_id`:**
The §4.1 example shows `transaction_type_toggle` has no accessibility_id on Android (only `xpath`). A strict `entry[platform]["accessibility_id"]` lookup would `KeyError`. Walking `_STRATEGY_PRIORITY` keeps the loader robust as the YAML grows.

### 4.3 Strict priority order

1. `accessibility_id` (Flutter semantic label) — **preferred**
2. `id` / `resource-id`
3. `class` chain
4. `xpath` (last resort)
5. `predicate` (iOS only)

---

## 5. Architecture Layers

```
┌─────────────────────────────────────────┐
│  tests/features/*.feature               │  Gherkin (human language)
└──────────────────┬──────────────────────┘
                   │ pytest-bdd discovers
                   ▼
┌─────────────────────────────────────────┐
│  tests/step_defs/*_steps.py             │  Step implementations
│  (Given/When/Then → calls Flow)         │
└──────────────────┬──────────────────────┘
                   │ calls
                   ▼
┌─────────────────────────────────────────┐
│  flow/*_flow.py                         │  Business logic
│  (Use case orchestration)               │
└──────────────────┬──────────────────────┘
                   │ uses
                   ▼
┌─────────────────────────────────────────┐
│  page/*_page.py                         │  Page Object
│  (UI element actions)                   │
└──────────────────┬──────────────────────┘
                   │ inherits
                   ▼
┌─────────────────────────────────────────┐
│  page/base_page.py                      │  Abstract base
│  (click, input, swipe, wait, screenshot)│
└──────────────────┬──────────────────────┘
                   │ uses
                   ▼
┌─────────────────────────────────────────┐
│  utils/driver.py                        │  Appium wrapper
│  (No raw driver.find_element outside)   │
└──────────────────┬──────────────────────┘
                   ▼
               Appium → Trackify App
```

**Layer rules**:
- ❌ Step defs never import `page.*` directly — they go through Flow.
- ❌ Flow never imports `utils.driver` directly — it calls Page methods only.
- ❌ Page never imports other Pages — keep them independent.
- ✅ Base page exposes primitives: `click`, `input_text`, `swipe`, `wait_for`, `screenshot`, `is_visible`.

### 5.1 Fixture Wiring (conftest.py)

The driver and every Page / Flow instance MUST be injected via pytest fixtures — never instantiated inside a step body. This keeps the teardown path single-source.

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

PKG = "com.blixcode.trackify"  # Trackify Android package id


@pytest.fixture(scope="session")
def driver() -> WebElement:
    """Session-scoped Appium driver — one session per pytest run."""
    platform = os.getenv("PLATFORM", "android")
    factory = AppiumDriverFactory(platform=platform)
    d = factory.create()
    yield d
    d.quit()


@pytest.fixture(autouse=True)
def reset_app_state(driver):
    """Wipe Hive DB before every test for deterministic state.

    Why `pm clear` (not a seed file):
    - Trackify stores data in Hive at /data/data/<pkg>/app_flutter/hive_box.db.
    - Clearing via Settings UI is flaky and order-dependent.
    - `pm clear` is one ADB call, runs in <1s, and is the official reset path.
    """
    subprocess.run(["adb", "shell", "pm", "clear", PKG], check=True, timeout=10)
    driver.launch_app()  # relaunch after clear
    yield


# Page fixtures — thin wrappers, lazily constructed per test
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

# Flow fixtures — compose pages
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

**Why fixture wiring matters**:
- Without it, step defs end up calling `HomePage(driver())` themselves → no teardown, leaked sessions.
- The `reset_app_state` fixture is `autouse=True` so every test starts from a clean Hive.
- After reset, every feature `Background` completes the same three ordered first-run stages before business actions begin: save name `Kimbal`; select `$ US Dollar` and monthly budget `30000`; enable Bank SMS Reader and tap `Get Started`.
- Never use onboarding `Skip` as a test precondition. Skipping leaves profile, currency, budget, and tracking preferences undefined.

---

## 6. BDD Conventions (pytest-bdd)

### 6.1 File naming

- One `.feature` per page/feature.
- One `_steps.py` per `.feature`, with matching name.

### 6.2 Scenario tags (pytest markers)

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

### 6.3 Step function reuse

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

**Rules**:
- ✅ Parameterize with `parsers.parse(...)` — avoid hardcoded strings in steps.
- ✅ Reuse steps across scenarios; don't duplicate logic.
- ❌ No inline assertions in step bodies — only in `Then` steps.

### 6.4 pytest markers (pytest.ini)

```ini
[pytest]
# ---- discovery ----
testpaths = tests
bdd_features_base_dir = tests/features
python_files = *_steps.py test_*.py
python_classes = Test*
python_functions = test_*

# ---- markers (v3 scope) ----
markers =
    smoke: P0 critical path
    regression: P0 + P1 full coverage
    p0: critical priority
    p1: high priority
    custom_category: 自定义类别流程（在 Add Transaction 内新增 category）
    filter: 列表筛选（Transactions 按 type / category / 日期）
    grouping: 列表按日期分组（Transactions 列表展示）

# ---- output ----
addopts = -ra --strict-markers --tb=short
```

**Field-by-field why**:

| Field | Why it's there |
|-------|----------------|
| `testpaths` | Limits collection to `tests/` — prevents picking up `page/`, `flow/`, `utils/` modules accidentally |
| `bdd_features_base_dir` | pytest-bdd needs to know where `.feature` files live; without it, feature paths in collected IDs are wrong |
| `python_files = *_steps.py` | pytest-bdd requires step files to end in `_steps.py`; the glob forces this even if a developer names one `add_transaction.py` |
| `--strict-markers` | Typos like `@smoek` raise an error instead of being silently ignored — catches marker mistakes early |
| `--tb=short` | Traceback truncated to one frame per failure — keeps the Allure report scannable |

**Marker mapping for v3 scope** (7 BDD scenarios):

| Marker | Scenarios |
|--------|-----------|
| `@smoke @p0` | Add Expense, Add Income, Add Transfer, Validation (empty amount) |
| `@p1` | Custom Category, Filter by type, Group-by-date |

### 6.5 Gherkin Style Guide

Without these rules, each scenario reads like an independent AI generation. Codex MUST follow all of them:

| Rule | Why |
|------|-----|
| **Third person, present simple** — "user taps Save", not "I tap Save" or "user tapped Save" | Matches pytest-bdd step regex defaults; consistent tense prevents step_defs duplication |
| **Use "user" (not "the user" / "users" / "I")** | One token to grep across all .feature files |
| **Same action = same wording everywhere** — if one scenario uses "user enters amount", every scenario uses "user enters amount" | Step matching is exact-string; verb drift = "step definition not found" |
| **Use `Scenario Outline` + `Examples` for data-driven cases**; only use `Scenario` when the case is truly unique | Reduces .feature line count; lets one step_def power N scenarios |
| **Common setup goes in `Background`** — every feature file starts with one `Background:` block; do not repeat "user is on X page" inside each Scenario | DRY; one place to edit when preconditions change |
| **`Then` MUST include both**: (a) a **specific value assertion** AND (b) a **negative assertion** ("X did NOT happen") | Catches regressions where the wrong transaction gets saved; protects against over-broad matching |
| **One feature = one user journey** — `add_transaction.feature` covers all 3 transaction types + validation + custom category (5 scenarios); `transactions.feature` covers filter + grouping (2 scenarios) | Each .feature file = one reviewer mental model |
| **Use `And` / `But` to chain steps within the same clause** — don't repeat `Given` / `When` / `Then` | Standard Gherkin readability |

**Anti-patterns to reject in review**:

```gherkin
# ❌ BAD — first person + past tense + "the user"
Given I was on the Home page

# ❌ BAD — three different verbs for the same action across scenarios
# In scenario A:
When user enters amount "100"
# In scenario B:
When user inputs amount "200"
# In scenario C:
When user types amount "300"

# ❌ BAD — vague Then without specific value or negative check
Then the transaction is saved

# ❌ BAD — repeating Background as Given in each scenario
Scenario: Add expense
  Given app is launched with clean database
  And user is on the Home page
  When ...
Scenario: Add income
  Given app is launched with clean database
  And user is on the Home page
  When ...
```

### 6.6 Step Vocabulary Contract

**This is a contract**: `step_defs/*_steps.py` MUST implement every phrase below, and every `.feature` file MUST use only these phrases. Adding a new phrase requires adding both the Gherkin usage AND the Python step in the same commit.

#### Given phrases (3 page contexts + 4 Background steps)

```gherkin
# Used once per .feature file in a Background: block
Given app is launched with a clean database
Given user enters name "<name:str>" and continues
Given user selects currency "<currency:str>" and sets monthly budget "<monthly_budget:int>"
Given user enables Bank SMS Reader and gets started

Given user is on the Home page
Given user is on the Add Transaction page
Given user is on the Transactions page
```

#### When phrases (10 actions)

```gherkin
When user selects type "<type:str>"                  # type ∈ {expense, income, transfer}
When user enters amount "<amount:float>"
When user leaves amount empty
When user selects category "<category:str>"
When user enters note "<note:str>"
When user taps Save
When user taps Cancel
When user taps "Add new category"
When user creates custom category "<name:str>"
When user filters transactions by type "<type:str>"  # type ∈ {expense, income, transfer}
```

#### Then phrases (6 assertions)

```gherkin
Then transaction appears in Recent transactions with amount "<amount:float>"
Then error message "<message:str>" is shown for amount
Then no transaction appears in Recent transactions
Then no transaction appears in Recent transactions with category "<category:str>" missing
Then only transactions of type "<type:str>" are shown
Then transactions are grouped by date with section headers
```

**Parsing rules** (used by `parsers.parse(...)` in step_defs):

| Placeholder | Type | Example value | Validation |
|-------------|------|---------------|------------|
| `<type:str>` | `str` | `"expense"` | Must be one of `expense`, `income`, `transfer` (asserted in Flow, not step) |
| `<amount:float>` | `float` | `100.0`, `9.99` | Must be `> 0` (asserted in Flow) |
| `<category:str>` | `str` | `"Food"`, `"Transport"` | Free text |
| `<note:str>` | `str` | `"breakfast with Dinna"` | Free text |
| `<name:str>` | `str` | `"baby cost"` | Free text |
| `<currency:str>` | `str` | `"$ US Dollar"` | Full visible option label |
| `<monthly_budget:int>` | `int` | `30000` | Must be a positive whole number and match the displayed slider value |
| `<message:str>` | `str` | `"Amount is required"` | Substring match against displayed text |

→ **Where these phrases are actually used**: see §6.7 Scenario Inventory v3. Each scenario there is built by combining a subset of these phrases. If §6.7 needs a phrase not listed here, add it here FIRST, then update the scenario in the same commit.

### 6.7 Scenario Inventory v3 (source of truth for §7 Tasks 8 / 8b / 10)

The 7 scenarios below are the **single source of truth**. §7 Task 8 / 8b / 10 ACs reference this list by exact title.

#### `tests/features/add_transaction.feature` — 5 scenarios

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
    And user taps Save
    Then transaction appears in Recent transactions with amount "100.0"

  @smoke @p0
  Scenario: Add income happy path
    When user taps "Add Income"
    And user enters amount "5000"
    And user selects category "Salary"
    And user taps Save
    Then transaction appears in Recent transactions with amount "5000.0"

  @smoke @p0
  Scenario: Add transfer happy path
    When user taps "Add Transfer"
    And user enters amount "200"
    And user selects category "Food"
    And user taps Save
    Then transaction appears in Recent transactions with amount "200.0"

  @smoke @p0
  Scenario: Validation — empty amount shows error and does not save
    When user taps "Add Expense"
    And user leaves amount empty
    And user selects category "Food"
    And user taps Save
    Then error message "Amount is required" is shown for amount
    And no transaction appears in Recent transactions

  @p1 @custom_category
  Scenario: Add expense with new custom category created in flow
    When user taps "Add Expense"
    And user enters amount "50"
    And user taps "Add new category"
    And user creates custom category "baby cost"
    And user taps Save
    Then transaction appears in Recent transactions with amount "50.0"
    And no transaction appears in Recent transactions with category "baby cost" missing
```

Implementation notes for the current Android build:
- The Gherkin phrase `user taps "Add new category"` maps to a left swipe on the horizontal Category list, followed by `New` → `Add Category`.
- `baby cost` uses the New Category form's default icon and color. Its fixed-width transaction chip exposes the shortened label `baby`, but Manage Categories and the saved Home transaction retain the full name.
- Empty amount submission remains on Add Transaction with an empty field and saves nothing. The build does not expose the expected validation copy to accessibility, so the assertion prefers visible copy and otherwise verifies that rejected form state before checking the Home list is empty.

#### `tests/features/transactions.feature` — 2 scenarios

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
    When user adds an expense "100" with category "Food"
    And user adds an income "5000" with category "Salary"
    And user navigates to the Transactions page
    And user filters transactions by type "expense"
    Then only transactions of type "expense" are shown

  @p1 @grouping
  Scenario: Transactions grouped by date with section headers
    When user adds an expense "100" with category "Food"
    And user navigates to the Transactions page
    Then transactions are grouped by date with section headers
```

> ⚠️ **Note for Codex**: the two "user adds an expense X with category Y" lines in `transactions.feature` Background setup rely on the `When user taps "Add Expense" → enters amount → selects category → taps Save` chain from §6.6. If §6.6 phrases change, update both feature files in the same commit.

**Why this inventory is here, not just in Feature_Inventory.md**:
- Feature_Inventory.md is the **what** (which features, why chosen).
- TECHNICAL_SPEC.md §6.7 is the **how** (exact scenario titles, tags, Given/When/Then lines).
- Keeping both lets the evaluator read Feature_Inventory.md for scope rationale and Codex read §6.7 for implementation.

---

## 7. Implementation Task List (13 tasks, one commit each)

> ⚠️ **Do NOT execute any task before its predecessors are committed and `pytest` runs cleanly (or no tests exist yet).**

### Day 0 — Manual Prerequisites (no commit, one-time)

These run once on the developer's machine before Task 1. They produce no commit.

```bash
# 1. Appium server toolchain
npm install -g appium                              # CLI
appium driver install uiautomator2                 # Android driver

# 2. Start Appium server (background)
appium &                                           # listens on :4723

# 3. Verify the server is alive
curl http://localhost:4723/status | jq .           # expects {"value":{"ready":true}}

# 4. Verify the emulator + app package
adb devices                                        # list attached devices
adb install -r -t app/app-release.apk              # install Trackify
adb shell pm list packages | grep com.blixcode.trackify # confirm pkg present
```

**If any of these fail, fix before Task 1.** The Day 0 failures (server not running, package missing) are the #1 cause of "pytest hangs forever" symptoms later — not real bugs.

| # | Task | Files touched | Acceptance criteria | Commit message |
|---|------|---------------|---------------------|----------------|
| 1 | Project bootstrap | `pyproject.toml`, `pytest.ini`, `conftest.py`, `.gitignore` | `pytest --collect-only` exits 0; `conftest.py` includes the `reset_app_state` autouse fixture from §5.1 (calls `adb shell pm clear com.blixcode.trackify` before every test) | `chore: bootstrap project` |
| 2 | Base page | `page/base_page.py` | Importing `BasePage` works | `feat(page): base page with click/wait/screenshot` |
| 3 | Driver factory | `utils/driver.py`, `utils/config.py` | `AppiumDriverFactory(platform="android").create()` returns a live Appium session; class name avoids collision with `selenium.webdriver.Driver`; consumed by `driver` fixture in §5.1 | `feat(utils): appium driver factory` |
| 4 | Locator loader | `utils/locator_loader.py`, `locator/home.yaml` (skeleton) | `load_locator("home", "x", "android")` returns string | `feat(utils): yaml locator loader + skeleton` |
| 5 | Home page + Locator | `page/home_page.py`, `locator/home.yaml` | `home.click_add_expense()` works against manual Appium session | `feat(page): home page (Add Transaction shortcut)` |
| 6 | Add Transaction page + Locator | `page/add_transaction_page.py`, `locator/add_transaction.yaml` | `add_tx.add_expense(amount=100, category="Food")` works | `feat(page): add transaction page (all 3 types)` |
| 7 | Add Transaction flow | `flow/add_transaction_flow.py`, `data/test_data.yaml` | `flow.add_expense(...)` orchestrates Page + returns new ID | `feat(flow): add transaction business logic` |
| 8 | First BDD feature (Add Expense happy path) | `tests/features/add_transaction.feature`, `tests/step_defs/add_transaction_steps.py`, `conftest.py` (page/flow fixtures) | `pytest tests/features/add_transaction.feature -k "happy_path"` collects and runs **only** the "Add expense happy path" scenario from §6.7. Other 4 Add Transaction scenarios written but tagged `@skip` (or feature-level Background-only). Implements every §6.6 phrase used in this scenario. | `test(case): add transaction bdd (expense happy path)` |
| 8a | First-run setup baseline | `locator/onboarding.yaml`, `page/onboarding_page.py`, `flow/app_setup_flow.py`, `conftest.py`, BDD `Background` blocks | Every business scenario completes `Kimbal` → `$ US Dollar` + `30000` → Bank SMS Reader enabled + `Get Started`; no test path taps onboarding `Skip`; Home shows `Kimbal` and `$` before business actions | `feat(setup): complete required first-run configuration` |
| 8b | Remaining Add Transaction scenarios | `tests/features/add_transaction.feature`, `tests/step_defs/add_transaction_steps.py` | Un-skip the remaining **4 scenarios** from §6.7 (Add Income, Add Transfer, Validation, Custom Category). Implement the additional §6.6 phrases (`user selects type`, `user taps "Add new category"`, `user creates custom category`, `error message ... is shown for amount`, `no transaction appears ...`). Custom Category creates and selects `baby cost` with any icon/color. All **5 Add Transaction scenarios** pass. | `test(case): add transaction bdd (4 more scenarios + custom category)` |
| 9 | Transactions page + flow | `page/transactions_page.py`, `flow/transactions_flow.py`, `locator/transactions.yaml` | Manual test: filter + group-by-date works | `feat(page): transactions page + flow` |
| 10 | Transactions BDD | `tests/features/transactions.feature`, `tests/step_defs/transactions_steps.py` | Both Transactions scenarios from §6.7 collect and run: filter by type (`@filter`), group-by-date (`@grouping`). Implement the additional §6.6 phrases (`user filters transactions by type`, `only transactions of type ... are shown`, `transactions are grouped by date ...`). **Total project: 5 Add Transaction + 2 Transactions = 7 scenarios**. | `test(case): transactions bdd (2 scenarios)` |
| 11 | Allure + Summary + Screenshot on fail | `conftest.py` (add `pytest_runtest_makereport` hook + Allure fixture), `report/summary.xlsx` generator | `pytest --alluredir=./allure-results` produces results; on `call` failure the hook saves PNG to `report/screenshots/<test_name>.png` and attaches it to Allure — **do NOT wrap test bodies in try/except** (see §8 anti-patterns). Hook pattern: `pytest.hookimpl(tryfirst=True, hookwrapper=True) def pytest_runtest_makereport(item, call)` that yields and inspects `outcome.excinfo`. | `feat(report): allure + summary + screenshot on fail` |
| 12 | CI + Reflection | `.github/workflows/ci.yml`, `docs/REFLECTION.md` | README links work; all commits squashed cleanly | `docs: reflection + ci + final polish` |

**Optional Day 4 tasks** (if time permits):
- **Task 13**: AI Triage (`ai/triage.py` triggered on test failure; categorizes failure as Locator / App Bug / Env / Script / Data)

**Optional Day 5 task** (post-challenge extension):
- **Task 14**: Excel ↔ .feature Sync Engine — `scripts/sync_engine.py` reads `data/test_cases.xlsx`, diffs against `tests/features/*.feature` by `scenario_id` comment, writes back only `added` / `modified` rows, leaves untouched scenarios byte-identical. `data/test_cases_template.xlsx` ships as the starting registry. See §11 for full design. Commit message: `feat(sync): excel ↔ feature sync engine PoC`.

---

## 8. Anti-Patterns (DO NOT do)

| Anti-pattern | Why it's bad | Do this instead |
|--------------|--------------|-----------------|
| `driver.find_element(...)` in test code | Couples test to raw Appium | Always go through `BasePage` / Page Object |
| `time.sleep(2)` in Page | Flaky on slow devices | Use `wait_for(...)` with explicit condition |
| Inline XPaths in Python | Hard to maintain | Move to `locator/*.yaml` |
| `from page.X import Y` inside another Page | Tight coupling | Page has no dependencies on other Pages |
| `if/else` branches in BDD steps | Hard to debug | Split into multiple scenarios |
| Calling Appium directly from Flow | Skips Page layer | Flow → Page → Driver |
| Using `pytest.fixture` without scope/cleanup thinking | Resource leaks | Explicit `autouse=False` + teardown |
| Writing the entire automation in one go | Impossible to review / debug | One task per commit, per §7 |
| Adding "extra" features (Docker, MyPy, Black) | Scope creep | Stick to §1 Tech Stack only |

---

## 9. Reference Documents

Codex MUST read these before starting Task 1:

1. `README.md` — scope, AI usage rules, evaluator-facing story (highest-level)
2. `docs/Feature_Inventory.md` — what pages exist + which 2 are in scope (7 BDD cases total)
3. `docs/TECHNICAL_SPEC.md` — this file (how to build)

After Task 8 (first BDD scenario passes), Codex SHOULD re-read `README.md` "Test Coverage" + `Feature_Inventory.md` §四 to confirm scope alignment before continuing to Task 8b / 10.

### Internal cross-references (inside TECHNICAL_SPEC.md)

| If you are writing… | You MUST obey… |
|---------------------|----------------|
| `.feature` files (Tasks 8 / 8b / 10) | §6.5 Style Guide + §6.6 Step Vocabulary + §6.7 Scenario Inventory (exact titles) |
| `step_defs/*_steps.py` | §6.6 phrases (1-to-1 with `parsers.parse`) + §6.3 reuse rules |
| `page/*_page.py` | §3 conventions + §4 locator YAML format + §4.3 priority chain |
| `flow/*_flow.py` | §5 layer rules (no `utils.driver` import; only call Page) |
| `conftest.py` | §5.1 fixture wiring template (driver + reset_app_state + per-page fixtures) |
| Locator yaml | §4.1 format + §4.1 full template + §4.2 fallback loader |

---

## 10. Git & Commit Discipline

- **One task per commit** — do not batch
- **Commit message format**: `<type>(<scope>): <subject>`
  - Types: `chore`, `feat`, `test`, `docs`, `fix`, `refactor`
  - Scopes: `page`, `flow`, `utils`, `case`, `report`, `ai`
- **Before each commit**, run `pytest --collect-only` to ensure no import errors
- **Reference**: each commit message should map to a row in §7

### Squash policy (revised)

> ⚠️ **Do NOT squash the 13 task commits into one.** Each commit is a reviewable unit; squashing destroys the trail of "what was added when and why".

When the user / evaluator wants a clean main history, use **interactive rebase to squash *only* trivial commits** (e.g., 8 and 8b can be combined since they touch the same files and represent one feature):

```bash
# Optional: combine 8 and 8b into a single "add transaction bdd" commit
git rebase -i HEAD~3            # mark 8b as "squash"
# Keep 1-7 and 9-13 as standalone — they are independent features
```

**What to keep as separate commits** (do NOT squash):
- Task 1 (bootstrap) — sets the foundation
- Task 11 (Allure + screenshot) — orthogonal concern
- Task 12 (CI + reflection) — final polish
- Any `fix:` commit that lands after the original feature commit

**Default**: leave the 13 commits as-is. Squash only on user request.

---

## 11. Living Documentation: Excel ↔ Feature Sync (Day 5 extension)

> ⚠️ **This section is OPTIONAL for the 4-6h challenge.** Tasks 1-12 must complete first. Task 14 (sync engine PoC) ships separately as `feat(sync): ...` after the main 13 commits land.

### 11.1 Why this section exists

Industry practice (Google / Microsoft / Amazon / Spotify / Tencent) for BDD at scale converges on three ideas:

1. **Manual test cases live in Excel / TestRail** (testers edit freely; not gated by Git workflow)
2. **Automated scenarios live in `.feature` files** (versioned, peer-reviewed, executable)
3. **A sync layer keeps the two in lockstep** by `scenario_id` (stable anchor; survives content changes)

Without a sync layer, the two drift: Excel says "TC_001 is automated", code says "where is TC_001?". With a sync layer, Excel is the **single source of truth** and `.feature` is the **generated artifact**.

### 11.2 Scenario ID Convention (mandatory for Task 14)

Every scenario in `tests/features/*.feature` MUST start with a `scenario_id` comment derived from the Excel `Test Case ID` column. The sync engine uses this comment as the diff anchor — without it, sync cannot run.

```gherkin
@smoke @p0
# scenario_id: TC_ADD_TX_001
# introduced_in: 1.0.0
# platforms: android, ios
Scenario: Add expense happy path
  ...
```

**Rules**:
- `scenario_id` MUST be unique across all .feature files (enforced by sync engine)
- Format: `TC_<MODULE>_<NNN>` (e.g., `TC_ADD_TX_001`)
- `# introduced_in:` and `# platforms:` are optional but recommended (drive Q2 version-aware selection)
- All four comment lines are added by Codex in Task 8 / 8b / 10 — not optional

### 11.3 Excel Schema (`data/test_cases_template.xlsx`)

The shipped template has 11 L1 columns (mandatory) + 5 L2 columns (recommended). See the actual file for column headers; here's the contract:

| Column | Required | Purpose | Maps to .feature |
|--------|----------|---------|------------------|
| **Test Case ID** | ✅ | Anchor | `# scenario_id:` comment |
| **Module** | ✅ | Routing | `.feature` filename |
| **Scenario Title** | ✅ | Human name | `Scenario:` line |
| **Priority** | ✅ | Tag | `@p0` / `@p1` / `@p2` marker |
| **App Version Introduced** | ✅ | Selection (Q2) | `# introduced_in:` comment |
| **App Version Deprecated** | ✅ (nullable) | Selection (Q2) | `# deprecated_in:` comment |
| **Platform** | ✅ | Filter (Q2) | `# platforms:` comment |
| **Automation Status** | ✅ | Sync gate | row only processed if `automated` |
| **Tags** | ⚠️ Recommended | Marker mapping | `@smoke`, `@custom_category`, etc. |
| **Pre-conditions** | ⚠️ Recommended | Given | `Given ...` line |
| **Test Steps** | ⚠️ Recommended | When | `When ...` lines |
| **Expected Result** | ⚠️ Recommended | Then | `Then ...` lines |

**Status values** for `Automation Status`:
- `manual` — only lives in Excel, sync skips
- `automated` — sync pushes to `.feature`
- `candidate` — QA candidate, sync skips (for human review)
- `deprecated` — sync moves the scenario to a `# DEPRECATED:` comment block

### 11.4 Sync Engine PoC (`scripts/sync_engine.py`)

~30-line script. Reads `data/test_cases.xlsx`, diffs each row against `tests/features/*.feature` by `scenario_id`, applies `added` / `modified` rows, comments-out `deleted` rows. **Untouched scenarios are byte-identical after the run** — the sync engine never re-serializes a scenario it didn't change.

Run modes:

```bash
# One-shot diff + apply
python scripts/sync_engine.py

# Watch mode (auto-trigger on xlsx change, 5s debounce)
python scripts/sync_engine.py --watch

# Dry-run (print diff without writing)
python scripts/sync_engine.py --dry-run
```

Implementation constraints (PoC):
- Uses `openpyxl` for Excel parsing (per §1)
- Uses **regex** for `.feature` parsing — does NOT depend on the `gherkin` Python library (per §1 do-not-add)
- Writes a timestamped backup to `data/.backup/<file>.<date>.bak` before every modification
- Refuses to commit if `pytest --collect-only` fails after a write (caller's responsibility in Day 5+)

### 11.5 Out-of-Scope for PoC (deferred to Day 6+)

These are explicitly NOT in the PoC, listed here so Codex / future-you don't try to add them:

- ❌ Bidirectional sync (writing `Last Run Result` back to Excel) — requires CI integration
- ❌ Auto-PR creation (sync writes to a `sync/<date>` branch, not main) — needs GitHub API token
- ❌ Multi-Excel-file merging — single source for now
- ❌ LLM-generated row proposals — see `docs/SCALING.md` §4 for the AI-assisted flow design
- ❌ Real-time file-watch triggers in CI — `--watch` mode is for local dev only

### 11.6 Reference

For the full Q1-Q6 strategic context (industry practices, version-aware regression, doc-driven sync, AI from screenshots, Excel field rationale), see [`docs/SCALING.md`](SCALING.md). Codex SHOULD read it once at Task 14 commit time but MUST NOT block Tasks 1-12 on it.

---

*End of TECHNICAL_SPEC.md — read this entire file before writing any code.*
