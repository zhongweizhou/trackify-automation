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
│   ├── system_dialogs.py            # Targeted Android permission handling
│   └── config.py                    # Reads platform / device from pytest.ini
│
├── ai/                              # AI-assisted modules (Day 4)
│   ├── __init__.py
│   ├── gen_cases.py                 # LLM-drafted BDD case ideas
│   └── triage.py                    # LLM-based failure categorizer
│
├── data/
│   ├── test_cases.xlsx              # Manual test case registry (Task 14 — sync source)
│   ├── test_cases_template.xlsx     # Reusable corrected seven-case baseline
│   └── .backup/                     # Auto-created by sync_engine.py before each write
│
├── scripts/
│   └── sync_engine.py               # Excel → .feature check/apply (Task 14 PoC)
│
├── report/
│   ├── allure-results/              # Generated each run
│   ├── screenshots/                 # Generated on failure
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
- Every Page Object wait checks for the Android system prompt `Allow Trackify to send you notifications?` and clicks `Allow` before continuing. The handler matches notification copy specifically and does not accept SMS or other permission prompts.

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

#### When phrases (14 actions)

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

#### Then phrases (9 assertions)

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

**Parsing rules** (used by `parsers.parse(...)` in step_defs):

| Placeholder | Type | Example value | Validation |
|-------------|------|---------------|------------|
| `<type:str>` | `str` | `"expense"` | Must be one of `expense`, `income`, `transfer` (asserted in Flow, not step) |
| `<amount:float>` | `float` | `100.0`, `9.99` | Must be `> 0` (asserted in Flow) |
| `<category:str>` | `str` | `"Food"`, `"Transport"` | Free text |
| `<note:str>` | `str` | `"breakfast with Dinna"` | Free text |
| `<tags:str>` | `str` | `"food,breakfast"` | Non-empty comma-separated tag text |
| `<name:str>` | `str` | `"baby cost"` | Free text |
| `<currency:str>` | `str` | `"$ US Dollar"` | Full visible option label |
| `<monthly_budget:int>` | `int` | `30000` | Must be a positive whole number and match the displayed slider value |
| `<message:str>` | `str` | `"Amount is required"` | Substring match against displayed text |
| `<date_time:str>` | `str` | `"20250506 9:00 AM"` | Local date/time in `YYYYMMDD h:mm AM/PM` format |

**Add Transaction post-save assertion rules**:
- Capture the date and time displayed on Add Transaction before tapping Save. The Transactions assertion must find one row under the corresponding date containing the same formatted amount, category, and time.
- Expense and income transactions increment the existing Home `This Month` expense and income values respectively. Transfer transactions do not change either value.
- The large `This Month` value is `income - expense`.
- The displayed budget percentage is `expense / budget * 100`, rounded to the nearest integer with half-up behavior (`ROUND_HALF_UP`). Examples for budget `20000`: expense `125` gives `0.625%` and displays `1%`; expense `1125` gives `5.625%` and displays `6%`; expense `9500` gives `47.5%` and displays `48%`.
- Empty-amount validation must leave both Recent Transactions and the Transactions page empty and must leave all `This Month` values unchanged.

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

Implementation notes for the current Android build:
- The Gherkin phrase `user taps "Add new category"` maps to a left swipe on the horizontal Category list, followed by `New` → `Add Category`.
- `baby cost` uses the New Category form's default icon and color. Its fixed-width transaction chip exposes the shortened label `baby`, but Manage Categories and the saved Home transaction retain the full name.
- Empty amount submission remains on Add Transaction with an empty field and saves nothing. The build does not expose the expected validation copy to accessibility, so the assertion prefers visible copy and otherwise verifies that rejected form state before checking the Home list is empty.
- With budget `30000`, expenses `100` and `50` produce percentages below `0.5%` and correctly display `0%` after half-up rounding.

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

