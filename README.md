# Trackify Mobile UI Automation

<p align="center">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.zh-HK.md">繁體中文</a>
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
[honest reflection](docs/REFLECTION.md) |
[runner flow and call chain](docs/RUNNER_FLOW.md)

| Engineering highlight | Evidence in this repository |
|---|---|
| Contract-driven BDD | Seven versioned scenarios, a controlled Gherkin vocabulary, reusable steps, and strict pytest markers |
| Layered architecture | Gherkin → Step Definitions → Flow → Page Object → Appium Driver; each layer has a clear ownership boundary |
| Cross-platform locator strategy | Platform-specific YAML locators with `accessibility_id` first and bounded fallback strategies for Flutter semantics |
| Deterministic isolation | App state is reset before every scenario, then onboarding uses the validated `test`, `preprod`, or `prod` profile |
| Multi-device concurrency | One command discovers all ready Android and iOS targets, then either replicates or shards the suite across isolated workers |
| Collision-free Appium sessions | Unique Android `systemPort`, iOS WDA/MJPEG ports, and WDA derived-data paths per device |
| Traceable reporting | Environment, app version, platform, device, OS version, UDID, per-case result, JUnit, logs, screenshots, and merged Allure results |
| Advisory failure triage | Deterministic local signatures classify the first failed phase; an explicitly enabled Claude fallback handles ambiguous failures |
| Excel-managed living cases | A validated registry incrementally updates only managed Gherkin blocks, preserves unchanged bytes, and can run only changed scenarios |
| Reviewable engineering process | The technical specification defines layer rules, acceptance criteria, anti-patterns, and task-sized commits |

AI failure triage and Excel-to-Gherkin synchronization are both implemented.
The sync boundary deliberately stops at managed Scenario blocks: executable
step code, Pages, Flows, and locators remain code-owned.

---

## Demo Videos

### Smoke selection sharded across Android and iOS

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  -- \
  -m smoke
```

This demo shows pytest marker pass-through, automatic Android/iOS discovery,
parallel execution, collision-free Appium sessions, and a merged Allure report.
Because the command uses `split`, the selected smoke scenarios are distributed
across the ready device pool and each scenario runs exactly once; use the
default `replicate` mode when every device must run every selected scenario.

[Watch the smoke matrix demo on Bilibili](https://www.bilibili.com/video/BV17QKG6mEWW)

### Excel-driven changed-case health and intentional assertion failure

```bash
./scripts/run_changed_matrix.sh
```

The demo starts from one BDD Scenario, finds the same stable case ID in Excel,
and changes the action amount while deliberately leaving the expected result
unchanged. The health gate detects only that modified case, synchronizes its
managed Feature block, replicates it across the discovered Android and iOS
devices, and reports the failed case plus its assertion reason in Allure. The
failure is intentional: it demonstrates that a data/expectation mismatch is
observable, attributable to a case and device, and returned to the caller as an
unhealthy result rather than being hidden or self-healed.

[Watch the changed-case failure demo on Bilibili](https://www.bilibili.com/video/BV1EDKG6EELD)

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

Manual target management remains available:

```bash
# Ready Android targets must show the state "device"
adb devices -l

# Ready iOS Simulators must show the state "Booted"
xcrun simctl list devices booted
```

For an automated lifecycle, use `--prepare-devices` during the actual run. No
device name is required: each requested platform reuses one running virtual
target or deterministically selects and boots an installed target. The runner
then replaces the app from `app/`, runs pytest, waits 60 seconds, and shuts down
the selected Android emulator or iOS Simulator. Real devices are never started
or stopped automatically. Android AVDs started by the runner use
`-skip-adb-auth`, so the emulator does not block on the USB-debugging approval
dialog. Manually started emulators and physical devices may still require a
one-time **Always allow from this computer** confirmation.

### 4. Appium lifecycle

Before device preparation or pytest execution, the runner checks Appium's
`/status` endpoint. A ready local server is reused. If it is missing,
matrix execution starts it automatically, writes output to
`report/appium/appium.log`, and waits until `ready: true`. Use
`--no-auto-start-appium` to require a manually started local server. A server
that was already running before the command is never stopped. A server started
by the runner is stopped after the test run's `--shutdown-after` delay (60
seconds by default).

Remote Appium servers must be started on their host manually. For a local
manual start, set Android SDK variables in that same terminal:

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium --address 127.0.0.1 --port 4723
```

