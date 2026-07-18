# Multi-Environment Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the same Trackify BDD suite against `test`, `preprod`, or `prod` onboarding profiles and identify both the environment and tested app version in Allure and matrix reports.

**Architecture:** Excel and Gherkin continue to own business parameters. Strict YAML files own only shared onboarding values, a pytest fixture resolves the selected profile before Appium setup, and a focused metadata module resolves app versions per device/artifact. Existing pytest and matrix report paths consume one resolved execution context.

**Tech Stack:** Python 3.11+, pytest, pytest-bdd, PyYAML, Appium Python Client, Allure, openpyxl/artifact-tool for workbook verification, Bash.

---

### Task 1: Strict Environment Profiles

**Files:**
- Create: `data/environments/test.yaml`
- Create: `data/environments/preprod.yaml`
- Create: `data/environments/prod.yaml`
- Create: `utils/environment_profile.py`
- Create: `tests/unit/test_environment_profile.py`

- [ ] **Step 1: Write failing loader tests**

Cover the exact three profiles, `--env > TEST_ENV > preprod` resolution through a pure helper, unknown environments, unknown YAML keys, invalid schema versions, blank values, and non-boolean SMS settings.

```python
def test_committed_profiles_resolve_exact_values():
    assert load_environment_profile("test").name == "Rose"
    assert load_environment_profile("preprod").name == "Kimbal"
    assert load_environment_profile("prod").name == "Kimi"

def test_resolve_environment_prefers_cli(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "test")
    assert resolve_environment("prod") == "prod"
```

- [ ] **Step 2: Run tests and confirm the module is missing**

Run: `.venv/bin/python -m pytest tests/unit/test_environment_profile.py -q`

Expected: collection error for `utils.environment_profile`.

- [ ] **Step 3: Implement the frozen model and strict loader**

```python
SUPPORTED_ENVIRONMENTS = ("test", "preprod", "prod")

@dataclass(frozen=True)
class EnvironmentProfile:
    environment: str
    name: str
    currency: str
    bank_sms_reader_enabled: bool

def resolve_environment(cli_value: str | None, environ=os.environ) -> str:
    value = cli_value or environ.get("TEST_ENV") or "preprod"
    if value not in SUPPORTED_ENVIRONMENTS:
        raise EnvironmentProfileError(
            f"Unsupported environment {value!r}; expected test, preprod, or prod"
        )
    return value
```

Use `yaml.safe_load`, require exactly `schema_version`, `name`, `currency`, and `bank_sms_reader_enabled`, and reject invalid values before returning the dataclass.

- [ ] **Step 4: Run the focused tests**

Run: `.venv/bin/python -m pytest tests/unit/test_environment_profile.py -q`

Expected: all profile tests pass.

- [ ] **Step 5: Commit**

```bash
git add data/environments utils/environment_profile.py tests/unit/test_environment_profile.py
git commit -m "feat(config): add validated environment profiles"
```

### Task 2: Pytest Selection and Environment-Driven Onboarding

**Files:**
- Modify: `conftest.py`
- Modify: `tests/features/add_transaction.feature`
- Modify: `tests/features/transactions.feature`
- Modify: `tests/step_defs/common_steps.py`
- Modify: `flow/app_setup_flow.py`
- Modify: `page/onboarding_page.py` only if setting `false` requires a state transition helper
- Create: `tests/unit/test_environment_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Test pytest option registration, fixture resolution without Appium, and Flow calls for a supplied profile.

```python
def test_setup_flow_uses_environment_profile(flow, profile):
    flow.complete_onboarding(profile, "30000")
    onboarding.enter_name_and_continue.assert_called_once_with(profile.name)
    onboarding.select_currency.assert_called_once_with(profile.currency)
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/unit/test_environment_runtime.py -q`

Expected: missing option/fixture/Flow API failures.

- [ ] **Step 3: Add pytest option and session fixture**

```python
def pytest_addoption(parser):
    parser.addoption("--env", choices=SUPPORTED_ENVIRONMENTS, default=None)

@pytest.fixture(scope="session")
def environment_profile(pytestconfig):
    environment = resolve_environment(pytestconfig.getoption("--env"))
    return load_environment_profile(environment)
```

Ensure the driver fixture requests `environment_profile`, so invalid config fails before `AppiumDriverFactory.create()`.

- [ ] **Step 4: Refactor onboarding vocabulary and Flow**

Replace hard-coded Background values with configured-environment steps while keeping budget `30000` explicit. Add `AppSetupFlow.complete_onboarding(profile, budget)` to perform and verify all three stages. Remove unused literal-profile Given steps after all Feature references move.

- [ ] **Step 5: Run runtime tests and collection**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_environment_runtime.py -q
.venv/bin/python -m pytest --collect-only -q --env test
.venv/bin/python -m pytest --collect-only -q --env preprod
.venv/bin/python -m pytest --collect-only -q --env prod
```

Expected: focused tests pass and each command collects the same 7 BDD scenarios plus unit tests without Appium.

- [ ] **Step 6: Commit**

```bash
git add conftest.py flow page tests/features tests/step_defs tests/unit/test_environment_runtime.py
git commit -m "feat(test): drive onboarding from selected environment"
```

### Task 3: Cross-Platform App Version Resolution

**Files:**
- Create: `utils/app_metadata.py`
- Create: `tests/unit/test_app_metadata.py`

- [ ] **Step 1: Write failing metadata tests**

Cover `APP_VERSION`, capability keys, Android `dumpsys` parsing, iOS `.app` plist, iOS `.ipa` plist, and the actionable failure.

```python
def test_override_has_highest_priority(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "9.8.7")
    assert resolve_app_version(driver, config) == "9.8.7"

def test_parse_android_version_name():
    assert parse_android_version("versionName=1.2.3\n") == "1.2.3"
```

