# Trackify Mobile UI Automation

<p align="center">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</p>

> AI-assisted End-to-End mobile automation for **Trackify** (Flutter personal-finance tracker).
>
> Built as part of the Trackify Challenge.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/) [![Appium](https://img.shields.io/badge/Appium-3.x-green)](https://appium.io/) [![pytest-bdd](https://img.shields.io/badge/pytest--bdd-BDD-orange)](https://pytest-bdd.readthedocs.io/) [![Allure](https://img.shields.io/badge/Allure-Reporting-yellow)](https://allurereport.org/)

---

## Quick View

This repository demonstrates more than a set of UI scripts: it treats mobile
automation as a small test platform with explicit architecture, deterministic
state, cross-platform execution, and attributable reports.

**Start here**: [sample Android + iOS matrix report](docs/reports/device-matrix-preprod-sample.md)
| [technical specification](docs/TECHNICAL_SPEC.md) |
[architecture decisions](docs/DESIGN.md) |
[honest reflection](docs/REFLECTION.md)

| Engineering highlight | Evidence in this repository |
|---|---|
| Contract-driven BDD | Seven versioned scenarios, a controlled Gherkin vocabulary, reusable steps, and strict pytest markers |
| Layered architecture | Gherkin → Step Definitions → Flow → Page Object → Appium Driver; each layer has a clear ownership boundary |
| Cross-platform locator strategy | Platform-specific YAML locators with `accessibility_id` first and bounded fallback strategies for Flutter semantics |
| Deterministic isolation | App state is reset before every scenario, then the same required onboarding baseline is completed |
| Multi-device concurrency | One command discovers all ready Android and iOS targets, then either replicates or shards the suite across isolated workers |
| Collision-free Appium sessions | Unique Android `systemPort`, iOS WDA/MJPEG ports, and WDA derived-data paths per device |
| Traceable reporting | Environment, platform, device, OS version, UDID, per-case result, JUnit, logs, screenshots, and merged Allure results |
| Advisory failure triage | Deterministic local signatures classify the first failed phase; an explicitly enabled Claude fallback handles ambiguous failures |
| Reviewable engineering process | The technical specification defines layer rules, acceptance criteria, anti-patterns, and task-sized commits |

AI failure triage is implemented. The Excel-to-Gherkin synchronization described
in the technical specification remains an extension contract, not a claim about
the currently shipped runtime.

---

## Reproduction Guide

Once Android/iOS tooling and simulators are available, the following path takes
any user from clone to a report without needing to understand the framework
internals first.

### 1. Clone and install dependencies

```bash
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

# Install uv first when it is not already available on macOS
brew install uv
uv sync
npm install -g appium allure-commandline
appium driver install uiautomator2
appium driver install xcuitest
```

### 2. Provide the app builds

App binaries are intentionally excluded from Git. Place the builds at these
default paths:

| Target | Required build | Default path |
|---|---|---|
| Android emulator/device | APK | `app/app-release.apk` |
| iOS Simulator | Simulator `.app` bundle | `app/Runner.app` |
| Physical iOS device | Signed device `.ipa` or `.app` | Any path passed with `--ios-real-app` |

```bash
mkdir -p app
cp /path/to/app-release.apk app/app-release.apk
cp -R /path/to/Runner.app app/Runner.app
```

An iOS Simulator cannot install a device-only build. `Runner.app` must be built
for the Simulator architecture.

### 3. Boot and verify targets

Start the desired emulators/simulators before running the commands below.

```bash
# Ready Android targets must show the state "device"
adb devices -l

# Ready iOS Simulators must show the state "Booted"
xcrun simctl list devices booted
```

### 4. Start Appium in a dedicated terminal

The Android SDK variables must be set in the same terminal that starts Appium.
Leave this process running.

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium
```

### 5. Preview what will run

In a second terminal, from the repository root:

```bash
.venv/bin/python scripts/run_device_matrix.py --list

# Preview both device discovery and split assignment without running tests
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list
```

Confirm that every intended device, OS version, and UDID appears in the list.
This command does not install the app or execute tests.

### 6. Execute and open the report

```bash
# All 7 scenarios on every discovered Android and iOS target
.venv/bin/python scripts/run_device_matrix.py --env preprod

# Split the 7 scenarios across all targets; each scenario runs exactly once
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod
```

The default `replicate` distribution validates the full suite on every device.
Use `split` when the goal is reducing total suite duration by assigning a
disjoint subset to each device.

The runner prints the exact summary and Allure paths when it finishes:

```text
[matrix] Summary: .../report/device-matrix/preprod/<timestamp>/summary.md
[matrix] Allure:  .../report/device-matrix/preprod/<timestamp>/allure-report/index.html
```

Open `summary.md` directly on GitHub or in an editor. Open the generated HTML
report on macOS with:

```bash
open "$(find report/device-matrix/preprod -path '*/allure-report/index.html' -print | sort | tail -1)"
```

For a platform-limited setup, use one of these commands instead:

```bash
# Every connected Android target
.venv/bin/python scripts/run_device_matrix.py --platform android --env preprod

# Every booted/paired iOS target
.venv/bin/python scripts/run_device_matrix.py --platform ios --env preprod
```

Expected evidence includes a device-level summary, individual case results,
per-device pytest/JUnit artifacts, a merged Allure report, and screenshots for
call-stage failures. Compare the output with the committed
[sample report](docs/reports/device-matrix-preprod-sample.md).

### Common setup failures

| Symptom | Check |
|---|---|
| No devices discovered | Run `adb devices -l` and `xcrun simctl list devices booted`; boot or reconnect the target |
| Appium connection refused | Confirm the dedicated `appium` terminal is still running on port `4723` |
| Android SDK not found | Export `ANDROID_HOME` and `ANDROID_SDK_ROOT` before starting Appium, then restart Appium |
| Android/iOS app not found | Confirm `app/app-release.apk` and/or `app/Runner.app` exists from the repository root |
| XCUITest driver missing | Run `appium driver install xcuitest` |
| Physical iOS build requested | Pair/unlock the device, enable Developer Mode, and provide `--ios-real-app <signed-build>` |

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

# Appium and Allure CLIs
npm install -g appium allure-commandline
appium driver install uiautomator2

# Put the local APK in the ignored app directory, then install it
mkdir -p app
cp /path/to/app-release.apk app/app-release.apk
adb devices
adb install -r -t app/app-release.apk

# Finally, start Appium in a dedicated terminal and leave it running
appium
```

### Run Tests

Real UI runs require a running Android device/emulator, `app/app-release.apk`,
and an Appium server. Every business scenario clears the app database and
completes the required onboarding (name, currency, Monthly budget, and Bank SMS
Reader), so the full seven-scenario run takes several minutes.

Commands below use `uv`. If the repository already has a `.venv` but `uv` is
not installed, replace `uv run pytest` with
`.venv/bin/python -m pytest`.

#### Command index

The table below is the complete command-oriented entry point for the current
test suite. Detailed examples follow it.

| Category | Command | Purpose |
|---|---|---|
| Validate BDD collection | `uv run pytest -m "not unit" --collect-only -q` | Parse the 7 mobile scenarios without opening an Appium session |
| Matrix unit tests | `.venv/bin/python -m unittest discover -s unit_tests -v` | Validate device sharding without Appium or a mobile device |
| Triage unit tests | `uv run pytest -m unit tests/unit/test_triage.py -q` | Validate Task 13 without Appium, devices, or network calls |
| Default single device | `uv run pytest -m "not unit"` | Run all 7 scenarios on the default Android target |
| Explicit Android device | `PLATFORM=android DEVICE_UDID=<udid> APP_PATH="$PWD/app/app-release.apk" uv run pytest -m "not unit"` | Run all scenarios on one Android emulator or physical device |
| Explicit iOS simulator | `PLATFORM=ios DEVICE_UDID=<udid> APP_PATH="$PWD/app/Runner.app" uv run pytest -m "not unit"` | Run all scenarios on one booted iOS simulator |
| Feature | `uv run pytest tests/features/add_transaction.feature -q` | Run one feature file (5 Add Transaction scenarios) |
| Marker | `uv run pytest -m smoke -q` | Run a priority or functional subset |
| Scenario | `uv run pytest -k "add_expense_happy_path" -q` | Run one generated pytest scenario name |
| Replicate across devices | `.venv/bin/python scripts/run_device_matrix.py --env preprod` | Run all 7 scenarios on every discovered Android and iOS target |
| Split across devices | `.venv/bin/python scripts/run_device_matrix.py --distribution split --env preprod` | Split the selected suite across devices so each scenario runs exactly once |
| Android matrix | `.venv/bin/python scripts/run_device_matrix.py --platform android --env preprod` | Run all connected Android targets concurrently |
| iOS matrix | `.venv/bin/python scripts/run_device_matrix.py --platform ios --env preprod` | Run all booted iOS simulators and paired iOS devices concurrently |
| Selected devices | `.venv/bin/python scripts/run_device_matrix.py --env preprod --device <udid-1> --device <udid-2>` | Run only the listed devices; repeat `--device` as needed |
| Matrix subset | `.venv/bin/python scripts/run_device_matrix.py --env preprod -- -m smoke` | Forward pytest arguments after `--` to every device worker |
| Reported run | `uv run pytest -m "not unit" --alluredir=./allure-results --clean-alluredir` | Produce Allure raw results for a single-device run |
| Failure/debug | `uv run pytest -m "not unit" -x -s -vv` | Stop on the first failure and show uncaptured diagnostic output |

Use `.venv/bin/python -m pytest` instead of `uv run pytest` in any row when
`uv` is unavailable. Start Appium before any command that executes UI tests.

#### Full suite

```bash
# Run all 7 BDD scenarios
uv run pytest -m "not unit"

# Concise output
uv run pytest -m "not unit" -q
```

#### By feature

```bash
# 5 Add Transaction scenarios
uv run pytest tests/features/add_transaction.feature -q

# 2 Transactions scenarios
uv run pytest tests/features/transactions.feature -q
```

#### By priority or function marker

```bash
# 4 P0 smoke scenarios
uv run pytest -m smoke -q
uv run pytest -m p0 -q

# 3 P1 scenarios
uv run pytest -m p1 -q

# One targeted workflow
uv run pytest -m custom_category -q
uv run pytest -m filter -q
uv run pytest -m grouping -q

# All current priorities
uv run pytest -m "p0 or p1" -q
```

`regression` is registered in `pytest.ini`, but no scenario currently has the
`@regression` tag. `uv run pytest -m regression` therefore collects zero tests.

#### One scenario

Use a generated test-name substring with `-k`:

```bash
uv run pytest -k "add_expense_happy_path" -q
```

Available selectors:

```text
add_expense_happy_path
add_income_happy_path
add_transfer_happy_path
validation__empty_amount_shows_error_and_does_not_save
add_expense_with_new_custom_category_created_in_flow
filter_transactions_by_type_shows_only_matching_type
transactions_grouped_by_date_with_section_headers
```

#### Collection only

This validates imports, Gherkin parsing, markers, and step matching without
starting Appium or executing a scenario:

```bash
uv run pytest -m "not unit" --collect-only -q
```

#### Allure results and failure screenshots

```bash
uv run pytest \
  -m "not unit" \
  --alluredir=./allure-results \
  --clean-alluredir

# Open a temporary report server
allure serve ./allure-results

# Or generate a static report
allure generate ./allure-results --clean -o ./allure-report
open ./allure-report/index.html
```

Call-stage failures automatically save PNG evidence under
`report/screenshots/` and attach it to the corresponding Allure result.

#### Failure-focused and debug runs

```bash
# Stop on the first failure
uv run pytest -m "not unit" -x -vv

# Stop after one failure
uv run pytest -m "not unit" --maxfail=1 -vv

# Rerun only failures from the previous pytest run
uv run pytest -m "not unit" --lf -vv

# Disable output capture while debugging
uv run pytest -m "not unit" -s -vv
```

#### Override the local Appium target

Defaults already point to Android, `app/app-release.apk`, and
`http://127.0.0.1:4723`. Override them when using another local target:

```bash
PLATFORM=android \
APP_PATH="$PWD/app/app-release.apk" \
DEVICE_NAME="Android Emulator" \
APPIUM_SERVER_URL="http://127.0.0.1:4723" \
uv run pytest -m "not unit"
```

#### Run on every connected device

The device-matrix runner discovers every ready Android target from `adb` and
every booted iOS simulator from `simctl`. It starts one isolated pytest process
per device and runs them concurrently. `replicate` runs the selected suite on
every device; `split` distributes disjoint subsets across devices. The test
environment defaults to `preprod`.

| Distribution | Behavior with 7 tests and 2 devices | Best for |
|---|---|---|
| `replicate` (default) | A runs 7, B runs 7; 14 device-case executions | Cross-platform/device compatibility coverage |
| `split` | A runs 4, B runs 3; 7 device-case executions | Faster feedback for one logical suite |

```bash
# Preview the discovered matrix without running tests
.venv/bin/python scripts/run_device_matrix.py --list

# Preview the exact split assignment without starting Appium sessions
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list

# Run all seven scenarios on every discovered Android and iOS device
.venv/bin/python scripts/run_device_matrix.py --env preprod

# Split all seven scenarios across discovered devices (4 + 3 on two devices)
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod

# Run every connected Android device only
.venv/bin/python scripts/run_device_matrix.py \
  --platform android \
  --env preprod

# Run every booted/paired iOS device only
.venv/bin/python scripts/run_device_matrix.py \
  --platform ios \
  --env preprod

# Run only smoke scenarios on the full matrix
.venv/bin/python scripts/run_device_matrix.py --env preprod -- -m smoke

# Collect smoke scenarios, then split that subset across the matrix
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  -- \
  -m smoke

# Run one device by UDID
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --device emulator-5554

# Run a selected Android + iOS pair (repeat --device for more targets)
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  --device emulator-5554 \
  --device BFE1DE67-0F95-47B7-A02A-D25EE83CD999

# Include connected physical iOS devices using a signed device build
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

Before running, start Appium once and leave it running:

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium
```

The Android SDK variables must be present in the terminal that starts Appium;
setting them only in the pytest terminal does not update an existing Appium
process.

Each device receives a unique Appium backend port and isolated artifact
directories. Results are written under:

```text
report/device-matrix/<environment>/<timestamp>/
├── summary.md                    # Human-readable status by device
├── summary.json                  # Machine-readable matrix result
├── allure-results/               # Combined raw Allure results
├── allure-report/index.html      # Combined static report
├── android-<device>-<udid>/
│   ├── pytest.log
│   ├── junit.xml
│   ├── allure-results/
│   └── screenshots/
└── ios-<device>-<udid>/
    ├── pytest.log
    ├── junit.xml
    ├── allure-results/
    └── screenshots/
```

Every Allure test result includes the environment, platform, device name,
operating-system version, and UDID. The matrix summary reports passed, failed,
error, and skipped counts separately for each device. It also records the
distribution strategy and the exact node IDs assigned to each device. If there
are more devices than selected tests in `split` mode, excess devices remain
idle instead of starting empty pytest sessions.

See the committed [preprod matrix report example](docs/reports/device-matrix-preprod-sample.md),
captured from a real run of all seven scenarios on Android 17 and iOS 26.5.

Physical iOS devices must be paired, unlocked, in Developer Mode, and visible
to `xcrun devicectl list devices`. Because `mobile: clearApp` is simulator-only,
the runner resets a physical iOS target by uninstalling and reinstalling the
signed app before each scenario.

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
| Budget configuration as a standalone journey | Monthly budget exists in first-run onboarding and is verified through Home summary calculations; no separate Budget Management scenario was selected |

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
│   ├── reports/                    # Reviewable, committed report examples
│   ├── SCALING.md                  # Long-term scaling roadmap
│   └── TECHNICAL_SPEC.md           # Implementation contract
├── tests/
│   ├── features/
│   │   ├── add_transaction.feature # Five Add Transaction scenarios
│   │   └── transactions.feature    # Filter and grouping scenarios
│   ├── step_defs/                  # pytest-bdd step implementations
│   ├── unit/test_triage.py         # Device-free Task 13 coverage
│   └── __init__.py
├── ai/triage.py                    # Local + optional Claude failure triage
├── unit_tests/                     # Device-free matrix sharding tests
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
├── scripts/
│   ├── run_device_matrix.py        # Concurrent Android + iOS runner
│   └── sync_engine.py              # Excel sync extension scaffold
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
| Failure triage | Implemented bounded local signatures and an opt-in Claude fallback | Verified every category, privacy rule, fallback failure, and controlled pytest failure |
| Documentation | Structured architecture and reflection material | Reconciled every claim with the repository and latest run |

AI shortened investigation time, but live Appium behavior overruled generated
assumptions whenever they disagreed.

---

## AI Failure Triage

The first failed pytest phase (`setup`, `call`, or `teardown`) receives one
advisory triage result. The verdict never changes the pytest outcome, hides the
original traceback, retries a test, or files a bug automatically.

```text
[AI Triage] Locator (98%): Matched local failure signature 'element_missing'.
```

The always-on local stage uses deterministic signatures for `Locator`,
`App Bug`, `Env`, `Script`, and `Data`. Weak or unknown signals return
`Unknown`; confidences are never added together. Results are attached to Allure
as `AI Triage` JSON with the schema version, test, failing phase, category,
confidence, reasoning, next action, classifier, and matched signature IDs.

Claude fallback is disabled by default. Enable it only when all three variables
are intentionally configured:

```bash
export AI_TRIAGE_LLM_ENABLED=1
export ANTHROPIC_API_KEY="<key>"
export ANTHROPIC_MODEL="<model>"
```

The fallback is attempted only below `0.70` local confidence. It uses one
standard-library HTTP request, no retry, and a five-second timeout. Failure text
is bounded and redacted before network use; authorization values, tokens, API
keys, and URL queries are removed. Screenshots are never uploaded: only an
availability flag and basename may enter the prompt. Any missing configuration,
timeout, HTTP error, or invalid response safely returns `Unknown`.

Run all Task 13 tests without Appium, a device, or network access:

```bash
uv run pytest -m unit tests/unit/test_triage.py -q
```

---

## Test Results

After every run, see:

- **Allure report**: `allure-report/index.html` (open in browser)
- **Screenshots on failure**: `report/screenshots/`
- **Committed report example**: [preprod Android + iOS matrix report](docs/reports/device-matrix-preprod-sample.md)

### Latest Verified Run

```
Passed: 7 / Failed: 0 / Skipped: 0
Add Transaction: 5 passed
Transactions:    2 passed
```

Command: `uv run pytest -m "not unit" --alluredir=./allure-results`

---

## iOS Support

> The full suite is device-validated on Android and on an iPhone 17 simulator
> running iOS 26.5. Other iOS device sizes and locale settings may require
> additional locator or picker calibration.

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
4. **Review the iOS entries when the app UI or simulator profile changes**
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
   uv run pytest -m "not unit"
   ```
6. **Adapt native picker and back-navigation mechanics inside Pages only**

### Known iOS Flutter Differences

| Issue | Android | iOS |
|-------|---------|-----|
| Semantic tree | UiAutomator2 classes | XCUIElementType classes |
| Back navigation | Android button/navigation | iOS button or edge gesture |
| Date/time picker | Android calendar/clock | iOS wheel or compact picker |
| Permission dialog | Android runtime permission | iOS system alert |

The current iOS entries were verified against the bundled `Runner.app` on an
iPhone 17 simulator running iOS 26.5. Run the full suite when changing the app,
simulator profile, locale, or 12/24-hour time setting.

---

## CI

The workflow at `.github/workflows/ci.yml` has two levels:

- Every push to `test`, pull request, and manual dispatch installs dependencies,
  runs device-free matrix distribution and failure-triage unit tests, and
  collects all seven BDD scenarios.
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