> The Transactions scenarios reuse setup and transaction-entry steps from `tests/step_defs/common_steps.py`; feature-specific steps only navigate, filter, and assert list behavior.

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
| 7 | Add Transaction flow | `flow/add_transaction_flow.py` | `flow.add_expense(...)` orchestrates Page + returns new ID | `feat(flow): add transaction business logic` |
| 8 | First BDD feature (Add Expense happy path) | `tests/features/add_transaction.feature`, `tests/step_defs/add_transaction_steps.py`, `conftest.py` (page/flow fixtures) | `pytest tests/features/add_transaction.feature -k "happy_path"` collects and runs **only** the "Add expense happy path" scenario from §6.7. Other 4 Add Transaction scenarios written but tagged `@skip` (or feature-level Background-only). Implements every §6.6 phrase used in this scenario. | `test(case): add transaction bdd (expense happy path)` |
| 8a | First-run setup baseline | `locator/onboarding.yaml`, `page/onboarding_page.py`, `flow/app_setup_flow.py`, `conftest.py`, BDD `Background` blocks | Every business scenario completes `Kimbal` → `$ US Dollar` + `30000` → Bank SMS Reader enabled + `Get Started`; no test path taps onboarding `Skip`; Home shows `Kimbal` and `$` before business actions | `feat(setup): complete required first-run configuration` |
| 8b | Remaining Add Transaction scenarios | `tests/features/add_transaction.feature`, `tests/step_defs/add_transaction_steps.py` | Un-skip the remaining **4 scenarios** from §6.7 (Add Income, Add Transfer, Validation, Custom Category). Implement the additional §6.6 phrases (`user selects type`, `user taps "Add new category"`, `user creates custom category`, `error message ... is shown for amount`, `no transaction appears ...`). Custom Category creates and selects `baby cost` with any icon/color. All **5 Add Transaction scenarios** pass. | `test(case): add transaction bdd (4 more scenarios + custom category)` |
| 8c | Transaction persistence and Home summary assertions | `locator/home.yaml`, `locator/transactions.yaml`, `page/base_page.py`, `page/home_page.py`, `page/transactions_page.py`, `page/add_transaction_page.py`, `flow/add_transaction_flow.py`, `utils/system_dialogs.py`, Add Transaction BDD files | Every Add Transaction scenario verifies the matching Transactions date/amount/category/time and the `This Month` income, expense, balance, and half-up integer percentage. Transfer has no summary impact. Notification permission prompts are accepted globally. | `test(case): verify transaction persistence and monthly summary` |
| 9 | Transactions page + flow | `page/transactions_page.py`, `flow/transactions_flow.py`, `locator/transactions.yaml`, Add Transaction date/time Page/Flow locators, `conftest.py` | Manual test: filter works and a transaction at `2025-05-06 9:00 AM` is grouped under `06 May 2025` | `feat(page): transactions page + flow` |
| 10 | Transactions BDD | `tests/features/transactions.feature`, `tests/step_defs/transactions_steps.py` | Both Transactions scenarios from §6.7 collect and run: filter by type (`@filter`), group-by-date (`@grouping`). Implement the additional §6.6 phrases (`user filters transactions by type`, `only transactions of type ... are shown`, `transactions are grouped by date ...`). **Total project: 5 Add Transaction + 2 Transactions = 7 scenarios**. | `test(case): transactions bdd (2 scenarios)` |
| 11 | Allure + Screenshot on fail | `conftest.py` (add Allure metadata + `pytest_runtest_makereport` hooks) | `pytest --alluredir=./allure-results` produces results; on `call` failure the hook saves PNG to `report/screenshots/<test_name>.png` and attaches it to Allure — **do NOT wrap test bodies in try/except** (see §8 anti-patterns). Hook pattern: `pytest.hookimpl(tryfirst=True, hookwrapper=True) def pytest_runtest_makereport(item, call)` that yields and inspects the call report. | `feat(report): allure + screenshot on fail` |
| 12 | CI + Reflection | `.github/workflows/ci.yml`, `docs/REFLECTION.md` | README links work; all commits squashed cleanly | `docs: reflection + ci + final polish` |

