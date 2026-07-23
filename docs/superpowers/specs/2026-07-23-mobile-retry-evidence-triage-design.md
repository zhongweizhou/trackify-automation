# Mobile Retry, Failure Evidence, and Final Triage Design

## Scope

This change covers all non-unit mobile tests, whether they are started by direct
pytest, `scripts/run_device_matrix.py`, or `scripts/run_changed_matrix.sh`.
Tests marked `unit` never retry.

The implementation also fixes the unreliable horizontally scrolled category
selection exposed by `TC_ADD_TX_006`, and fixes missing failure screenshots for
pytest-bdd scenarios.

## Retry Contract

- A mobile test runs once and may be retried up to two times after failure.
- The default maximum is therefore three attempts.
- The final attempt alone determines the test's final pass/fail status.
- A later pass makes the test pass while preserving earlier failed attempts as
  retry history in Allure.
- `--reruns 0` disables retries for a diagnostic run.
- Retry behavior is provided by `pytest-rerunfailures`; the project does not
  implement its own fixture or scenario retry engine.
- The project marks unit tests with a zero-rerun override so global retry
  defaults never apply to them.

## Reporting Contract

- Allure preserves each failed attempt as retry history and presents the last
  attempt as the current result.
- JUnit and matrix summaries expose one final result per pytest node ID.
- If an upstream JUnit producer emits duplicate attempts, matrix parsing
  collapses them by test identity and keeps the last result before calculating
  pass/fail totals.
- Each failed BDD attempt captures a PNG screenshot and Appium page source.
- Artifact names contain the attempt number so retries cannot overwrite one
  another.
- Evidence is attached during the pytest-bdd step-error lifecycle while the
  dynamically requested Appium driver is still available.
- Setup/teardown failures use the best available session driver; lack of a
  driver remains a warning and never hides the original failure.

## Final-Failure Triage

- Intermediate pytest reports whose outcome is `rerun` never call AI triage.
- A test that passes on retry never calls AI triage.
- A test that remains failed after the third attempt produces exactly one AI
  Triage attachment and one terminal summary line.
- Triage receives the final exception, traceback, node ID, pytest phase,
  attempt count, failed BDD step when available, and final screenshot basename.
- Deterministic local signatures always run first.
- Generic missing-element signals are treated as symptoms rather than automatic
  98% locator verdicts. Strong selector-specific evidence may remain a local
  Locator result; ambiguous post-action page-state failures fall through to the
  optional LLM when configured.
- The LLM remains opt-in, gets one request with no request retry, and cannot
  change the pytest outcome.

## Category Selection Reliability

The category scroller must not treat a small clipped fragment as safely
clickable. Before tapping a category, the Page Object:

1. Locates or scrolls toward the target category.
2. Re-reads its bounds after every scroll.
3. Requires its center to be inside a horizontal safe inset of the category
   viewport.
4. Corrects left- or right-edge clipping with a directional swipe.
5. Taps only after the target is in the safe region.
6. Raises a focused timeout if it cannot produce a safe target after the bounded
   number of attempts.

This stays in the Page layer because it is UI interaction mechanics; Flow and
BDD steps retain their current business responsibilities.

## Implementation Boundaries

- `pyproject.toml` and `pytest.ini`: retry dependency and defaults.
- `conftest.py`: unit opt-out, attempt metadata, BDD evidence capture, and
  final-attempt-only triage orchestration.
- `page/add_transaction_page.py`: safe horizontal category positioning.
- `ai/triage.py`: stronger local-rule specificity and bounded retry metadata.
- `scripts/run_device_matrix.py`: defensive last-attempt JUnit aggregation and
  summary semantics.
- Existing README and AI-triage documentation: retry commands, final-result
  semantics, and evidence behavior in supported languages.

No application code, Excel-to-Feature lifecycle rule, device discovery rule,
or LLM transport retry is changed.

## Verification

Automated coverage must prove:

- partially visible left/right category targets are repositioned before click;
- `TC_ADD_TX_006` passes on the Android emulator;
- a fail-then-pass controlled mobile test reports final PASS and no AI triage;
- a fail-three-times controlled mobile test reports one final FAIL and exactly
  one AI triage call;
- each failed attempt has uniquely named screenshot and page-source evidence;
- pytest-bdd dynamic fixtures provide a live driver to the evidence hook;
- matrix JUnit parsing keeps the last duplicate attempt result;
- unit tests execute once even when global mobile retry defaults are enabled;
- existing local-first, optional-LLM triage tests continue to pass.
