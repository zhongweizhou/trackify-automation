# Scaling Trackify Automation — Implemented Foundation and Roadmap

> **Status**: Task 14's local Excel-to-Gherkin foundation is implemented. Version-aware
> selection, a shared test-management service, and bidirectional result sync remain roadmap.
> **Pair**: TECHNICAL_SPEC.md §11 is the normative implementation contract; this file
> explains the broader scaling context.

---

## Q1 — What can be verified about mature test organizations

Exact internal test platforms and operating rules at individual companies are generally
not public enough to support a reliable company-by-company comparison. The defensible
comparison is between published product capabilities and open specifications:

| Public source | Verifiable capability | Design implication |
|---------------|-----------------------|--------------------|
| [Azure Test Plans: associate automated tests](https://learn.microsoft.com/en-us/azure/devops/test/associate-automated-test-with-test-case?view=azure-devops) | Links automated tests to managed test cases for traceability and pipeline execution | Keep a stable case ID between registry metadata and executable code |
| [Azure Pipelines: Test Impact Analysis](https://learn.microsoft.com/en-us/azure/devops/pipelines/test/test-impact-analysis?view=azure-devops) | Selects the subset of tests required for a code change | Run impacted cases plus a small safety suite instead of every case on every commit |
| [Cucumber Gherkin reference](https://cucumber.io/docs/gherkin/reference) | Defines structured, executable specifications in a business-readable language | Keep Gherkin readable and treat the step vocabulary as an executable contract |

### Common mature-system pattern

1. A test-management system owns planning metadata, history, permissions, and audit.
2. Executable automation stays versioned with code and is changed through review.
3. Stable case IDs provide traceability across those two systems.
4. CI runs smoke coverage plus a risk- or change-selected subset, then broader scheduled regression.
5. Results flow back to a dashboard or test-management API with environment and device identity.
6. Locator and implementation changes remain engineer-reviewed because blind self-healing can hide product defects.

### Trackify mapping

Task 14 implements the same boundaries at local-project scale: Excel holds planning
metadata, stable IDs bind rows to code-owned scenarios, CI rejects drift, and
`--run-changed` executes the changed subset. Excel is a practical bootstrap and
authoring format, not the recommended concurrent database for many teams. When
permissions, audit history, webhooks, and concurrent editing become requirements,
replace it with a test-management API while retaining the IDs and one-way adapter.

---

## Q2 — App version × platform × selective regression

The "test selection" problem: how to pick the right scenarios to run given a new APK / IPA build.

### 2.1 Scenario metadata extension

Each scenario carries four extra comment fields (parsed by sync_engine, see §11.2):

```gherkin
# scenario_id: TC_ADD_TX_001
# introduced_in: 1.0.0
# deprecated_in: null        # still active
# platforms: android, ios
# min_android_sdk: 26
Scenario: ...
```

### 2.2 Selection strategies (pick one or combine)

#### Strategy A: app_version manifest (simplest)

```yaml
# config/app_versions.yaml
android:
  current: 1.4.2
  min_supported: 1.2.0
ios:
  current: 1.4.0
```

Select scenarios where `introduced_in ≤ current < deprecated_in`.

#### Strategy B: code-change-driven (intermediate)

```
git diff main..HEAD --name-only
  ↓
map changed_files → touched_modules
  ↓
select scenarios tagged @module:payments OR @module:settings
  ↓
run selected + smoke
```

Tools: Gradle `testFilter`, Bazel `affected_tests`, pytest-test-impact (OSS).

#### Strategy C: coverage-driven (advanced)

Track code-line coverage per scenario (Jacoco for Android). On new build, only run scenarios that cover lines both (a) not previously covered and (b) touched in this commit. Google Test Impact Analysis uses this approach.

### 2.3 Recommended 4-tier CI pipeline

| Layer | Trigger | Scope | Runtime | Devices |
|-------|---------|-------|---------|---------|
| **L1 PR check** | push to feature branch | `@smoke` + touched `@p0` | 3-10 min | 1 emulator |
| **L2 main merge** | PR merged | `@smoke` + `@p0` + touched `@p1` | 15-30 min | 2-3 devices (Android + iOS) |
| **L3 nightly** | cron 02:00 | all scenarios | 2-4 h | device farm (10+ devices) |
| **L4 release regression** | release tag cut | full + cross-platform matrix | 4-8 h | 20+ real devices |

### Trackify mapping

4-6h challenge can't deliver full L1-L4. But TECHNICAL_SPEC.md §11.2 reserves the metadata fields so Day 5+ can add the selection engine without rewriting `.feature` files.

---

## Q3 — Docs → auto-update BDD

### Industry tooling comparison

| Tool | Direction | Capability | Fit |
|------|-----------|------------|-----|
| **Hiptest → Cucumber** | manual → BDD | bidirectional sync, template-driven | mid-size teams |
| **TestRail + custom script** | manual → automation link | ID binding, status sync | **recommended for Trackify** |
| **Zephyr Scale + Automation** | Jira-native | direct `.feature` generation | mid-size |
| **Allure TestOps** | bidirectional | AI gap analysis | enterprise |
| **SpecSync (Azure DevOps)** | Test Plan ↔ `.feature` | strict bidirectional | enterprise |
| **LLM-assisted** | PRD → `.feature` draft | draft + human review | **best for 4-6h challenge** |

### "Don't break existing" — three core principles

#### Principle 1: ID anchoring

`scenario_id` is the stable anchor — Scenario title, tags, and steps can all change; the ID stays.

```gherkin
@smoke @p0
# scenario_id: TC_ADD_TX_001     # ← the only stable thing
# last_synced_from: TEST_RAIL#TC_4521 @ 2026-07-10T10:00:00Z
Scenario: Add expense happy path
  ...
```

#### Principle 2: line-level diff, not file-level diff

The sync_engine (Q6) walks scenarios one-by-one, computes per-scenario hash, and replaces only changed scenario blocks. Unchanged scenarios are not re-serialized — byte-identical before and after.

```python
def diff(excel_rows, feature_scenarios):
    by_id = {s.scenario_id: s for s in feature_scenarios}
    added = [r for r in excel_rows if r.scenario_id not in by_id]
    modified = [(by_id[r.scenario_id], r) for r in excel_rows
                if r.scenario_id in by_id and hash(r.gherkin_text) != hash(by_id[r.scenario_id].gherkin_text)]
    untouched = [s for sid, s in by_id.items() if sid not in {r.scenario_id for r in excel_rows}]
    deleted = [s for sid, s in by_id.items() if sid not in {r.scenario_id for r in excel_rows}]
```

#### Principle 3: atomic commit + validation

1. Generate patch (untouched scenarios untouched)
2. `git diff --stat` (human eyeballs the scope)
3. `pytest --collect-only` (must exit 0)
4. `pytest -m smoke` (must pass)
5. `git add tests/features/`
6. `git commit -m "sync: ... | +N ~M -K scenarios"`
7. **Do NOT push** — leave on a `sync/<date>` branch for PR review

### Trackify mapping

Excel is the **single source of truth** for the managed fields in
`data/test_cases.xlsx`. The implemented sync engine validates the complete workbook,
shows a scenario-level diff, and updates only changed managed blocks.

---

## Q4 — Screenshots / videos → generate BDD

### Industry reality (2026)

| Capability | Academia | Industry | Real products |
|------------|----------|----------|---------------|
| **Static screenshot → test case list** | ✅ many papers | ⚠️ exploratory | testRigor (semi), Mabl |
| **Recording video → full test script** | ✅ demos | ❌ no mature product | none (GPT-4V/Claude tried; <60% accuracy) |
| **Screenshot → locator suggestion** | ✅ mature | ✅ mainstream | Appium Inspector + AI plugins |
| **Screenshot → assertion suggestion** | ⚠️ research | ⚠️ early | Applitools (visual diff) |

### How big-tech actually does it (pragmatic version)

No company goes **screencast → complete test** directly. The pattern is **multi-step with a human in the loop**:

```
Screenshots / video
   ↓ (1) QA picks 1-3 key screenshots
   ↓
   ↓ (2) Feed to LLM: "list interactive elements + plausible flows"
   ↓
   ↓ (3) LLM outputs: "Add Expense button, Amount input, Food dropdown, ..."
   ↓
   ↓ (4) QA converts to `.feature` Scenario titles
   ↓
   ↓ (5) AI suggests locators (Claude Vision reads screenshot, guesses accessibility_id)
   ↓
   ↓ (6) QA verifies in Appium Inspector, writes to YAML
```

### testRigor / Mabl claim "video → test"

Reality: they ship a recorder; the user records their own actions; **a template engine** (not end-to-end AI) generates steps. Accuracy 70-80%; the remaining 20% needs human fixing.

### Trackify Day 4 AI scope (Task 13 in spec)

`ai/gen_cases.py` PoC (30-min build):

```python
def gen_cases_from_screenshots(screenshot_paths: list[Path]) -> str:
    """Feed screenshots to Claude Vision; ask for testable flows as JSON."""
    prompt = """Look at these Trackify app screenshots. For each, output JSON:
    {
      "screen_name": "Add Transaction modal",
      "actions": [
        {"element": "Add Expense button", "interaction": "tap"},
        {"element": "Amount input", "interaction": "type 100"}
      ],
      "candidate_scenarios": ["Add expense happy path", ...]
    }
    Do NOT generate Gherkin — humans write that."""
    images = [load_image(p) for p in screenshot_paths]
    return claude_vision_call(images=images, prompt=prompt)
```

**Key boundary**: AI produces **scenario titles** and **candidate flows**. The Gherkin syntax + step vocabulary contract (TECHNICAL_SPEC.md §6.6) stays human-authored.

---

## Q5 — BDD Excel schema (full field reference)

Mandatory (L1) and recommended (L2) fields. The shipped `data/test_cases_template.xlsx` has all L1 columns plus 5 L2 columns as the minimum viable registry.

### L1: Core traceability (11 columns, mandatory)

| Field | Type | Example | Why required |
|-------|------|---------|--------------|
| Test Case ID | string | `TC_ADD_TX_001` | sync_engine anchor — no ID, no sync |
| Module | enum | `add_transaction` | routing to `.feature` filename |
| Scenario Title | string | `Add expense happy path` | direct 1:1 with `Scenario:` line |
| Priority | enum | `P0` / `P1` / `P2` | maps to `@p0` / `@p1` / `@p2` marker |
| App Version Introduced | semver | `1.0.0` | Q2 selection filter |
| App Version Deprecated | semver/null | `null` (still active) | Q2 selection filter |
| Platform | enum | `android` / `ios` / `both` | cross-platform filter |
| Automation Status | enum | `manual` / `automated` / `candidate` / `deprecated` | sync_engine gate |
| Author | email | `kimbal@team.com` | responsibility |
| Last Reviewed Date | date | `2026-07-14` | prevents indefinite staleness |
| Last Run Result | enum | `pass` / `fail` / `skip` / `not_run` | health-check at a glance |

### L2: Execution details (5 columns, recommended)

| Field | Type | Example | Maps to |
|-------|------|---------|---------|
| Tags | string | `smoke,p0` | marker mapping |
| Pre-conditions | text | `Hive DB clean; user on Home page` | `Given ...` |
| Test Steps | text | `When user taps "Add Expense"...` | `When ...` |
| Expected Result | text | `Then transaction appears with amount "100.0"` | `Then ...` |
| Estimated Runtime (s) | int | `8` | scheduler input |

### L3: Optional (deferred until needed)

Linked User Story (JIRA URL), Linked Bug Tickets, Automation PR, Risk Score, Step Implementation Path, Latest Screenshot path, Latest Recording path, Notes, Owner Team, Reviewer.

### Automation Status semantics

| Value | Meaning | Sync behavior |
|-------|---------|---------------|
| `manual` | never automated | row skipped |
| `automated` | implemented in `.feature` | row pushed / kept in sync |
| `candidate` | QA candidate for automation | row skipped (for human review queue) |
| `deprecated` | retired | row moved to `# DEPRECATED:` block in `.feature` |

---

## Q6 — Excel watcher + sync engine architecture

### Full design

```
┌────────────────────────────────────────────────────────────────┐
│  data/test_cases.xlsx                                          │
└────────────────────┬───────────────────────────────────────────┘
                     │ (mtime change + SHA-256 hash diff)
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  scripts/sync_engine.py --watch                                │
│  - watchdog.Observer on data/                                  │
│  - 5s debounce                                                 │
│  - on event: re-read xlsx, diff vs features, apply             │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  parse_excel() → list[ExcelRow]                                │
│  parse_feature(path) → list[Scenario] (regex on # scenario_id) │
│  diff(excel, scenarios) → (added, modified, deleted, untouched)│
│  apply(feature_ast, diff) → new .feature text                  │
│    ↑ AST-level mutation: untouched nodes are byte-identical     │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Validation layer                                              │
│  - pytest --collect-only  (must exit 0)                        │
│  - pytest -m smoke          (must pass)                        │
│  - git diff --stat          (human eyeballs scope)             │
│  - git commit on sync/<date> branch (no push)                  │
└────────────────────────────────────────────────────────────────┘
```

### Critical design constraints (PoC scope)

| Constraint | Why |
|-----------|-----|
| Use regex, not the `gherkin` Python lib | Keeps §1 do-not-add list clean; sufficient for PoC |
| Backup before every write (`data/.backup/<file>.<date>.bak`) | Recoverable if diff logic has a bug |
| Untouched scenarios must be byte-identical after the run | Reviewer trust — sync doesn't accidentally reformat |
| Single xlsx file (no merge across files) | Day 6+ problem |
| One-shot CLI mode AND `--watch` mode | Local dev experience |
| `--check` mode | Pre-merge validation and drift detection with zero writes |

### Deferred (Day 6+, explicitly out of PoC)

- Bidirectional sync (writing `Last Run Result` back to Excel) — needs CI integration
- Auto-PR creation — needs GitHub API token
- Multi-xlsx-file merge — needs conflict resolution policy
- LLM-generated row proposals (Q4) — needs Claude Vision integration
- Real-time file-watch in CI — `--watch` is local-dev only

---

## Cross-cutting: how the 6 questions connect

```
            ┌─────────────────────────────────────────┐
            │      Q5 Excel = single source of truth  │
            └──────────────┬──────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   Manual cases (rows)          Automated cases (rows)
              │                         │
              │   ┌─────────────────┐   │
              └──▶│  Q6 sync engine │◀──┘
                  │  (scripts/)     │
                  └────────┬────────┘
                           │
                           ▼
                tests/features/*.feature
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   Q2 selective               Q3 doc-driven
   regression                 updates
              │                         │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   Q4 LLM-assisted       │
              │   row proposals         │
              └─────────────────────────┘
```

**Q5 is the data backbone. Q6 is the only write path. Q2 / Q3 / Q4 all flow through Q5 + Q6.**

---

## Delivered foundation vs deferred scale work

| Delivered | Deferred until scale requires it |
|-----------|----------------------------------|
| 7 cross-platform `.feature` scenarios | Version- and code-impact-aware selection |
| Page + Flow + Driver framework | Shared test-management database/API |
| Allure, screenshots, and Task 13 failure triage | Bidirectional result synchronization |
| Concurrent Android + iOS device matrix | Cloud device-farm orchestration |
| Task 14 Excel registry, incremental sync, rollback, and changed-case execution | Multi-writer conflict resolution and approval workflows |

TECHNICAL_SPEC.md §11 remains the source of truth for Task 14's shipped behavior.