**Optional Day 4 task** (if time permits):
- **Task 13**: AI Triage — classify the first failing pytest phase for each test as one of {**Locator**, **App Bug**, **Env**, **Script**, **Data**, **Unknown**}. The verdict is advisory: it MUST NOT mutate the pytest outcome, suppress the original traceback, or be presented as a confirmed root cause.

  **Result contract** (`TriageResult`, frozen dataclass):

  | Field | Type | Rule |
  |-------|------|------|
  | `category` | enum string | One of `Locator`, `App Bug`, `Env`, `Script`, `Data`, `Unknown` |
  | `confidence` | float | Clamped to `0.0..1.0` |
  | `reasoning` | string | Concise, max 500 characters; never contains secrets or the full traceback |
  | `next_action` | string | Concrete engineer action, max 500 characters |
  | `classifier` | string | `local`, `llm`, or `disabled` |
  | `matched_signatures` | tuple/list | Local signature IDs only; empty for LLM/disabled results |

  The Allure JSON attachment MUST include the fields above plus `schema_version`, `test_name`, and failing `phase`. Serialization uses `dataclasses.asdict()`; no raw exception object is serialized.

  **Architecture (2 stages)**:

  1. **Local weighted heuristic (always on)** — compile `LOCAL_SIGNATURES` once at module import, then match normalized `error_msg + traceback`. Each signature has its own confidence. Choose the highest-confidence match; ties use `Env > Locator > Data > App Bug > Script`. Return immediately only when confidence is `>= 0.70`. Do not add weak matches together: multiple generic strings must not manufacture high confidence. This stage performs no file, environment, or network I/O.
  2. **Claude-compatible fallback (explicit opt-in)** — runs only when local confidence is below `0.70` **and** `AI_TRIAGE_LLM_ENABLED=1`, `ANTHROPIC_API_KEY`, and `ANTHROPIC_MODEL` are all present. `ANTHROPIC_BASE_URL` is optional and defaults to `https://api.anthropic.com`; gateway paths such as `https://api.minimaxi.com/anthropic` are preserved before appending `/v1/messages`. Use the Anthropic Messages protocol through the Python standard library (or an injected callable in tests); do not add an SDK dependency outside §1. One request maximum, no retry, 5-second total timeout. Any timeout, HTTP error, missing config, malformed JSON, unknown category, or invalid field returns `Unknown / 0.0` without raising.

  **Required local signatures** (`re.IGNORECASE`; `re.DOTALL` only for bounded contextual patterns):

  | Category | Signature ID / regex intent | Confidence | Default `next_action` |
  |----------|-----------------------------|------------|-----------------------|
  | **Env** | `connection_refused`: `ConnectionRefused(?:Error)?`, `ECONNREFUSED`, or `Failed to establish a new connection` near `4723`/Appium | `0.98` | Verify Appium is listening on `:4723`; inspect `appium.log` |
  | **Env** | `device_unavailable`: `adb.*(?:not found\|No such file)`, `device (?:offline\|unauthorized)`, or `no (?:Android )?devices?` | `0.95` | Run `adb devices`; reconnect or boot the target device |
  | **Locator** | `element_missing`: `NoSuchElement(?:Exception\|Error)` or `Unable to locate element` | `0.98` | Check the named locator YAML entry and current Appium page source |
  | **Locator** | `locator_timeout`: `TimeoutException` within a bounded context containing `find_element`, `locator`, `accessibility_id`, or `xpath` (in either order) | `0.85` | Confirm page state, then update the locator/fallback if the element changed |
  | **Data** | `test_data_missing`: `KeyError` near `test_data`/`fixture`/`yaml`, or test-data/YAML text near `missing`, `required`, or `not found` | `0.90` | Validate required keys and row values in `data/` |
  | **Data** | `database_corrupt`: `HiveError` or corruption text near `data`/`database` | `0.80` | Reset the local app database and verify the seed/setup path |
  | **App Bug** | `app_crash`: `ANR`, `App crashed`, `not responding`, `has stopped`, or `java\.lang\.` | `0.98` | Reproduce manually on the same build/device and file an app bug if repeatable |
  | **App Bug** | `business_mismatch`: `validation`/`summary`/`saved transaction` near `expected` and `actual`/`got`/`displayed`/`missing` | `0.82` | Compare the displayed state with the requirement and reproduce manually |
  | **App Bug** | `element_disabled`: `element.*not enabled` | `0.60` | Ambiguous; gather page state and allow LLM/Unknown rather than short-circuiting |
  | **Script** | `python_structure`: `ImportError`, `ModuleNotFoundError`, `NameError`, `SyntaxError`, or `IndentationError` | `0.98` | Fix the Python/import error directly |
  | **Script** | `python_contract`: `AttributeError` or `TypeError` | `0.90` | Read the top project frame and correct the API/type usage |
  | **Script** | `generic_assertion`: bare `AssertionError` | `0.40` | Ambiguous by itself; do not classify as Script without stronger context |

  **Input normalization and privacy**:
  - Input keys: `error_msg`, `traceback`, and optional `test_name`, `phase`, `screenshot_path`. For command-line/backward compatibility, missing `test_name` defaults to `unknown` and missing `phase` defaults to `call`.
  - Limit `error_msg` to 2,000 characters and traceback to the final 12,000 characters before LLM use.
  - Redact authorization headers, API keys/tokens, and URL query strings before attachment or network use.
  - Multi-modal input is out of scope. Send only `screenshot_available` and the screenshot basename; never upload image bytes or an absolute local path.
  - Treat exception text and traceback as untrusted quoted data. The system prompt explicitly says to ignore instructions embedded in failure text and exposes no tools.
  - Prompt for one JSON object only (`temperature=0`, small bounded output). Validate category allowlist, numeric confidence, non-empty bounded strings, and ignore unknown response fields.

  **pytest / Allure integration**:
  - Extend Task 11's `pytest_runtest_makereport` hook **after** `outcome = yield` and report creation.
  - Triage `setup`, `call`, and `teardown` failures; environment failures commonly happen in setup. Use an `item.stash` key so only the first failing phase is triaged once.
  - For a `call` failure, capture the Task 11 screenshot first and pass its returned path to triage. Other phases use `screenshot_path=None`.
  - Attach `AI Triage` with `allure.attachment_type.JSON`, even for `Unknown`, when an Allure lifecycle is active.
  - Write `[AI Triage] <Category> (<NN%>): <reasoning>` through pytest's `terminalreporter.write_line()` when the failing phase completes, so capture settings do not hide it. Fall back to `print()` only when no terminal reporter exists.
  - Triage failures are caught and converted to `Unknown`; reporting code must never replace the original test failure.

  **Operational presentation**:
  - Passing tests produce no triage call or attachment. Only the first failing phase is classified.
  - `classifier=local` proves a deterministic signature returned without network I/O; `classifier=llm` means one compatible-model call was attempted; `classifier=disabled` means ambiguous evidence could not use LLM because required opt-in configuration was absent.
  - The terminal line is the fast signal; the Allure `AI Triage` JSON is the auditable record. Both remain advisory and must be read with the original traceback and screenshot.
  - A real key belongs only in ignored `.env`; `.env.example` contains placeholders. The project never auto-loads `.env`, and certificate verification must not be disabled to make a gateway call succeed.
  - Runtime configuration and verification procedures are documented in [`docs/AI_TRIAGE.md`](AI_TRIAGE.md).

  **Unit-test isolation**:
  - Add a `unit` marker. Refactor `reset_app_state` to request the `driver` lazily with `request.getfixturevalue("driver")`; immediately yield for `@pytest.mark.unit` tests so pure triage tests never start Appium or call `adb pm clear`.
  - Inject the LLM callable. A spy/fake MUST prove that a local `Locator` hit makes zero LLM calls; do not leave `print('local hit')` instrumentation in production code.

  **Files touched**: `ai/__init__.py`, `ai/triage.py`, `tests/unit/test_triage.py`, `conftest.py`, `pytest.ini`.

  **Acceptance criteria**:
  - `uv run python -c "from ai.triage import triage_failure; print(triage_failure({'error_msg': 'NoSuchElementException: ...', 'traceback': ''}).category)"` prints `Locator`.
  - `uv run pytest -m unit tests/unit/test_triage.py -q` passes without a running Appium server or connected device.
  - Unit cases cover every category, precedence, bare `AssertionError -> Unknown` without LLM, missing config, timeout/malformed LLM output, confidence clamping, redaction, and zero network calls on a local hit.
  - A controlled setup or call failure produces exactly one `AI Triage` JSON attachment with the required schema and one visible console line; the original pytest failure remains unchanged.
  - Missing `ANTHROPIC_API_KEY` or disabled LLM returns `Unknown`, `confidence=0.0`, `classifier=disabled`, with no exception and no network call.
  - Local classification has no I/O and is deterministic. Runtime may be benchmarked for information, but no hardware-dependent `<1 ms` assertion is required.

  **Out-of-scope for PoC**:
  - Multi-modal screenshot analysis / Claude Vision.
  - Self-learning from engineer corrections.
  - Cross-run caching or flaky-test history.
  - Automatic test retry, failure suppression, or bug filing.
  - Classification of non-English error messages.

  **Commit message**: `feat(ai): failure triage with local heuristic + LLM fallback`

