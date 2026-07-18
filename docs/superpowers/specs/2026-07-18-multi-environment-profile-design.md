# Multi-Environment Profile Design

## Objective

Support `test`, `preprod`, and `prod` as explicit execution environments. The
selected environment supplies Trackify's shared onboarding profile, while
business-defining test values such as transaction amounts and monthly budget
remain visible in Excel and Gherkin. Every Allure result must identify the
environment and the tested app version.

## Scope

This change covers:

- three validated, non-secret YAML environment profiles;
- consistent `--env test|preprod|prod` selection for direct pytest, device
  matrix, and changed-case matrix execution;
- environment-driven onboarding on Android and iOS;
- app-version discovery and reporting in per-test Allure metadata,
  `environment.properties`, combined reports, and matrix summaries;
- workbook, Feature, README, and architecture documentation updates;
- focused unit tests plus existing collection and sync-regression checks.

This change does not add per-scenario data profiles, generic `${...}` template
substitution, Excel-to-YAML synchronization, secrets in YAML, backend data
factories, or environment-specific Feature files.

## Ownership Boundary

| Concern | Owner | Examples |
|---|---|---|
| Scenario and business parameters | Excel managed blocks / Gherkin | amount `100`, budget `30000`, expected validation text |
| Shared onboarding profile | Environment YAML | name, currency, Bank SMS Reader setting |
| Device and app artifact selection | CLI/environment configuration | UDID, Appium URL, APK, `.app`, `.ipa` |
| Secrets | CI secret or process environment | future credentials or tokens |
| Runtime-generated backend entities | Future data factory | out of scope |

Excel remains authoritative for managed Scenario blocks. YAML is authoritative
only for environment profile values. The Sync Engine remains one-way
`Excel -> Feature` and never writes YAML.

## Environment Files

Create the following files:

```text
data/environments/
  test.yaml
  preprod.yaml
  prod.yaml
```

Each file has the same strict schema:

```yaml
schema_version: 1
name: Rose
currency: "$ US Dollar"
bank_sms_reader_enabled: true
```

Resolved values are:

| Environment | Name | Currency | Bank SMS Reader |
|---|---|---|---|
| `test` | `Rose` | `$ US Dollar` | enabled |
| `preprod` | `Kimbal` | `$ US Dollar` | enabled |
| `prod` | `Kimi` | `$ US Dollar` | enabled |

`utils/environment_profile.py` loads one exact file into a frozen dataclass.
Unknown environments, missing files, unknown keys, invalid schema versions,
blank strings, and non-boolean SMS settings fail before an Appium session is
created. There is no silent fallback between environments.

## Environment Selection

The supported values are exactly `test`, `preprod`, and `prod`.

Resolution precedence for direct pytest is:

```text
pytest --env
  > TEST_ENV
  > preprod
```

Supported entry points include:

```bash
.venv/bin/python -m pytest --env test
.venv/bin/python scripts/run_device_matrix.py --env preprod
./scripts/run_changed_matrix.sh --env prod
```

`run_device_matrix.py` and `run_changed_matrix.sh` reject unsupported values in
preflight. Matrix workers receive the validated selection through `TEST_ENV`.
The pytest option and environment variable must resolve to the same value; the
resolved value is the only source used by onboarding and reporting.

## BDD and Flow Changes

The code-owned Background in both Feature files becomes environment-aware while
keeping the business budget explicit:

```gherkin
Background:
  Given app is launched with a clean database
  And user enters the configured environment name and continues
  And user selects the configured environment currency and sets monthly budget "30000"
  And user applies the configured Bank SMS Reader setting and gets started
  And user is on the Home page
```

Step definitions consume the session-scoped `environment_profile` fixture and
pass resolved values into `AppSetupFlow`. The Flow retains the ordered setup
contract and verifies the configured name, currency symbol, and desired SMS
Reader state. Page Objects remain unaware of environment names and YAML.

All seven workbook Preconditions are updated to describe environment-profile
onboarding instead of hard-coding `Kimbal`. No new workbook column is added.
Managed Scenario steps and expected results remain unchanged.

## App Version Resolution

App version resolution uses the following precedence:

1. explicit `APP_VERSION` process value;
2. Appium capability values when supplied by the driver;
3. Android installed-package metadata (`versionName`) for the selected UDID;
4. iOS `CFBundleShortVersionString` from the selected `.app` or `.ipa`;
5. a configuration error with an actionable instruction to set `APP_VERSION`.

`utils/app_metadata.py` owns platform-specific resolution. It returns a
non-empty version or raises a bounded error; normal completed runs must not
silently report `unknown`.

Version discovery runs after driver creation for direct pytest. Matrix workers
write the resolved version into their Allure results, and the matrix aggregator
reads those properties rather than guessing one shared version for potentially
different Android and iOS artifacts.

## Reporting

Each test receives these Allure parameters:

- Environment
- App Version
- Platform
- Device
- OS Version
- UDID

Each worker's `environment.properties` includes:

```properties
Test.Environment=test
App.Version=1.2.3
Device.Platform=Android
Device.Name=...
Device.UDID=...
Device.OS.Version=...
```

The combined Allure properties and `summary.md` preserve app version per
device. If Android and iOS artifacts have different versions, both values are
shown; the aggregator does not collapse them to one misleading version.

Setup failures that occur before app-version discovery still retain the
environment/device identity. A version-discovery failure is itself a setup
configuration failure with Task 13 evidence; it does not produce a successful
report with missing version metadata.

## Production Safety Boundary

The current Trackify suite clears and modifies local app storage only. Therefore
`--env prod` is allowed with the supplied local onboarding profile. If Trackify
later connects these scenarios to a shared production backend, destructive prod
execution must be reconsidered before adding credentials or backend data; this
design does not authorize destructive production data mutation.

## Error Handling

- CLI rejects unsupported environment values before discovery or sync.
- Profile validation reports the environment, file, and invalid field without
  exposing secret values.
- YAML parsing errors stop the run before Appium setup.
- App-version discovery errors explain the attempted platform source and the
  `APP_VERSION` override.
- Reporting failures never replace the original pytest failure, matching the
  existing screenshot and AI Triage behavior.

## Verification

Add unit coverage for:

- all three environment files and their exact resolved values;
- CLI-over-environment-over-default precedence;
- unknown environment and invalid YAML/schema/field failures;
- direct pytest option registration and collection isolation;
- Android, iOS `.app`, iOS `.ipa`, capability, and override version resolution;
- Allure properties containing environment and app version;
- matrix parser validation, worker propagation, aggregation, and summary output;
- changed-matrix environment validation;
- environment-driven onboarding Flow behavior.

Regression verification must also prove:

- all existing unit tests pass;
- all seven BDD scenarios collect;
- Excel and managed Feature blocks have zero drift;
- the workbook remains readable and visually unchanged apart from Preconditions;
- `--env test`, `--env preprod`, and `--env prod` resolve the expected profile;
- a controlled Allure result exposes both environment and app version.

Real-device execution is proportional to locally available artifacts and
devices. Unit tests cover platform metadata fallbacks independently of Appium.