### 5. Preview what will run

In a second terminal, from the repository root:

```bash
.venv/bin/python scripts/run_device_matrix.py --list

# List installed virtual targets and show the zero-config automatic choices
.venv/bin/python scripts/run_device_matrix.py --list-available-devices

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

# Zero configuration: select one Android and one iOS target automatically
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --env preprod

# Explicit target override for deterministic compatibility runs
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --android-avd Pixel_10 \
  --ios-simulator "iPhone 17" \
  --env preprod

# Android-only lifecycle; use --shutdown-after 0 to keep it running for debug
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --platform android \
  --shutdown-after 0 \
  --env preprod
```

`--android-avd` takes an AVD name from `emulator -list-avds`.
`--ios-simulator` accepts an exact Simulator name or UDID. These preparation
commands run on the machine executing the script; a remote Appium host must run
the same script there or have its devices provisioned separately.

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
| Appium connection refused | Matrix commands can auto-start a local server; for direct pytest, start Appium on `4723` or pass `--appium-url` |
| Appium `/status` returns 502 | Verify the local endpoint without a proxy: `curl --noproxy '*' http://127.0.0.1:4723/status`; inspect `report/appium/appium.log` |
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

#### Select an environment profile

The same seven scenarios support three validated onboarding profiles:

| `--env` | Name | Currency | Bank SMS Reader |
|---|---|---|---|
| `test` | `Rose` | `$ US Dollar` | enabled |
| `preprod` (default) | `Kimbal` | `$ US Dollar` | enabled |
| `prod` | `Kimi` | `$ US Dollar` | enabled |

```bash
# Direct pytest on one configured device
uv run pytest --env test -m "not unit"
uv run pytest --env preprod -m "not unit"
uv run pytest --env prod -m "not unit"

# Matrix execution on every discovered device
.venv/bin/python scripts/run_device_matrix.py --env test
.venv/bin/python scripts/run_device_matrix.py --env preprod
.venv/bin/python scripts/run_device_matrix.py --env prod
```

Selection precedence is `--env` > `TEST_ENV` > `preprod`. Profile files live
under `data/environments/` and contain non-secret shared onboarding values only;
business inputs and expected results remain in Excel/Gherkin. Unsupported names
and invalid profile schemas fail before Appium starts.

`prod` is currently safe only because these scenarios clear and modify local
Trackify storage. Reassess destructive execution before the app is connected to
a shared production backend or credentials.

Completed runs also require a concrete app version. Resolution uses
`APP_VERSION`, then Appium capabilities, Android installed-package metadata, or
iOS `.app`/`.ipa` metadata. Set an explicit override when artifact metadata is
unavailable:

```bash
APP_VERSION=1.2.3 uv run pytest --env test -m "not unit"
```

#### Command index

The table below is the complete command-oriented entry point for the current
test suite. Detailed examples follow it.