**Optional Day 5 task** (post-challenge extension):
- **Task 14**: Excel → `.feature` Sync Engine — `data/test_cases.xlsx` is authoritative only for managed Scenario blocks identified by `scenario_id`; Feature headers and Background blocks remain code-owned. The engine routes rows by Module, validates the complete workbook before writing, applies only `added` / `modified` / explicitly `deprecated` blocks through a backup/replace/rollback transaction, and leaves untouched managed blocks byte-identical. `data/test_cases_template.xlsx` ships as the bootstrap registry. See §11 for the full contract. Commit message: `feat(sync): excel-to-feature sync engine PoC`.

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

## 11. Living Documentation: Excel → Feature Sync (Day 5 extension)

> **This section is optional for the challenge.** Tasks 1-12 complete first. Task 14 ships as a separate `feat(sync): ...` commit. The arrow is intentionally one-way: the PoC never writes test results or scenario edits from `.feature` back to Excel.

### 11.1 Ownership Model

The synchronization contract is hybrid, not "Excel owns every byte":

| Artifact region | Owner | Sync behavior |
|-----------------|-------|---------------|
| Excel row for a managed test case | Excel | Source for scenario metadata, tags, When/Then steps, and lifecycle status |
| Managed Scenario block beginning with `# scenario_id:` | Excel | Added, replaced, or explicitly deprecated by ID |
| `Feature:` line, file comments, and `Background:` block | Code / reviewer | Never generated or rewritten by the PoC |
| Step definitions, Pages, Flows, locators | Code | Never modified by sync |
| `Last Run Result` and review metadata | QA / future CI | Read-only to this PoC; never written back |

