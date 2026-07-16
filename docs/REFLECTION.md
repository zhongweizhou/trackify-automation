# Project Reflection

## Outcome

The delivered suite covers seven Android BDD scenarios across the two selected
journeys:

| Journey | Scenarios | Result |
|---------|-----------|--------|
| Add Transaction | Expense, Income, Transfer, empty amount, custom category | 5 passing |
| Transactions | Type filter, historical date grouping | 2 passing |

Every business scenario completes first-run setup, and successful Add
Transaction scenarios verify both the saved Transactions row and the Home
monthly summary. The latest local Allure run completed with 7 passed, 0 failed,
and 0 skipped.

## What Worked Well

### Clear ownership between layers

Separating Gherkin, Steps, Flows, Pages, and locator YAML kept failures local.
For example, changing a keyboard interaction affected one Page method rather
than every scenario. Transaction summary calculations remained testable as
Flow behavior rather than becoming UI selector logic.

### Deterministic setup

Clearing package data before every scenario costs time, but it made onboarding,
custom category creation, and summary baselines repeatable. Explicitly entering
the user name, currency, budget, and SMS preference also tests the real first-run
path instead of bypassing it with Skip.

### Assertions beyond a save confirmation

The successful scenarios do not stop when the Add Transaction form closes.
They verify date, amount, category, and time in Transactions, then check income,
expense, balance, and budget percentage on Home. This caught integration issues
that a toast or Recent Transactions assertion alone would miss.

### Failure evidence

Allure uses the original BDD Feature and Scenario names. A call-stage failure
saves a local PNG and attaches it to the result without wrapping test bodies or
hiding the original traceback.

## What Was Harder Than Expected

### Flutter accessibility semantics

Some controls expose strong accessibility IDs, while others are merged into
large semantics nodes or expose only positional text fields. The suite contains
scoped XPath fallbacks as a result. They are isolated in YAML, but remain more
sensitive to app layout changes than stable semantic IDs.

### Keyboard state

The Android keyboard blocked both the onboarding budget slider and Add
Transaction controls. Sending the IME Done action after amount, note, tags, and
category-name input proved more reliable than tapping arbitrary coordinates.

### Horizontal categories

The `New` category entry sits at the far right of a horizontal list. Creating
`baby cost` required a controlled swipe, category creation, Back navigation,
and selection of a chip that may display only `baby` because of its fixed width.

### Transition races

When two transactions were added in one scenario, the second Home shortcut
could match a same-named tab on the form that was still closing. Waiting for
Home after a successful save removed the race and made sequential transactions
reliable.

## Current Limitations

- Each device worker is serial; matrix mode adds device-level concurrency but
  does not parallelize multiple Appium sessions on the same target.
- Full package reset makes each scenario slower than a targeted state fixture.
- iOS locators and all seven scenarios are validated on an iPhone 17 simulator
  running iOS 26.5; other device profiles and locale settings remain unverified.
- Photo attachment and broader Settings/Analytics behavior are outside the
  seven-scenario scope.
- GitHub-hosted E2E requires an externally downloadable APK through the
  `TRACKIFY_APK_URL` secret; without it, CI performs unit tests and collection.
- `summary.xlsx` generation was intentionally deferred from Task 11.

## AI Assistance

AI helped inspect the repository, translate the specification into BDD and Page
objects, reason about Flutter/Appium locator behavior, and shorten debugging
cycles. Each suggested interaction was checked against the live emulator. The
most useful feedback came from actual failures: category navigation, keyboard
state, date/time persistence, and post-save races all required evidence from the
running app rather than accepting generated code at face value.

## Next Improvements

1. Calibrate Task 13 signature precision against a larger set of real failures
   while keeping every verdict advisory and the LLM fallback opt-in.
2. Ask the app team for stable semantic IDs on text fields, date groups, and
   bottom navigation.
3. Validate the iOS locator set on a simulator and isolate native picker
   differences inside the Page layer.
4. Introduce a faster state-seeding strategy only after preserving one clean
   first-install smoke path.
5. Publish the APK through an authenticated build artifact service so mobile
   E2E can run on every trusted branch build.

The main lesson is that a small suite becomes valuable when its assertions
follow data across screens. Seven scenarios with deterministic state and strong
downstream checks provided more signal than a larger set of shallow UI scripts.
