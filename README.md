# Trackify Mobile UI Automation

> AI-assisted End-to-End mobile automation for **Trackify** (Flutter personal-finance tracker).
>
> Built as part of the Trackify Challenge.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/) [![Appium](https://img.shields.io/badge/Appium-3.x-green)](https://appium.io/) [![pytest-bdd](https://img.shields.io/badge/pytest--bdd-BDD-orange)](https://pytest-bdd.readthedocs.io/) [![Allure](https://img.shields.io/badge/Allure-Reporting-yellow)](https://allurereport.org/)

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
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- Node.js LTS
- Android SDK + Platform Tools (`adb`)
- An Android emulator or real device with **Android 10+**

### Setup

```bash
# Clone
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

# Python deps (using uv)
uv sync

# Appium drivers
npm install -g appium
appium driver install uiautomator2

# Start Appium server in one terminal
appium

# Put the local APK in the ignored app directory, then install it
mkdir -p app
cp /path/to/app-release.apk app/app-release.apk
adb install -r -t app/app-release.apk
```

### Run Tests

```bash
# All tests
uv run pytest

# Smoke only (P0)
uv run pytest -m smoke

# P1 scenarios
uv run pytest -m p1

# Single feature
uv run pytest tests/features/add_transaction.feature

# With Allure report
uv run pytest --alluredir=./allure-results
allure serve ./allure-results
```

---

## Test Coverage

We focused on the **two highest-value features** of the user journey:

| Feature | Sub-features | P0 | P1 | Total | Why chosen |
|---------|--------------|----|----|-------|------------|
| **Home → Add Transaction shortcut** | Add Expense / Income / Transfer; amount, category (+ custom), date, note, tags, photo upload | 4 | 1 | 5 | The primary entry point for recording any transaction; downstream data source for Home summary, Transactions list, and Analytics |
| **Transactions list** | Filter by type; date-grouped summary | 0 | 2 | 2 | Validation surface — the same data must appear correctly here after Add |

### Detailed Sub-feature Coverage

#### Home → Add Transaction shortcut

| Sub-feature | Priority |
|-------------|----------|
| Add Expense with amount, Food category, note, tags, persistence, and Home summary assertions | P0 |
| Add Income with amount, Salary category, tags, persistence, and Home summary assertions | P0 |
| Add Transfer and verify it does not change current-month income or expense | P0 |
| Reject an empty amount without creating a transaction or changing Home totals | P0 |
| Create and use the custom category `baby cost` in the Add Transaction flow | P1 |

#### Transactions list

| Sub-feature | Priority |
|-------------|----------|
| Filter an Expense from mixed Expense and Income data | P1 |
| Group a transaction at `2025-05-06 9:00 AM` under `06 May 2025` | P1 |

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
├── .github/workflows/ci.yml        # Collection + gated Android E2E
├── docs/
│   ├── DESIGN.md                   # Architecture and tradeoffs
│   ├── Feature_Inventory.md        # Manual feature exploration
│   ├── REFLECTION.md               # Outcomes and limitations
│   ├── SCALING.md                  # Long-term scaling roadmap
│   └── TECHNICAL_SPEC.md           # Implementation contract
├── tests/
│   ├── features/
│   │   ├── add_transaction.feature # Five Add Transaction scenarios
│   │   └── transactions.feature    # Filter and grouping scenarios
│   ├── step_defs/                  # pytest-bdd step implementations
│   └── __init__.py
├── locator/
│   ├── onboarding.yaml
│   ├── home.yaml
│   ├── add_transaction.yaml
│   └── transactions.yaml
├── page/
│   ├── base_page.py
│   ├── onboarding_page.py
│   ├── home_page.py
│   ├── add_transaction_page.py
│   └── transactions_page.py
├── flow/
│   ├── app_setup_flow.py
│   ├── add_transaction_flow.py
│   └── transactions_flow.py
├── utils/
│   ├── config.py                   # Environment and pytest.ini config
│   ├── driver.py                   # Appium driver factory
│   ├── locator_loader.py           # YAML locator resolver
│   └── system_dialogs.py           # Notification permission handling
├── data/
│   ├── test_data.yaml
│   └── test_cases_template.xlsx
├── scripts/sync_engine.py
├── report/                         # Generated screenshots (ignored)
├── app/app-release.apk             # Local APK (ignored)
├── conftest.py                     # Driver, reset, Pages, Flows, reporting
├── pytest.ini
└── pyproject.toml
```

### Layered Architecture

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

- Step definitions do not call Appium directly.
- Flows own business expectations and compose Pages.
- Pages own UI interaction and use explicit waits instead of fixed sleeps.
- Locator values stay in YAML; scoped XPath is a fallback when Flutter exposes
  no stable semantic identifier.
- Every scenario starts from a clean package database and completes onboarding.

---

## Design Decisions

See [`docs/DESIGN.md`](docs/DESIGN.md) for full architectural justification.

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| BDD framework | pytest-bdd | behave | Stays inside pytest ecosystem |
| Locator format | YAML | Python dict | Easier for non-devs to edit |
| Reset DB | `pm clear` | App UI | Deterministic for automation |
| Failure evidence | Allure + PNG | Plain logs | Traceback plus visible app state |
| Feature focus | Home + Transactions | Expense CRUD + Budget | Home is the primary entry point; Transactions validates downstream correctness |

---

## AI Usage

AI assistance was used deliberately, with emulator evidence as the final source
of truth:

| Phase | AI contribution | Human verification |
|-------|-----------------|--------------------|
| Scope and BDD design | Compared candidate journeys and refined seven scenarios | Checked against the explored app and specification |
| Locator analysis | Interpreted Appium XML and screenshots to suggest stable selectors | Exercised every selector on the Android emulator |
| Implementation | Drafted Page, Flow, fixture, and reporting changes | Reviewed diffs and ran focused plus full regression tests |
| Debugging | Formed hypotheses for keyboard, category, date picker, and transition failures | Accepted changes only after reproducing and rerunning the failing path |
| Documentation | Structured architecture and reflection material | Reconciled every claim with the repository and latest run |

AI shortened investigation time, but live Appium behavior overruled generated
assumptions whenever they disagreed.

---

## Test Results

After every run, see:

- **Allure report**: `allure-report/index.html` (open in browser)
- **Screenshots on failure**: `report/screenshots/`

### Latest Verified Run

```
Passed: 7 / Failed: 0 / Skipped: 0
Add Transaction: 5 passed
Transactions:    2 passed
```

Command: `uv run pytest --alluredir=./allure-results`

---

## iOS Extension Plan

> The current suite is device-validated on Android. The existing platform
> boundary allows an iOS extension without changing Gherkin or Flow behavior.

### Step-by-step

1. **Install iOS toolchain**
   ```bash
   xcode-select --install
   xcrun simctl list devices                  # verify
   ```
2. **Install Appium iOS driver**
   ```bash
   appium driver install xcuitest
   ```
3. **Place and open Runner.app in the simulator**
   ```bash
   mkdir -p app
   cp -R /path/to/Runner.app app/Runner.app
   xcrun simctl boot "iPhone 16"
   open -a Simulator
   ```
4. **Validate the iOS entries in each existing locator YAML**
   ```yaml
   amount_input:
     android:
       xpath: "//android.view.View[@content-desc='$']/android.widget.EditText"
     ios:
       xpath: "(//XCUIElementTypeTextField)[1]"
   ```
5. **Run with the existing configuration boundary**
   ```bash
   PLATFORM=ios \
   APP_PATH="$PWD/app/Runner.app" \
   DEVICE_NAME="iPhone 16" \
   uv run pytest
   ```
6. **Adapt native picker and back-navigation mechanics inside Pages only**

### Known iOS Flutter Differences

| Issue | Android | iOS |
|-------|---------|-----|
| Semantic tree | UiAutomator2 classes | XCUIElementType classes |
| Back navigation | Android button/navigation | iOS button or edge gesture |
| Date/time picker | Android calendar/clock | iOS wheel or compact picker |
| Permission dialog | Android runtime permission | iOS system alert |

The iOS entries are placeholders until they are verified against a live
simulator.

---

## CI

The workflow at `.github/workflows/ci.yml` has two levels:

- Every push to `test`, pull request, and manual dispatch installs dependencies
  and collects all seven scenarios.
- Full Android E2E requires a repository secret named `TRACKIFY_APK_URL` that
  points to a downloadable APK. This is necessary because the app binary is not
  committed.
- With that secret present, CI starts an API 34 emulator and Appium, runs pytest,
  and uploads raw results, an HTML Allure report, failure screenshots, and
  `appium.log` for 14 days.
- Without the secret, the workflow emits an explicit notice and skips only the
  mobile job steps; collection still gates the change.

---

## Honest Reflection

See [`docs/REFLECTION.md`](docs/REFLECTION.md) for what I did well, what I'd do differently, and what I'd improve with more time.
