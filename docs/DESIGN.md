# Architecture Design

## Goals

The framework automates Trackify's highest-value Android journeys while keeping
UI mechanics separate from business assertions. The design optimizes for:

- readable BDD scenarios;
- deterministic first-run state;
- reusable Android/iOS locator definitions;
- useful failure evidence;
- small, reviewable modules.

It does not try to automate the entire app, provide visual-diff testing, or hide
environment failures behind retries.

## Layers

```text
Gherkin feature
    -> pytest-bdd step definition
        -> Flow (business state and assertions)
            -> Page Object (UI interaction)
                -> Appium WebDriver
                    -> Trackify
```

The dependency direction is one-way:

- Steps translate scenario wording into Flow calls.
- Flows compose Pages and own transaction expectations.
- Pages resolve YAML locators and interact with Appium.
- `BasePage` owns shared waits, clicks, swipes, screenshots, and permission
  handling.
- Pages never import other Pages, and Flows never access the driver directly.

This keeps Gherkin stable when a locator changes and keeps UI mechanics out of
business assertions.

## Fixture Lifecycle

`conftest.py` owns the Appium session and dependency graph. One driver session
is shared for a pytest run. Before each scenario, the autouse fixture clears the
Trackify package data and reactivates the app. Each scenario then completes the
same required onboarding sequence using the validated profile selected by
`--env` or `TEST_ENV`:

1. enter the profile name (`Rose`, `Kimbal`, or `Kimi`);
2. select the profile currency and the scenario-owned budget `30000`;
3. apply the profile Bank SMS Reader state and tap Get Started.

The reset is deliberately expensive but deterministic. It prevents one
scenario's Hive data, custom categories, or onboarding state from affecting the
next scenario.

## Environment and Build Identity

`data/environments/{test,preprod,prod}.yaml` owns non-secret values shared by
the onboarding Background. Excel/Gherkin continues to own scenario business
inputs and expected results, so environment selection does not duplicate the
case registry. Resolution is strict and deterministic: `--env` overrides
`TEST_ENV`, which overrides the `preprod` default; invalid profiles fail before
driver creation.

After driver creation, `utils/app_metadata.py` resolves a non-empty tested app
version from an explicit `APP_VERSION`, Appium capabilities, Android installed
package metadata, or iOS bundle metadata. The resolved environment/build/device
context is attached to every Allure case and written to each worker's
`environment.properties`. Matrix aggregation reads each worker's version, so
different Android and iOS builds remain visible rather than being collapsed.

The current `prod` profile changes local app storage only. This is not blanket
authorization for destructive tests against a future shared production backend.

## Locator Design

Locators live in `locator/<page>.yaml`, grouped by platform. Python code asks
for a semantic key such as `amount_input` or `save_button`; the loader returns
the platform-specific strategy and value.

The preferred order is:

1. accessibility ID;
2. resource ID;
3. stable class or platform predicate;
4. scoped XPath when Flutter exposes no stronger semantic identifier.

The current build still requires XPath for some text inputs and merged Flutter
semantics nodes. These selectors are isolated in YAML so they can be replaced
without changing Page or Flow behavior.

## Synchronization

Pages use explicit waits rather than fixed sleeps. Two additional rules address
mobile-specific races found during implementation:

- text fields complete the IME action before the next control is selected;
- a successful transaction save waits until Home is visible before another
  shortcut can be used.

The second rule prevents an `Income` selector on the closing Add Transaction
screen from being mistaken for the Home shortcut with the same accessibility
label.

## Business Assertions

`AddTransactionFlow` captures the type, amount, category, and selected local
date/time before saving. The scenario then verifies the corresponding
Transactions row and Home monthly summary.

- Expense increases expense.
- Income increases income.
- Transfer changes neither summary total.
- Balance is `income - expense`.
- Budget percentage is `expense / budget * 100`, rounded half-up to an integer.
- Historical transactions are verified in their date section and do not alter
  the current-month summary.

`TransactionsFlow` separately verifies type filters and date-section grouping.

## Failure Evidence

The pytest report hook captures a PNG only for call-stage failures. It stores the
file under `report/screenshots/` and attaches the same image to the Allure test
result. Screenshot errors emit a warning and never replace the original test
failure. pytest-bdd hooks also expose the original Feature and Scenario names in
Allure.

## Advisory Failure Triage

Task 13 consumes failure evidence only after pytest creates the original report.
It classifies the first failed phase, prints one concise terminal hint, and
attaches the same structured result to Allure. The dependency is one-way:

```text
pytest failure -> screenshot/traceback -> local signatures -> optional LLM
               -> terminal + Allure advisory result
```

High-confidence local signatures handle deterministic environment, locator,
data, app, and script failures without network I/O. Only ambiguous evidence may
use the explicitly enabled MiniMax/Anthropic-compatible fallback. Reporting
errors degrade to `Unknown`; they cannot mutate the test outcome or original
evidence. This keeps failure intelligence useful without turning probabilistic
advice into an automated repair mechanism.

See [AI_TRIAGE.md](AI_TRIAGE.md) for runtime semantics, secure configuration,
verification, and troubleshooting.

## CI Boundary

The repository does not commit the Trackify APK. CI therefore has two explicit
levels:

- every push and pull request installs dependencies and collects all scenarios;
- Android E2E runs only when `TRACKIFY_APK_URL` provides a downloadable APK.

The E2E job starts an API 34 emulator and Appium, runs the same pytest command as
local development, and uploads raw Allure results, screenshots, and Appium logs.
When the APK secret is absent, CI reports the E2E job as intentionally skipped
instead of claiming mobile coverage.

## Cross-Platform Extension

Driver configuration and locator YAML already accept `android` and `ios`.
Extending the suite to iOS requires validated XCUITest locators and picker/back
navigation behavior, but does not require new Gherkin scenarios or Flow logic.

See [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) for implementation contracts and
[Feature_Inventory.md](Feature_Inventory.md) for scope selection.