This boundary keeps common first-run setup in the code-reviewed Background while allowing QA to maintain individual scenario actions and assertions. "Excel source of truth" means **source of truth for managed Scenario blocks only**.

### 11.2 Canonical Managed Block and Scenario IDs

Task 14 MUST first add IDs to all seven existing scenarios using the IDs already present in `data/test_cases_template.xlsx`. A managed block has this canonical order:

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

`# deprecated_in: <version>` is optional and appears after `# introduced_in:` only when populated. Therefore there are **three mandatory metadata comments** (`scenario_id`, `introduced_in`, `platforms`) plus one optional deprecation comment; tags are not comment lines.

**ID mapping for the current inventory**:

| Scenario | ID | Module |
|----------|----|--------|
| Add expense happy path | `TC_ADD_TX_001` | `add_transaction` |
| Add income happy path | `TC_ADD_TX_002` | `add_transaction` |
| Add transfer happy path | `TC_ADD_TX_003` | `add_transaction` |
| Validation — empty amount shows error and does not save | `TC_ADD_TX_004` | `add_transaction` |
| Add expense with new custom category created in flow | `TC_ADD_TX_005` | `add_transaction` |
| Filter transactions by type shows only matching type | `TC_TXN_001` | `transactions` |
| Transactions grouped by date with section headers | `TC_TXN_002` | `transactions` |

