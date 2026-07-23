# Task 13: Advisory Failure Triage

## Purpose

Task 13 reduces the time between a failed regression case and the first useful
debugging action. After retries are exhausted, it classifies only the final
failed pytest phase as one of
`Locator`, `App Bug`, `Env`, `Script`, `Data`, or `Unknown`, then presents the
same advisory result in the terminal and Allure.

It is not a test generator or an automatic repair system. Mobile cases are
retried by `pytest-rerunfailures`, not by the triage engine: one initial attempt
plus at most two retries, with the last attempt determining PASS/FAIL. Unit
tests opt out. Triage never changes the pytest result, edits a locator,
suppresses a traceback, or files a defect. Passing cases do not invoke triage.

## Runtime Flow

```text
setup/call/teardown failure (attempt 1 or 2)
          |
          v
capture attempt-numbered screenshot + Appium page source
          |
          +-- retry remains --> keep retry history and run again
          |
          v
final failure (attempt 3)
          |
          v
capture original exception + bounded traceback + failed BDD step
          |
          v
deterministic local signatures
          |
          +-- confidence >= 0.70 --> local verdict
          |
          +-- confidence < 0.70
                    |
                    +-- LLM disabled/missing config --> disabled Unknown
                    |
                    +-- LLM enabled --> one bounded MiniMax/Anthropic request
                                              |
                                              +-- valid JSON --> llm verdict
                                              +-- error/invalid JSON --> safe Unknown
          |
          v
terminal line + Allure "AI Triage" JSON attachment
          |
          v
original pytest PASSED/FAILED status remains unchanged
```

The exact order is `failure -> retry history -> final failure -> local
signatures -> optional LLM`. Each failed BDD attempt keeps uniquely named PNG
and XML evidence. The final failing phase is stored in the pytest item stash,
so it cannot produce duplicate diagnoses. Only screenshot availability and its
basename may enter the LLM prompt; image bytes, page source, and absolute paths
are never uploaded. The one LLM request is never retried.

## What Users See

The terminal receives exactly one concise line:

```text
[AI Triage] Locator (92%): Matched local failure signature 'selector_specific_missing'.
```

The Allure case contains an `AI Triage` JSON attachment with:

| Field | Meaning |
|---|---|
| `test_name`, `phase` | Failed case and `setup`, `call`, or `teardown` phase |
| `attempt`, `max_attempts`, `failed_step` | Exhausted attempt context and failed BDD action |
| `category`, `confidence` | Advisory classification and bounded confidence |
| `reasoning`, `next_action` | Why it was classified and the next debugging step |
| `classifier` | `local`, `llm`, or `disabled` |
| `matched_signatures` | Deterministic signature IDs; empty for LLM/disabled |

| Classifier | Meaning | Expected action |
|---|---|---|
| `local` | A high-confidence deterministic signature matched; no API call occurred | Follow the reported action and inspect original evidence |
| `llm` | The local signal was ambiguous and a configured compatible API was attempted | Review model advice together with traceback/screenshot |
| `disabled` | The signal was ambiguous but the opt-in switch, key, or model was missing | Configure fallback or triage manually |

## Typical Regression Examples

| Failure evidence | Likely result | Value |
|---|---|---|
| Appium connection refused during setup | `Env / local` | Routes investigation to server/device setup |
| Missing element plus a named selector strategy | `Locator / local` | Points to the YAML locator and current page source |
| Generic missing destination after an action | optional LLM or `Unknown / disabled` | Avoids treating a downstream state symptom as a proven locator defect |
| Expected monthly summary differs from displayed value | `App Bug / local` when business context is present | Prompts requirement comparison and manual reproduction |
| `TypeError` in a Flow or Page | `Script / local` | Routes investigation to automation implementation |
| Bare `AssertionError` without context | `llm` when enabled, otherwise `disabled` | Uses the compatible model only for ambiguous evidence |