| Category | Command | Purpose |
|---|---|---|
| Validate BDD collection | `uv run pytest -m "not unit" --collect-only -q` | Parse the 7 mobile scenarios without opening an Appium session |
| Matrix unit tests | `.venv/bin/python -m unittest discover -s unit_tests -v` | Validate device sharding without Appium or a mobile device |
| Triage unit tests | `uv run pytest -m unit tests/unit/test_triage.py -q` | Validate Task 13 without Appium, devices, or network calls |
| Sync unit tests | `uv run pytest -m unit tests/unit/test_sync_engine.py -q` | Validate Task 14 routing, incremental writes, byte preservation, and rollback |
| Check Excel drift | `uv run python scripts/sync_engine.py --check` | Validate the registry and report scenario-level drift without writing |
| Apply Excel drift | `uv run python scripts/sync_engine.py --apply` | Atomically update managed Feature blocks and collect pytest |
| Apply + run changes | `uv run python scripts/sync_engine.py --apply --run-changed` | Update, then execute only added/modified active scenarios |
| Changed cases on all devices | `./scripts/run_changed_matrix.sh` | Check, sync, then run every added/modified case concurrently on every discovered Android and iOS device |
| Default single device | `uv run pytest --env preprod -m "not unit"` | Run all 7 scenarios on the default Android target and profile |
| Explicit Android device | `PLATFORM=android DEVICE_UDID=<udid> APP_PATH="$PWD/app/app-release.apk" uv run pytest -m "not unit"` | Run all scenarios on one Android emulator or physical device |
| Explicit iOS simulator | `PLATFORM=ios DEVICE_UDID=<udid> APP_PATH="$PWD/app/Runner.app" uv run pytest -m "not unit"` | Run all scenarios on one booted iOS simulator |
| Feature | `uv run pytest tests/features/add_transaction.feature -q` | Run one feature file (5 Add Transaction scenarios) |
| Marker | `uv run pytest -m smoke -q` | Run a priority or functional subset |
| Scenario | `uv run pytest -k "add_expense_happy_path" -q` | Run one generated pytest scenario name |
| Replicate across devices | `.venv/bin/python scripts/run_device_matrix.py --env preprod` | Run all 7 scenarios on every discovered Android and iOS target |
| Split across devices | `.venv/bin/python scripts/run_device_matrix.py --distribution split --env preprod` | Split the selected suite across devices so each scenario runs exactly once |
| Explicit mapped shards | `.venv/bin/python scripts/run_device_matrix.py --distribution mapped --shard-config data/device_shards.local.yaml --env preprod` | Run exactly the cases assigned to each configured device and merge one report |
| List available devices | `.venv/bin/python scripts/run_device_matrix.py --list-available-devices` | Show installed targets, current state, UDID, and zero-config automatic choices |
| Managed device lifecycle | `.venv/bin/python scripts/run_device_matrix.py --prepare-devices --env preprod` | Automatically start/reuse Appium, choose/boot one target per platform, replace apps, run, wait 60s, then stop owned resources |
| Android matrix | `.venv/bin/python scripts/run_device_matrix.py --platform android --env preprod` | Run all connected Android targets concurrently |
| iOS matrix | `.venv/bin/python scripts/run_device_matrix.py --platform ios --env preprod` | Run all booted iOS simulators and paired iOS devices concurrently |
| Selected devices | `.venv/bin/python scripts/run_device_matrix.py --env preprod --device <udid-1> --device <udid-2>` | Run only the listed devices; repeat `--device` as needed |
| Matrix subset | `.venv/bin/python scripts/run_device_matrix.py --env preprod -- -m smoke` | Forward pytest arguments after `--` to every device worker |
| Reported run | `uv run pytest -m "not unit" --alluredir=./allure-results --clean-alluredir` | Produce Allure raw results for a single-device run |
| Failure/debug | `uv run pytest -m "not unit" -x -s -vv` | Stop on the first failure and show uncaptured diagnostic output |

Use `.venv/bin/python -m pytest` instead of `uv run pytest` in any row when
`uv` is unavailable. Direct single-device `pytest` commands still require a
manually running Appium server; matrix runners can manage a local server.

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
| `mapped` | The configured cases run only on their assigned devices | Reproducible ownership of case shards and one merged report |

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

# Prepare an explicit case-to-device mapping (edit the UDIDs after copying)
cp data/device_shards.example.yaml data/device_shards.local.yaml

# Preview the exact configured mapping without starting Appium sessions
.venv/bin/python scripts/run_device_matrix.py \
  --platform android \
  --distribution mapped \
  --env preprod \
  --shard-config data/device_shards.local.yaml \
  --list

