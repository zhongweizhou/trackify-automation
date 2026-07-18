# Project Reflection

## Outcome

The project now behaves as a small mobile test platform rather than a collection
of isolated UI scripts:

| Area | Delivered capability |
|---|---|
| Business coverage | Seven BDD scenarios across Add Transaction and Transactions |
| Platforms | Shared business flows on Android and iOS with platform-owned locators |
| Environments | Strict `test`, `preprod`, and `prod` onboarding profiles selected by CLI |
| Distribution | Full replication or disjoint sharding across every discovered device |
| Living cases | Validated Excel registry with incremental, transactional Feature updates |
| Diagnostics | Screenshots, logs, JUnit, Allure, and advisory Task 13 failure triage |
| Attribution | Environment, app version, device, OS version, and UDID per worker and case |

The isolated verification suite currently has 107 passing tests. All three
environment values collect the same seven BDD scenarios. Real execution used
Android 17 and an iPhone 17 simulator on iOS 26.5; both artifacts reported app
version `1.1.0`. The `test` matrix verified environment-aware onboarding on both
platforms, while focused `preprod` Android and `prod` iOS happy paths passed.

The repository intentionally retains one unhealthy demonstration: the Income
scenario enters `5002` but expects `5001.0`. It proves that the changed-case gate
returns an attributable failure on both platforms. It must not be presented as
a framework regression or as evidence that the full committed smoke selection
is currently green.

## What Worked Well

### Clear ownership between layers

Separating Gherkin, Steps, Flows, Pages, and locator YAML kept failures local.
Changing a keyboard interaction affects one Page method rather than every
scenario. Transaction calculations remain Flow behavior instead of leaking into
selectors or Gherkin.

The same ownership discipline now applies to data. Excel and managed Feature
blocks own scenario actions and expectations. `data/environments/` owns only
shared, non-secret onboarding values. Locator YAML owns UI selectors. This avoids
turning one spreadsheet into an untyped configuration database.

### Deterministic, environment-aware setup

Clearing app storage before every scenario is slower, but makes onboarding,
custom categories, and summary baselines repeatable. `--env` overrides
`TEST_ENV`, which overrides the `preprod` default; invalid names or YAML schemas
fail before Appium starts. Page Objects remain unaware of environment names, and
the Flow verifies the selected name, currency symbol, and SMS Reader state.

### Multi-device execution with explicit resource isolation

The matrix runner discovers Android emulators/devices, iOS simulators, and
paired iOS devices. It starts one pytest worker per target and supports two
different goals: `replicate` validates compatibility on every target, while
`split` shortens feedback by assigning each selected case exactly once.

Per-worker Android `systemPort`, iOS WDA/MJPEG ports, derived-data paths, logs,
screenshots, JUnit, and Allure directories prevent the most common concurrent
session collisions and keep failures attributable.

### Reports identify the tested build

Environment alone is not enough evidence. The runtime resolves app version from
an explicit override, Appium capability, Android installed-package metadata, or
iOS bundle metadata. Each Allure case and worker property file records the app
version beside platform, device, OS, and UDID. Matrix aggregation preserves
different versions per device instead of inventing one shared build identity.

### Living documentation has a bounded automation boundary

Task 14 validates the entire Excel registry, updates only managed Scenario
blocks, preserves unchanged blocks byte-for-byte, and rolls back Feature writes
when collection fails. `run_changed_matrix.sh` applies added/modified cases only
after preflight, then replicates them across selected devices and returns a
machine-meaningful health status.

The engine deliberately stops at executable Gherkin. It does not invent Step,
Flow, Page, or locator code and does not write test results back into Excel.
Those boundaries keep generated changes reviewable.

### Failure evidence remains primary

Allure keeps the original BDD Feature and Scenario names. Call-stage failures
attach screenshots without replacing the original traceback. Task 13 adds one
advisory category and next action, using deterministic local signatures first
and an explicitly enabled LLM only for ambiguous evidence. AI output never
changes pass/fail status, retries a test, or claims to be the confirmed cause.