- [ ] **Step 2: Run tests and confirm the module is missing**

Run: `.venv/bin/python -m pytest tests/unit/test_app_metadata.py -q`

Expected: collection error for `utils.app_metadata`.

- [ ] **Step 3: Implement bounded resolvers**

Use standard-library `plistlib` and `zipfile` for iOS. Use the existing `_adb` resolution pattern or an injected Android command runner. Never log environment contents. Return a non-empty normalized string or raise `AppVersionError` instructing the caller to set `APP_VERSION`.

- [ ] **Step 4: Run focused metadata tests**

Run: `.venv/bin/python -m pytest tests/unit/test_app_metadata.py -q`

Expected: all metadata tests pass without devices.

- [ ] **Step 5: Commit**

```bash
git add utils/app_metadata.py tests/unit/test_app_metadata.py
git commit -m "feat(report): resolve Android and iOS app versions"
```

### Task 4: Allure and Device Matrix Reporting

**Files:**
- Modify: `conftest.py`
- Modify: `scripts/run_device_matrix.py`
- Modify: `scripts/run_changed_matrix.sh`
- Modify: `unit_tests/test_run_device_matrix.py`
- Create or modify: `tests/unit/test_reporting_context.py`

- [ ] **Step 1: Write failing reporting tests**

Assert `App.Version` in `environment.properties`, per-test Allure parameters, `DeviceResult.app_version`, combined properties, per-device summary rows, supported `--env` choices, and Worker `TEST_ENV` propagation.

```python
def test_environment_properties_include_app_version(tmp_path):
    write_environment_properties(tmp_path, context)
    assert "Test.Environment=test" in text
    assert "App.Version=1.2.3" in text
```

- [ ] **Step 2: Run tests and confirm missing fields**

Run: `.venv/bin/python -m pytest tests/unit/test_reporting_context.py unit_tests/test_run_device_matrix.py -q`

Expected: failures for missing version/context fields and unrestricted environment parser.

- [ ] **Step 3: Integrate one execution context**

Resolve the selected profile before Driver creation, resolve app version after Driver creation, and attach the full context before the test call. Write the same fields to Worker properties. Extend `DeviceResult` and aggregation so differing Android/iOS versions remain visible.

- [ ] **Step 4: Validate all command entry points**

Set parser choices for `run_device_matrix.py`. Add Bash preflight validation for exactly `test|preprod|prod`. Preserve exit code `2` for configuration errors.

- [ ] **Step 5: Run focused reporting tests**

Run: `.venv/bin/python -m pytest tests/unit/test_reporting_context.py unit_tests/test_run_device_matrix.py -q`

Expected: all reporting and matrix unit tests pass.

- [ ] **Step 6: Commit**

```bash
git add conftest.py scripts/run_device_matrix.py scripts/run_changed_matrix.sh tests/unit/test_reporting_context.py unit_tests/test_run_device_matrix.py
git commit -m "feat(report): include environment and app version"
```

### Task 5: Workbook and User Documentation

**Files:**
- Modify: `data/test_cases.xlsx`
- Modify: `data/test_cases_template.xlsx`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `docs/DESIGN.md`
- Modify: `docs/TECHNICAL_SPEC.md`
- Modify: `docs/AI_TRIAGE.md` only if context examples mention fixed environment data

- [ ] **Step 1: Update only workbook Preconditions**

Replace hard-coded `Kimbal` onboarding text in all seven rows with wording that names the selected environment profile while retaining US Dollar and budget `30000` as business expectations. Apply the same baseline to the template. Do not change managed Test Steps or Expected Result cells.

- [ ] **Step 2: Verify workbook values and visual layout**

Use `@oai/artifact-tool` to inspect `Test Cases!A1:P8`, render both sheets, and confirm headers, wrapping, row heights, and formulas remain valid. Run the sync engine check and expect zero drift.

- [ ] **Step 3: Document commands and ownership**

Add all three environment examples, YAML schema/paths, precedence, app-version override/fallback, report fields, and the production-local-storage boundary to English and Simplified Chinese README plus architecture/spec documents.

- [ ] **Step 4: Run documentation checks**

Run:

```bash
git diff --check
.venv/bin/python scripts/sync_engine.py --check
```

Expected: no whitespace errors and `[sync] No changes`/exit 0.

- [ ] **Step 5: Commit**

```bash
git add data/test_cases.xlsx data/test_cases_template.xlsx README.md README.zh-CN.md docs
git commit -m "docs: document multi-environment execution"
```

### Task 6: Full Verification

**Files:**
- Verify only; fix failures in the owning files above.

- [ ] **Step 1: Run all isolated tests**

Run: `.venv/bin/python -m pytest tests/unit unit_tests -q`

Expected: all tests pass.

- [ ] **Step 2: Verify collection in every environment**

Run each environment with `--collect-only -q` and confirm identical BDD node IDs.

- [ ] **Step 3: Verify sync and command rejection**

Run sync check, matrix `--list` where devices are available, and invalid environment commands. Invalid values must exit 2 before Appium/device work.

- [ ] **Step 4: Run available real-device smoke coverage**

Use the currently running Android/iOS targets with the available artifacts. For each executable environment, verify onboarding name and report metadata. If a distinct environment build is not supplied, use the same local artifact and explicitly report that only profile selection, not backend routing, differs.

- [ ] **Step 5: Inspect generated Allure evidence**

Confirm a result contains Environment and App Version, and `environment.properties` plus matrix `summary.md` agree per device.

- [ ] **Step 6: Final status and commit audit**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: clean worktree and the implementation commits listed above.