**Rules**:
- ID format: `^TC_[A-Z][A-Z0-9_]*_[0-9]{3}$`.
- An ID MUST be unique in the workbook and across every feature file. Duplicate IDs are a hard error before any write.
- `Module` uses an allowlist, not a path: `add_transaction -> tests/features/add_transaction.feature`, `transactions -> tests/features/transactions.feature`. Unknown values are errors; never concatenate untrusted Module text into a path.
- A managed block starts at a line whose exact prefix is `# scenario_id:` and ends immediately before the next managed block or EOF. Content before the first managed block is code-owned.
- Tags are rendered after metadata and immediately before `Scenario:`. Comma-delimited Excel tags become space-delimited Gherkin tags (`smoke,p0 -> @smoke @p0`). Priority is injected as one canonical tag and deduplicated.
- The PoC supports `Scenario:` only. `Scenario Outline` / `Examples` synchronization is out of scope.
- A feature scenario that has no ID after the initial seven-scenario migration is a validation error, not an implicit addition/deletion candidate.

### 11.3 Excel Schema (`data/test_cases_template.xlsx`)

The actual template contains 16 columns: 11 L1 registry columns and 5 L2 automation columns. Every header is mandatory. "Nullable" or "recommended" below applies to row values, not header presence.

| Column | Row value | Purpose | PoC behavior |
|--------|-----------|---------|--------------|
| **Test Case ID** | Required | Stable anchor | `# scenario_id:` |
| **Module** | Required | Safe routing | Validated allowlist; selects one feature file |
| **Scenario Title** | Required | Human-readable name | `Scenario:` text |
| **Priority** | Required: `P0`, `P1`, `P2` | Selection | Normalized to one lowercase priority tag |
| **App Version Introduced** | Required | Version selection | `# introduced_in:` |
| **App Version Deprecated** | Nullable; required for `deprecated` | Lifecycle | Optional `# deprecated_in:` |
| **Platform** | Required: `android`, `ios`, or `both` | Platform selection | `both` renders `android, ios` in `# platforms:` |
| **Automation Status** | Required enum | Lifecycle gate | See status rules below |
| **Author** | Required registry metadata | Ownership | Validated non-empty; not rendered |
| **Last Reviewed Date** | Required ISO date | Auditability | Validated; not rendered |
| **Last Run Result** | Required registry metadata | Execution visibility | Read-only/ignored by this PoC |
| **Tags** | Recommended | pytest markers | Comma-delimited, no leading `@`; rendered with priority deduplication |
| **Pre-conditions** | Recommended metadata | Manual-test context | Not rendered in PoC; file Background remains code-owned |
| **Test Steps** | Required for `automated` | Scenario actions | One vocabulary phrase per newline; first renders `When`, remaining render `And` |
| **Expected Result** | Required for `automated` | Scenario assertions | One vocabulary phrase per newline; first renders `Then`, remaining render `And` |
| **Estimated Runtime (s)** | Recommended positive integer | Planning | Validated when present; not rendered |

Do not split steps on semicolons: notes and messages may legitimately contain them. Excel cells use newline-delimited phrases **without** `Given`/`When`/`Then`/`And` keywords; the renderer adds keywords and indentation deterministically.