## What Was Harder Than Expected

### Flutter accessibility semantics and keyboard state

Some controls expose stable accessibility IDs, while others are merged into
large semantics nodes or expose only positional text fields. Scoped XPath
fallbacks remain necessary. On both setup and transaction forms, keyboard state
also affects sliders and controls; completing the IME action is more reliable
than tapping arbitrary screen coordinates.

### Transitions and horizontal controls

The custom-category entry is at the end of a horizontal list and requires a
bounded swipe, creation flow, Back navigation, and chip selection. After Save,
the test must wait for Home before looking for another same-named shortcut;
otherwise a control on the closing form can be matched accidentally.

### Device concurrency does not remove infrastructure state

Unique ports prevent deterministic collisions, but WebDriverAgent still has its
own lifecycle. During final verification, an iOS session started immediately
after a previous matrix run failed in setup with `ECONNREFUSED 127.0.0.1:8100`.
The same command passed once WDA had fully restarted. The framework correctly
reported an `Env` setup failure and `unresolved` app version instead of hiding it
behind a blind retry. A future readiness probe should target this transition
explicitly.

### Keeping examples honest

The intentional `5002` versus `5001.0` mismatch is useful in a failure-demo
video, but it also means a normal smoke command is intentionally red. Reports
and documentation must distinguish fault injection from product or framework
regressions. A reusable project should generate this mismatch from temporary
demo data rather than keep the default registry unhealthy.

## Current Limitations

- Each worker is serial; matrix mode provides device-level concurrency, not
  multiple Appium sessions on one target.
- Full app reset makes each scenario slower than a targeted state fixture.
- The committed Income demo mismatch intentionally prevents a fully green smoke
  matrix until the input and expectation are aligned.
- iOS coverage is validated on one iPhone 17 simulator with iOS 26.5; broader
  device sizes, locales, and physical-device signing paths need more evidence.
- `prod` currently changes local app storage only. The profile does not authorize
  destructive execution against a future shared production backend.
- Task 14 remains one-way and does not generate implementation or self-heal
  locators.
- Task 13 remains advisory. Its opt-in compatible-model fallback needs a larger
  real-failure sample before changing confidence thresholds.
- GitHub-hosted E2E still requires externally supplied app artifacts.

## AI Assistance

AI helped turn requirements into explicit ownership rules, generate test and
documentation drafts, inspect Appium evidence, and shorten debugging loops. The
useful work was not accepting generated code quickly; it was comparing each
proposal with live page state, command output, and report artifacts.

That boundary is visible in both extension tasks. The sync engine generates only
deterministic managed text and validates it with pytest collection. Failure
triage treats model output as an attached hypothesis. Environment profiles and
app metadata use strict parsers and platform tools rather than asking a model to
guess runtime identity.

## Next Improvements

1. Move the intentional Income mismatch into a temporary demo workbook or fault-
   injection script so the committed default smoke suite stays green.
2. Add a bounded WDA readiness/recovery preflight that distinguishes startup
   transition from a persistent XCUITest configuration failure.
3. Ask the app team for stable semantic IDs on text fields, date groups, and
   bottom navigation.
4. Introduce faster state seeding only after preserving at least one clean-
   install onboarding smoke path per environment.
5. Publish signed Android/iOS artifacts through an authenticated build service
   so CI can report the same app-version identity as local matrices.
6. Expand environment profiles only when a real shared backend creates new
   configuration needs; keep credentials in secret stores, never profile YAML.
7. Replace the local Excel registry with a test-management API only when
   concurrent editing, permissions, and audit history justify the complexity.

The main lesson is that test-platform value comes from explicit boundaries and
attributable evidence. A small suite that identifies its environment, build,
device, data source, and failure phase provides more engineering signal than a
larger set of shallow UI scripts.