## Secure MiniMax Configuration

Copy the committed placeholder file and keep the real file local:

```bash
cp .env.example .env
chmod 600 .env
```

Configure `.env` without committing it:

```bash
AI_TRIAGE_LLM_ENABLED=1
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
ANTHROPIC_API_KEY=<local-secret>
ANTHROPIC_MODEL=MiniMax-M3
SSL_CERT_FILE=/etc/ssl/cert.pem
```

`SSL_CERT_FILE` is needed only when the local Python installation reports a TLS
certificate verification failure and that CA bundle exists. Certificate
verification must never be disabled.

The project does not auto-load `.env`. Load it in every new terminal:

```bash
set -a
source .env
set +a
```

Check configuration without printing the key:

```bash
.venv/bin/python - <<'PY'
import os

print({
    "enabled": os.getenv("AI_TRIAGE_LLM_ENABLED"),
    "base_url": os.getenv("ANTHROPIC_BASE_URL"),
    "api_key_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
    "model": os.getenv("ANTHROPIC_MODEL"),
    "ssl_cert_file": os.getenv("SSL_CERT_FILE"),
})
PY
```

## Verification

Disable retries for a focused diagnostic run with `--reruns 0`:

```bash
.venv/bin/pytest -m "not unit" -k "add_expense_happy_path" --reruns 0 -s -vv
```

Run the complete device-free Task 13 regression:

```bash
.venv/bin/pytest -m unit tests/unit/test_triage.py -q
```

Verify the local, zero-network path:

```bash
.venv/bin/python - <<'PY'
from dataclasses import asdict
from pprint import pprint
from ai.triage import triage_failure

pprint(asdict(triage_failure({
    "error_msg": "NoSuchElementException: Unable to locate element",
    "traceback": "",
    "test_name": "local_probe",
    "phase": "call",
})))
PY
```

Expected evidence includes `category=Locator`, `classifier=local`, confidence
`0.98`, and signature `element_missing`.

Verify the live compatible fallback with an intentionally ambiguous input:

```bash
.venv/bin/python - <<'PY'
from dataclasses import asdict
from pprint import pprint
from ai.triage import triage_failure

pprint(asdict(triage_failure({
    "error_msg": "AssertionError",
    "traceback": "",
    "test_name": "live_probe",
    "phase": "call",
})))
PY
```

`classifier=llm` proves that the network fallback was attempted. A valid model
verdict includes bounded reasoning/action. A strict-format failure still returns
`llm / Unknown / 0.0` and never changes a test outcome.

For an actual mobile regression, load `.env`, execute pytest or the device
matrix normally, then open the failed Allure case through `allure open` and
inspect the `AI Triage` attachment alongside the original traceback and
screenshot.

## Troubleshooting

| Result | Cause | Action |
|---|---|---|
| `classifier=disabled` | Switch is not `1`, `.env` was not sourced, or key/model is missing | Load `.env` and rerun the safe configuration check |
| `HTTP 401` | Invalid/unloaded API key | Recreate the local key and source `.env`; never print it |
| `HTTP 429` | Quota or rate limit | Check provider quota; do not add automatic retry to test reporting |
| TLS verification failure | Python CA bundle is missing | Set a valid `SSL_CERT_FILE`; never disable verification |
| Connection/timeout | Endpoint, DNS, proxy, or network issue | Verify Base URL and network path |
| Invalid response | Model output did not satisfy the strict JSON contract | Keep `Unknown`, inspect original failure, and measure frequency before changing policy |

## Privacy and Reliability Boundaries

- Error messages are capped at 2,000 characters and tracebacks at 12,000.
- Authorization headers, keys, tokens, and URL queries are redacted.
- Exception text is treated as untrusted prompt data.
- One LLM request is allowed, with no retry and a five-second timeout.
- Unknown/transport/model failures never replace the original pytest failure.
- Model advice is a debugging hypothesis, not a confirmed root cause.