**Automation Status rules**:
- `manual` / `candidate`: ignored when no managed feature block exists. If the ID already exists in a feature, stop with an error and require an explicit transition to `deprecated`; never silently remove executable coverage.
- `automated`: add or update the routed managed block.
- `deprecated`: requires `App Version Deprecated` and an existing managed block; deprecating an ID that was never generated is an error. Keep the metadata comments parseable, but comment the tags, Scenario line, and body between deterministic `DEPRECATED BEGIN/END <ID>` markers. Do not infer deprecation from a missing row.
- A managed feature ID absent from the workbook is a hard error. Missing Excel rows never mean delete.

Canonical deprecated form:

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

**Bootstrap data reconciliation (mandatory before first apply)**:
- Copy `data/test_cases_template.xlsx` to `data/test_cases.xlsx`; the working registry is the Task 14 input.
- Update all seven rows to match §6.7 exactly before generating features. The original template was an early draft: it contained `Coffee` instead of `baby cost`, old compound `user adds ...` phrases, missing tag/date actions, and incomplete persistence/monthly-summary assertions. The corrected baseline uses `Platform=both` because all seven scenarios have now passed on Android and iOS simulators.
- Preserve the template as a reusable example, but update it to the same corrected seven-row baseline so a new copy does not reintroduce drift.

### 11.4 Sync Engine Interface (`scripts/sync_engine.py`)

The implemented engine routes rows through the Module allowlist and updates only the corresponding managed feature blocks.

Safe run modes:

```bash
# Default: validate + diff only; no writes. Exit 1 when drift exists.
uv run python scripts/sync_engine.py --check

# Explicit mutation after full validation
uv run python scripts/sync_engine.py --apply

# Apply, then execute only added/modified active scenarios
uv run python scripts/sync_engine.py --apply --run-changed

# Cross-device health gate: check, apply, then replicate changes to all devices
./scripts/run_changed_matrix.sh

# Local-only watcher; mutation still requires --apply
uv run python scripts/sync_engine.py --watch --apply

# Optional non-default registry path for tests/local experiments
uv run python scripts/sync_engine.py --check --input /path/to/test_cases.xlsx
```

`--check` is the default when neither `--check` nor `--apply` is supplied. `--check`, `--apply`, and machine-readable `--list-changed` are mutually exclusive. `--run-changed` requires `--apply`; it runs the exact pytest node IDs for added/modified active scenarios after a successful collection. `scripts/run_changed_matrix.sh` consumes `--list-changed`, preflights devices/Appium, applies once, and runs the exact changed subset in matrix `replicate` mode so every selected device validates every changed case. `--watch` without `--apply` reports drift only. Diff categories are `added`, `modified`, `deprecated`, `unchanged`, and `errors`; there is no implicit `deleted` category.

Exit codes:
- `0`: valid and no drift (`--check`), or apply succeeded and post-write collection passed.
- `1`: valid but drift exists in `--check` mode.
- `2`: schema, duplicate, routing, parsing, I/O, lock, render, or post-write collection error.

### 11.5 Validation, Transactional Safety, and Rollback

The engine MUST complete all workbook and feature validation before the first write:

- required headers and required row values;
- ID format/uniqueness and feature ID uniqueness;
- allowed Module, status, priority, platform, and tag syntax;
- non-empty newline-delimited Test Steps / Expected Result for automated rows;
- one routed feature per automated/deprecated row;
- no managed feature ID missing from the workbook;
- no unmanaged `Scenario:` left after the initial ID migration;
- no duplicate scenario title within a module;
- UTF-8 feature decoding and one detected newline style per file.

Apply is a best-effort transaction across all affected feature files (Python/OS cannot atomically replace multiple files in one operation):