# Run the configured mapping and produce one merged Allure report
.venv/bin/python scripts/run_device_matrix.py \
  --platform android \
  --distribution mapped \
  --env preprod \
  --shard-config data/device_shards.local.yaml
```

`data/device_shards.example.yaml` accepts stable case IDs such as
`TC_ADD_TX_001` or complete pytest node IDs. `mapped` requires every selected
pytest case to be assigned exactly once, and every configured device to be
currently discoverable. The generated `summary.md` and `summary.json` retain
the exact case-to-device assignment.

```bash
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

Every Allure test result includes the environment, tested app version, platform,
device name, operating-system version, and UDID. Each worker writes the same
fields to `environment.properties`; the combined matrix summary preserves the
app version per device instead of assuming Android and iOS artifacts are
identical. It also records passed/failed/error/skipped counts, distribution
strategy, and exact node IDs. In `split` mode, excess devices remain idle rather
than starting empty pytest sessions.

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
│   ├── test_cases.xlsx              # Working BDD registry/source of truth
│   └── test_cases_template.xlsx     # Reusable corrected seven-case baseline
├── scripts/
│   ├── run_changed_matrix.sh       # Check + sync + changed-case all-device health
│   ├── run_device_matrix.py        # Concurrent Android + iOS runner
│   └── sync_engine.py              # Incremental Excel-to-Gherkin sync
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

Task 13 is a failure-time diagnostic layer for real regression runs. Passing
cases do nothing. On the first failing `setup`, `call`, or `teardown` phase, it
preserves the original failure, captures available evidence, assigns an
advisory category, and suggests the next debugging action. This reduces initial
triage time while keeping the engineer responsible for the root-cause decision.

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

| `classifier` | User-visible meaning |
|---|---|
| `local` | A high-confidence local signature classified the failure; no API call occurred |
| `llm` | Local evidence was ambiguous and one configured compatible-model call was attempted |
| `disabled` | Ambiguous evidence could not use LLM because the switch, key, or model was missing |

The terminal prints one `[AI Triage] ...` line, and the same structured result
is attached to the failed Allure case. Always read it beside the original
traceback and screenshot; it is a hypothesis, not a confirmed root cause.

Claude-compatible fallback is disabled by default. Enable it only when the
switch, API key, and model are intentionally configured. `ANTHROPIC_BASE_URL`
is optional and defaults to the official Anthropic endpoint. For the MiniMax
Anthropic-compatible API:

```bash
export AI_TRIAGE_LLM_ENABLED=1
export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export ANTHROPIC_API_KEY="<key>"
export ANTHROPIC_MODEL="MiniMax-M3"
```

The engine appends `/v1/messages` without discarding a gateway path. Copying
`.env.example` is optional; this project does not auto-load `.env`, so source it
explicitly with `set -a; source .env; set +a`. `.env` is ignored and must never
be committed. Use a bare `AssertionError` for a live probe because strong local
signatures intentionally return before the network fallback.

```bash
cp .env.example .env
chmod 600 .env
# Edit .env: enable the fallback and replace the placeholder key.
set -a; source .env; set +a

.venv/bin/python -c "from dataclasses import asdict; from ai.triage import triage_failure; print(asdict(triage_failure({'error_msg': 'AssertionError', 'traceback': '', 'test_name': 'live_probe', 'phase': 'call'})))"
```

A successful live call reports `classifier: llm` with a non-placeholder
reasoning/action. A safe `HTTP 401`, `429`, connection, timeout, or invalid
response diagnosis is returned without exposing the endpoint response or key.
If a python.org macOS build reports `TLS certificate verification failed` and
`/etc/ssl/cert.pem` exists, export `SSL_CERT_FILE=/etc/ssl/cert.pem`; do not
disable certificate verification.

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

For configuration checks, local-vs-LLM probes, an actual pytest/Allure
verification flow, troubleshooting, and privacy guarantees, see
[`docs/AI_TRIAGE.md`](docs/AI_TRIAGE.md).

---

## Excel-Managed BDD Sync

