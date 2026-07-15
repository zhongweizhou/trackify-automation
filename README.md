# Trackify Mobile UI Automation

> AI-assisted End-to-End mobile automation for **Trackify** (Flutter personal-finance tracker).
>
> Built as part of the Trackify Challenge.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)] [![Appium](https://img.shields.io/badge/Appium-3.x-green)] [![pytest-bdd](https://img.shields.io/badge/pytest--bdd-BDD-orange)] [![Allure](https://img.shields.io/badge/Allure-Reporting-yellow)]

---

## Overview

Trackify is a 100% offline Flutter personal-finance tracker using Hive as its local database. This repository contains an **end-to-end mobile UI automation framework** designed and implemented in **4-6 hours**, focused on the two highest-value features for a typical user journey:

1. **Home → Add Transaction shortcut** — the entry point for recording any transaction (Expense / Income / Transfer)
2. **Transactions list** — the downstream view, supporting filtering and date-grouped summaries

**Why this framework**:

| Driver | Why |
|--------|-----|
| Appium 3 | Industry standard for cross-platform mobile automation |
| pytest-bdd | Behavior-driven scenarios written in plain Gherkin |
| Page Object + Flow | Clean separation: Page = elements, Flow = business |
| AI-assisted | Used at every stage to maximize signal in limited time |

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1 / M2 / M3 / M4) — tested
- Python 3.11+
- Node.js LTS
- Android SDK + Platform Tools (`adb`)
- An Android emulator or real device with **Android 10+**

### Setup

```bash
# Clone
git clone https://github.com/<your-username>/trackify-automation
cd trackify-automation

# Python deps (using uv)
uv sync             # or: pip install -r requirements.txt

# Appium drivers
npm install -g appium
appium driver install uiautomator2

# Start Appium server in one terminal
appium

# In another terminal: install the app on a running emulator
adb install -r -t app-release.apk
```

### Run Tests

```bash
# All tests
pytest

# Smoke only (P0)
pytest -m smoke

# Regression (P0 + P1)
pytest -m regression

# Single feature
pytest tests/features/add_transaction.feature

# With Allure report
pytest --alluredir=./allure-results
allure serve ./allure-results
```

---

## Test Coverage

We focused on the **two highest-value features** of the user journey:

| Feature | Sub-features | P0 | P1 | Total | Why chosen |
|---------|--------------|----|----|-------|------------|
| **Home → Add Transaction shortcut** | Add Expense / Income / Transfer; amount, category (+ custom), date, note, tags, photo upload | 4 | 1 | 5 | The primary entry point for recording any transaction; downstream data source for Home summary, Transactions list, and Analytics |
| **Transactions list** | Filter by type (All / Expense / Income / Transfer); date-grouped summary | 2 | 0 | 2 | Validation surface — the same data must appear correctly here after Add |

### Detailed Sub-feature Coverage

#### Home → Add Transaction shortcut

| Sub-feature | Priority |
|-------------|----------|
| Add **Expense** transaction with: amount + category (mandatory, e.g. Food) + note ("breakfast with Dinna") + tags ("food,dinna") + date + photo attachment | P0 |
| Add **Income** transaction with: amount + category (mandatory, e.g. Salary) + note ("fulltime salary") + tags ("fulltime salary") + date + photo attachment | P0 |
| Add **Transfer** transaction with: amount + category (mandatory, e.g. Others) + note ("transfer amount from main account into sub account") + tags ("transfer") + date + photo attachment | P0 |
| Add a **custom category** inline during Add Transaction flow | P1 |
| Use the **new custom category** in an Expense transaction | P0 |

#### Transactions list

| Sub-feature | Priority |
|-------------|----------|
| Filter transactions by type (All / Expense / Income / Transfer) | P0 |
| Transactions list is **summarized by date** (grouped sections per date) | P0 |

### Out-of-scope features (and why)

| Feature | Reason |
|---------|--------|
| Analytics / charts | Visual-heavy, low-assertion-ROI; DOM structure unstable |
| Settings | Configuration-heavy, low business logic depth |
| Budget Management | **Does not exist in current Trackify build** (confirmed via full-app search) |

See [`docs/Feature_Inventory.md`](docs/Feature_Inventory.md) for the full exploration notes.

---

## Project Structure

```
trackify-automation/
├── docs/
│   ├── Feature_Inventory.md        # Day 1 manual exploration
│   ├── DESIGN.md                   # Architecture & decisions
│   └── REFLECTION.md               # Honest strengths + weaknesses
├── tests/
│   ├── features/
│   │   ├── add_transaction.feature # Gherkin BDD cases (Home shortcut)
│   │   └── transactions.feature    # Gherkin BDD cases (Transactions list)
│   ├── step_defs/                  # pytest-bdd step implementations
│   └── conftest.py
├── locator/
│   ├── home.yaml
│   ├── add_transaction.yaml
│   └── transactions.yaml
├── page/
│   ├── base_page.py
│   ├── home_page.py
│   ├── add_transaction_page.py
│   └── transactions_page.py
├── flow/
│   ├── add_transaction_flow.py
│   └── transactions_flow.py
├── utils/
│   ├── driver.py                   # Wrapped Appium driver
│   └── ai_helper.py                # AI-assisted locator suggestions
├── ai/
│   ├── gen_cases.py                # LLM-generated case drafts
│   └── triage.py                   # LLM-based failure triage
├── assets/
│   └── run_demo.mp4
├── data/
│   └── test_data.yaml
├── .github/workflows/ci.yml       # Minimal CI
├── conftest.py
├── pytest.ini
├── pyproject.toml
├── README.md
└── app-release.apk                 # Local (not committed)
```

### Architecture (3 Layers)

```
Requirement → Feature Files (Gherkin)
                ↓
Step Definitions (pytest-bdd)
                ↓
Flow Layer (business logic)
                ↓
Page Object (UI elements)
                ↓
Driver Wrapper (Appium)
                ↓
Appium uiautomator2
                ↓
Trackify App
```

**Key principles**:

- ❌ No `sleep()` in Page layer — all waits
- ❌ No `driver.find_element()` outside `utils/driver.py`
- ❌ No XPath as primary — AccessibilityID > ID > Class
- ✅ Locator strategy in YAML, not Python
- ✅ Each layer has **one** responsibility

---

## Design Decisions

See [`docs/DESIGN.md`](docs/DESIGN.md) for full architectural justification.

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| BDD framework | pytest-bdd | behave | Stays inside pytest ecosystem |
| Locator format | YAML | Python dict | Easier for non-devs to edit |
| Reset DB | `pm clear` | App UI | Deterministic for automation |
| Assert style | Allure attach | Plain logs | Visual evidence + easy review |
| Feature focus | Home + Transactions | Expense CRUD + Budget | Home is the primary entry point; Transactions validates downstream correctness |

---

## AI Usage

I used AI tools **deliberately** at multiple stages to maximize signal within the 4-6 hour budget:

| Phase | What AI did | Why | Tool |
|-------|-------------|-----|------|
| **Day 1 Feature Inventory** | AI helped reason about which features to test | Expanded my reasoning to include offline risk + edge cases | ChatGPT (peripheral) |
| **Day 2 BDD Case Generation** | AI drafted **7 Gherkin scenarios** which I reviewed, edited, and extended | Saved ~1.5h of writing | Claude / GPT-4o |
| **Day 2 Locator Suggestion** | Fed screenshots to AI to confirm AccessibilityID choices for Flutter elements | Reduced trial-and-error with Flutter's semantic tree | Claude Vision |
| **Day 3 Failure Triage** | LLM categorizes failure as Locator / App Bug / Env / Script / Data | Faster root cause | OpenAI |
| **README drafting** | AI helped structure sections | Focus on testing logic, not wording | Claude |
| **Tag/Note format conventions** | AI suggested Gherkin syntax for data tables (tags as comma-separated strings) | Standardized test data | Claude |

**Honest assessment**: AI made me faster, not smarter. I still drove every architectural decision and reviewed every line of AI output before committing.

---

## Test Results

After every run, see:

- **Allure report**: `allure-report/index.html` (open in browser)
- **Screenshots on failure**: `report/screenshots/`
- **Recording**: `assets/run_demo.mp4`

### Latest Run (placeholder — update after each run)

```
Passed: 6 / Failed: 0 / Skipped: 1
Add Transaction: 4 0  (1 P1 skipped)
Transactions:    2 0
```

---

## iOS Extension Plan

> I focused on Android for the 4-6 hour budget. Below is the plan to extend to iOS without changing the architecture.

### Step-by-step (estimate: 1-2 hours)

1. **Install iOS toolchain**
   ```bash
   xcode-select --install
   xcrun simctl list devices                  # verify
   ```
2. **Install Appium iOS driver**
   ```bash
   appium driver install xcuitest
   ```
3. **Open Runner.app in simulator**
   ```bash
   xcrun simctl boot "iPhone 16"
   open -a Simulator
   ```
4. **Add iOS Locator to existing YAML**
   ```yaml
   Add_Expense_Amount_Field:
     android:
       accessibility_id: "Amount Input"
     ios:
       accessibility_id: "Amount Input"
   ```
5. **Add platform capability in conftest.py**
   ```python
   if platform == "ios":
       caps["platformName"] = "iOS"
       caps["app"] = "path/to/Runner.app"
   ```
6. **Re-run the same feature files** — no `.feature` changes needed

### Known iOS Flutter Differences

| Issue | Android | iOS |
|-------|---------|-----|
| Element ID format | `com.trackify.app:id/amount` | `XCUIElementTypeTextField` |
| Back navigation | Hardware / Software button | Edge swipe gesture |
| Long press | `long_press` mobile action | `mobile:touchAndHold` |
| Date picker | Native | Wheel picker (different XPath) |
| Photo upload | File picker (gallery) | Photo library picker |

The **Locator YAML structure already supports per-platform** — only the iOS values need filling in.

---

## CI

Minimal GitHub Actions workflow at `.github/workflows/ci.yml`:

- Trigger: push to `test` / pull_request
- Steps: install Appium, start emulator, run pytest, upload Allure report as artifact
- See the file for full config

---

## Honest Reflection

See [`docs/REFLECTION.md`](docs/REFLECTION.md) for what I did well, what I'd do differently, and what I'd improve with more time.

---

## License

MIT — for educational evaluation purposes.