1. Acquire `data/.backup/sync.lock` atomically; store PID/timestamp and fail instead of running concurrent apply/watch writers. A stale lock is removed manually only after confirming that PID is no longer running.
2. Render every target file fully in memory. Preserve original UTF-8 encoding, newline style, code-owned prefix, and every unchanged managed block by exact string slicing.
3. Before **each** changing apply, write timestamped backups with microseconds to `data/.backup/<feature>.<YYYYMMDDTHHMMSSffffff>.bak`. Never reuse a once-per-day backup name.
4. Write each rendered file to a temporary file in the same directory, flush it, then use `os.replace()`; no direct `Path.write_text()` over the target.
5. Run `[sys.executable, "-m", "pytest", "--collect-only", "-q"]` once after all replacements.
6. If any replacement or collection fails, restore every affected file from that run's backup, report the original error plus rollback status, and exit `2`.
7. Always remove temporary files and release the lock in `finally`. Process-kill/power-loss journaling between multiple `os.replace()` calls is out of scope.

The engine never edits either workbook. `data/.backup/` remains gitignored. Watch mode uses `watchdog` with a 5-second debounce and invokes the same validated transaction; it is not a separate write path.

**Byte-identical guarantee** means the encoded byte slice for every `unchanged` managed block has the same SHA-256 before and after a successful apply. It does not mean a modified block or necessary separator around it remains unchanged.

### 11.6 Tests and Acceptance Criteria

**Files touched**: `scripts/sync_engine.py`, `scripts/run_changed_matrix.sh`, `scripts/run_device_matrix.py`, `data/test_cases.xlsx`, `data/test_cases_template.xlsx`, both feature files (initial IDs/metadata), `tests/unit/test_sync_engine.py`, `unit_tests/test_run_device_matrix.py`, and `.github/workflows/ci.yml`, plus `conftest.py` / `pytest.ini` only if the `unit` isolation marker from Task 13 is not already present.

All sync tests use temporary workbook/feature copies. They MUST NOT mutate repository feature files or the checked-in registry.

Acceptance criteria:

- Parsing the corrected registry returns exactly seven automated rows routed as five `add_transaction` and two `transactions` cases.
- Initial Task 14 feature files contain the seven unique IDs from §11.2 and still collect the same seven BDD scenarios.
- `uv run python scripts/sync_engine.py --check` exits `0` on the committed state and performs zero writes.
- Changing one Excel amount/title/step in a temporary copy reports exactly one `modified` block in the correct module; the other feature file is byte-identical.
- Running `--apply` twice is idempotent: the second run reports no drift and both feature-file hashes remain unchanged.
- Unit tests cover duplicate IDs (Excel and cross-feature), unknown Module, invalid enum/required fields, tag normalization, status transitions, missing workbook IDs, unsupported Scenario Outline, and newline preservation.
- A forced post-write collection failure restores all affected files and leaves no lock/temp file.
- SHA-256 assertions prove untouched managed blocks are byte-identical after neighboring add/modify/deprecate operations.
- Workbook hash is identical before and after every mode, including `--apply` and `--watch`.
- `--apply --run-changed` executes only added/modified active scenarios, reports their IDs and Allure path, and prints an exact retry command plus code/locator debugging scope on runtime failure.
- `scripts/run_changed_matrix.sh` returns `0` only when there is no runnable drift or every changed case passes on every selected device; matrix summaries preserve change kind, stable case ID, environment, device, OS, UDID, and per-device health.
- CI `validate` runs `uv run python scripts/sync_engine.py --check` before pytest collection once Task 14 lands.
- Full verification passes: unit sync tests, seven BDD scenarios collected, and `git diff --check` clean.

### 11.7 Out-of-Scope for PoC

- Bidirectional sync or writing `Last Run Result` back to Excel.
- Automatic deletion based on a missing row.
- Auto-PR/branch creation or committing from the script.
- Multi-workbook merge and conflict resolution.
- Scenario Outline / Examples generation.
- LLM-generated row proposals (see `docs/SCALING.md` §4).
- File watching in CI; `--watch` is local development only.

### 11.8 Reference

For the broader Q1-Q6 roadmap, version-aware regression, and document-driven testing context, see [`docs/SCALING.md`](SCALING.md). Read it at Task 14 implementation time; it does not block Tasks 1-12.

---

*End of TECHNICAL_SPEC.md — read this entire file before writing any code.*