[`data/test_cases.xlsx`](data/test_cases.xlsx) contains the current seven cases
as a maintainable 16-column registry. Excel owns metadata plus the managed
`Scenario` action/assertion blocks; Feature headers and `Background` remain
code-owned. Step definitions, Page/Flow code, test data, and YAML locators are
never generated or overwritten by the sync engine.

```bash
# Validate schema and show added/modified/deprecated/unchanged IDs; no writes
uv run python scripts/sync_engine.py --check

# Apply only validated scenario-level drift, then run pytest collection
uv run python scripts/sync_engine.py --apply

# Apply and execute only added/modified active scenarios
uv run python scripts/sync_engine.py --apply --run-changed

# One command: check, sync, and run every change on every Android/iOS device
./scripts/run_changed_matrix.sh

# Local five-second-debounced watch mode
uv run python scripts/sync_engine.py --watch --apply
```

`run_changed_matrix.sh` is the recommended cross-device health gate. It reads a
machine-readable change manifest, previews devices, applies the validated
Feature transaction, then uses matrix `replicate` mode. The delegated matrix
run automatically checks or starts a local Appium server, so a manually
running local server is optional. Examples:

```bash
# Default: preprod, every discovered Android + iOS device
./scripts/run_changed_matrix.sh

# Boot/reuse one explicit Android and iOS simulator, install apps, then wait
# 60 seconds and stop resources started by this command
./scripts/run_changed_matrix.sh \
  --prepare-devices \
  --android-avd Pixel_10 \
  --ios-simulator "iPhone 17"

# Every ready Android target only
./scripts/run_changed_matrix.sh --platform android

# Two selected targets; repeat --device for each UDID
./scripts/run_changed_matrix.sh \
  --device <android-udid> \
  --device <ios-udid>

# Physical iOS targets require a signed package
./scripts/run_changed_matrix.sh \
  --platform ios \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

Exit `0` means no pending runnable change or all changed cases passed on every
selected device. Exit `1` means at least one changed case failed on at least one
device. Exit `2` means the pipeline could not complete because of validation,
collection, device, Appium, app, lock, or I/O failure. Reports are written below
`report/changed-device-matrix/<environment>/<timestamp>/`; `summary.md` contains
a Changed Case Health table keyed by test case ID and device, `summary.json`
contains the same machine-readable selection and results, and the directory also
contains per-device logs/JUnit/screenshots plus merged Allure evidence.

The engine validates all rows and both features before its first write. It uses
an allowlisted Module-to-file route, stable `scenario_id`, timestamped backups,
same-directory temporary files, `os.replace`, a concurrent-writer lock, and
post-write pytest collection. Collection failure restores every changed Feature.
Unchanged managed blocks are reused as exact source slices and remain
byte-identical after neighboring additions, modifications, or deprecations.

`--run-changed` is the targeted implementation/debug loop. Passing cases return
a concise success message and Allure path. Runtime failures keep the valid
Feature update, run through Task 13 and screenshot reporting, and print the exact
pytest retry command plus a prompt to inspect step definitions, Page/Flow code,
and YAML locators. The engine does not guess or self-heal locators; those changes
require Appium evidence and code review. A collection failure, such as an
unimplemented Gherkin phrase, rolls the Feature update back and reports the
missing implementation.

The workbook itself is always read-only to the engine, including `--apply` and
watch mode. Missing rows never mean delete; use `Automation Status=deprecated`
with an explicit deprecated version.

### End-to-end operator verification

Use this workflow to prove that one Excel change updates and runs only one
scenario. Keep any real case changes; the restore commands at the end are only
for a disposable exercise.

1. Establish the committed baseline:

   ```bash
   git status --short
   uv run python scripts/sync_engine.py --check
   echo $?
   ```

   A clean baseline reports five unchanged `add_transaction` cases and two
   unchanged `transactions` cases, then exits `0`.

2. Open `data/test_cases.xlsx`, select the `Test Cases` sheet, and find
   `TC_ADD_TX_001`. For a simple drill, change amount `100` to `101` in both
   `Test Steps` and every matching amount assertion in `Expected Result`. Save
   and close Excel so it stops writing temporary files.

3. Preview the scenario-level change without writing Feature files:

   ```bash
   uv run python scripts/sync_engine.py --check
   echo $?
   git status --short
   ```

   The expected result is exactly one `modified: TC_ADD_TX_001`, no change in
   the `transactions` module, and exit `1`. Exit `1` here means valid drift was
   found; it is not a sync error.

4. Choose one apply path. To validate generation without a device, run:

   ```bash
   uv run python scripts/sync_engine.py --apply
   ```

   To apply and immediately run the changed case on Android instead, run:

   ```bash
   PLATFORM=android \
   DEVICE_UDID=<android-udid> \
   APP_PATH="$PWD/app/app-release.apk" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   Get the Android UDID with `adb devices`. For a booted iOS simulator, use:

   ```bash
   PLATFORM=ios \
   DEVICE_UDID=<ios-simulator-udid> \
   APP_PATH="$PWD/app/Runner.app" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   Get the iOS UDID with `xcrun simctl list devices booted`. Do not run plain
   `--apply` first if the goal is changed-case execution: after a successful
   apply there is no remaining drift, so a later `--run-changed` has nothing to
   select. Edit the workbook again if generation was already applied.

5. Confirm the scope and final state:

   ```bash
   git diff -- tests/features/add_transaction.feature
   git diff -- tests/features/transactions.feature
   uv run python scripts/sync_engine.py --check
   ```

   Only the managed `TC_ADD_TX_001` block should differ. The final check exits
   `0`. A successful device run names the case, exact pytest node ID, scenario
   count, and `report/sync/<timestamp>/allure-results` directory.

6. Inspect failure feedback when a changed mobile case fails. The valid Feature
   update stays in place for debugging, while the console prints the exact retry
   command and points to Task 13 triage, screenshots, Allure, step definitions,
   Page/Flow code, and YAML locators. Locators are never changed automatically.

7. Optionally verify collection rollback by changing the Scenario Title in
   Excel without updating its Python `@scenario` binding, then running
   `--apply`. Collection should fail with exit `2`, restore the Feature backup,
   and remove the lock. The workbook remains changed, so `--check` will continue
   to report drift until the title is corrected.

8. Restore the committed baseline after a disposable drill:

   ```bash
   git restore data/test_cases.xlsx
   uv run python scripts/sync_engine.py --apply
   uv run python scripts/sync_engine.py --check
   git status --short
   ```

   Do not use `git restore` for real case edits. In `git status --short`, `M`
   means a tracked file changed and `??` means an untracked file. `uv.lock` may
   be created by `uv`; it is a dependency lockfile, not sync-engine output, and
   should be reviewed and committed separately from case changes.

Command exit codes are `0` for no drift/success, `1` for check-mode drift or a
changed-case runtime failure, and `2` for validation, collection, lock, or I/O
errors.

Run Task 14 tests without Appium or a device:

```bash
uv run pytest -m unit tests/unit/test_sync_engine.py -q
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
  runs device-free matrix, failure-triage, and sync unit tests; rejects Excel
  registry drift; and collects all seven BDD scenarios.
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

---

## Support This Project

If this open-source project saved you some setup or debugging time and you would
like to support its continued maintenance, you are welcome to buy me a **CNY 10
Mixue drink**. Support is entirely optional and does not affect project usage,
issue responses, or roadmap priorities. A Star, Issue, or Pull Request is also
greatly appreciated.

<table>
  <tr>
    <td align="center">
      <strong>Alipay</strong><br><br>
      <img src="docs/assets/donate/alipay.png" alt="Alipay support QR code" width="260">
    </td>
    <td align="center">
      <strong>WeChat Pay</strong><br><br>
      <img src="docs/assets/donate/wechat-pay.png" alt="WeChat Pay support QR code" width="260">
    </td>
  </tr>
</table>
