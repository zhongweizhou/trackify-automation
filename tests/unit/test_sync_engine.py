"""Unit tests for safe, incremental Excel-to-Gherkin synchronization."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import scripts.sync_engine as sync_engine
from scripts.sync_engine import (
    LOCK_FILE_NAME,
    MODULE_PATHS,
    RegistryRow,
    SyncError,
    ValidationError,
    _normalized_tags,
    apply_plan,
    build_plan,
    build_plan_from_rows,
    changed_nodeids,
    execute_once,
    file_sha256,
    parse_feature,
    parse_workbook,
    run_changed_cases,
)

pytestmark = pytest.mark.unit
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "data" / "test_cases.xlsx"


def _success(_: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, "collected", "")


def _failure(_: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 1, "collection failed", "missing step")


def _sync_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "tests" / "features").mkdir(parents=True)
    (root / "tests" / "step_defs").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    for relative_path in MODULE_PATHS.values():
        source = PROJECT_ROOT / relative_path
        destination = root / relative_path
        shutil.copy2(source, destination)
    shutil.copy2(REGISTRY, root / "data" / "test_cases.xlsx")
    return root


def _row(rows: tuple[RegistryRow, ...], scenario_id: str) -> RegistryRow:
    return next(row for row in rows if row.scenario_id == scenario_id)


def _replace_row(
    rows: tuple[RegistryRow, ...],
    scenario_id: str,
    updated: RegistryRow,
) -> tuple[RegistryRow, ...]:
    return tuple(updated if row.scenario_id == scenario_id else row for row in rows)


def _block_hashes(root: Path, module: str) -> dict[str, str]:
    document = parse_feature(module, root / MODULE_PATHS[module])
    return {
        block.scenario_id: hashlib.sha256(block.text.encode("utf-8")).hexdigest()
        for block in document.blocks
    }


def test_corrected_registry_contains_seven_routed_automated_rows() -> None:
    rows = parse_workbook(REGISTRY)

    assert len(rows) == 7
    assert all(row.status == "automated" for row in rows)
    assert sum(row.module == "add_transaction" for row in rows) == 5
    assert sum(row.module == "transactions" for row in rows) == 2
    assert _row(rows, "TC_ADD_TX_005").steps[3] == (
        'user creates custom category "baby cost"'
    )


def test_committed_registry_and_features_have_zero_drift(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    workbook_hash = file_sha256(workbook)
    feature_hashes = {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    }

    exit_code = execute_once(workbook, apply=False, run_changed=False, root=root)

    assert exit_code == 0
    assert file_sha256(workbook) == workbook_hash
    assert {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    } == feature_hashes


def test_one_modified_row_updates_only_its_routed_feature(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    original = _row(rows, "TC_ADD_TX_001")
    updated = replace(
        original,
        steps=tuple(
            phrase.replace('amount "100"', 'amount "101"')
            for phrase in original.steps
        ),
    )
    changed_rows = _replace_row(rows, original.scenario_id, updated)
    transaction_path = root / MODULE_PATHS["transactions"]
    transaction_hash = file_sha256(transaction_path)
    before_blocks = _block_hashes(root, "add_transaction")
    workbook_hash = file_sha256(workbook)

    plan = build_plan_from_rows(changed_rows, root)

    assert [(change.kind, change.row.scenario_id) for change in plan.changes] == [
        ("modified", "TC_ADD_TX_001")
    ]
    assert set(plan.rendered_documents) == {
        root / MODULE_PATHS["add_transaction"]
    }
    apply_plan(plan, workbook, root, _success)

    assert file_sha256(transaction_path) == transaction_hash
    assert file_sha256(workbook) == workbook_hash
    after_blocks = _block_hashes(root, "add_transaction")
    assert before_blocks["TC_ADD_TX_001"] != after_blocks["TC_ADD_TX_001"]
    for scenario_id in before_blocks.keys() - {"TC_ADD_TX_001"}:
        assert before_blocks[scenario_id] == after_blocks[scenario_id]


def test_apply_is_idempotent(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    original = _row(rows, "TC_ADD_TX_002")
    changed_rows = _replace_row(
        rows,
        original.scenario_id,
        replace(original, title="Add income happy path updated"),
    )
    first_plan = build_plan_from_rows(changed_rows, root)
    apply_plan(first_plan, workbook, root, _success)
    first_hashes = {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    }

    second_plan = build_plan_from_rows(changed_rows, root)
    apply_plan(second_plan, workbook, root, _success)

    assert not second_plan.has_drift
    assert {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    } == first_hashes


def test_neighboring_add_preserves_existing_blocks(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    source = _row(rows, "TC_TXN_002")
    added = replace(
        source,
        row_number=9,
        scenario_id="TC_TXN_003",
        title="New transaction registry scenario",
        tags=("p1", "filter"),
    )
    before_blocks = _block_hashes(root, "transactions")

    plan = build_plan_from_rows((*rows, added), root)
    apply_plan(plan, workbook, root, _success)

    assert [(change.kind, change.row.scenario_id) for change in plan.changes] == [
        ("added", "TC_TXN_003")
    ]
    after_blocks = _block_hashes(root, "transactions")
    for scenario_id, digest in before_blocks.items():
        assert after_blocks[scenario_id] == digest


def test_deprecation_is_explicit_and_preserves_neighbors(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    original = _row(rows, "TC_ADD_TX_005")
    deprecated = replace(
        original,
        status="deprecated",
        deprecated_in="2.0.0",
    )
    changed_rows = _replace_row(rows, original.scenario_id, deprecated)
    before_blocks = _block_hashes(root, "add_transaction")

    plan = build_plan_from_rows(changed_rows, root)
    apply_plan(plan, workbook, root, _success)

    assert plan.changes[0].kind == "deprecated"
    assert plan.changed_active_rows == ()
    document = parse_feature(
        "add_transaction",
        root / MODULE_PATHS["add_transaction"],
    )
    block = next(
        item for item in document.blocks if item.scenario_id == original.scenario_id
    )
    assert "# deprecated_in: 2.0.0" in block.core
    assert f"# DEPRECATED BEGIN {original.scenario_id}" in block.core
    for scenario_id, digest in before_blocks.items():
        if scenario_id != original.scenario_id:
            assert _block_hashes(root, "add_transaction")[scenario_id] == digest


def test_manual_or_candidate_cannot_silently_remove_existing_coverage(
    tmp_path: Path,
) -> None:
    root = _sync_root(tmp_path)
    rows = parse_workbook(root / "data" / "test_cases.xlsx")
    existing = _row(rows, "TC_ADD_TX_001")

    with pytest.raises(ValidationError, match="transition it to deprecated"):
        build_plan_from_rows(
            _replace_row(rows, existing.scenario_id, replace(existing, status="manual")),
            root,
        )


def test_deprecating_unknown_id_is_rejected(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    rows = parse_workbook(root / "data" / "test_cases.xlsx")
    source = rows[0]
    unknown = replace(
        source,
        row_number=9,
        scenario_id="TC_ADD_TX_999",
        title="Unknown deprecated scenario",
        status="deprecated",
        deprecated_in="2.0.0",
    )

    with pytest.raises(ValidationError, match="cannot deprecate unknown"):
        build_plan_from_rows((*rows, unknown), root)


def test_duplicate_workbook_ids_are_rejected(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    rows = parse_workbook(root / "data" / "test_cases.xlsx")

    with pytest.raises(ValidationError, match="duplicate Test Case ID"):
        build_plan_from_rows((*rows, rows[0]), root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("module", "../../unsafe", "unknown Module"),
        ("priority", "P9", "invalid Priority"),
        ("platform", "windows", "invalid Platform"),
        ("status", "deleted", "invalid Automation Status"),
        ("title", "", "missing Scenario Title"),
    ],
)
def test_invalid_required_or_enum_values_are_rejected(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    root = _sync_root(tmp_path)
    rows = parse_workbook(root / "data" / "test_cases.xlsx")
    invalid = replace(rows[0], **{field: value})

    with pytest.raises(ValidationError, match=message):
        build_plan_from_rows(
            _replace_row(rows, rows[0].scenario_id, invalid),
            root,
        )


def test_tag_normalization_injects_and_deduplicates_priority() -> None:
    assert _normalized_tags("smoke,p0,p0", "P0", 2) == ("smoke", "p0")
    assert _normalized_tags("custom_category", "P1", 2) == (
        "p1",
        "custom_category",
    )
    with pytest.raises(ValueError, match="invalid marker"):
        _normalized_tags("@smoke", "P0", 2)


def test_cross_feature_duplicate_id_is_rejected(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    add_document = parse_feature(
        "add_transaction",
        root / MODULE_PATHS["add_transaction"],
    )
    duplicate = add_document.blocks[0].text
    transaction_path = root / MODULE_PATHS["transactions"]
    transaction_path.write_text(
        transaction_path.read_text(encoding="utf-8").rstrip() + "\n\n" + duplicate,
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate feature ID"):
        build_plan(root / "data" / "test_cases.xlsx", root)


def test_missing_workbook_id_is_not_treated_as_delete(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    rows = parse_workbook(root / "data" / "test_cases.xlsx")

    with pytest.raises(ValidationError, match="missing from workbook"):
        build_plan_from_rows(rows[:-1], root)


def test_unmanaged_scenario_and_outline_are_rejected(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    path = root / MODULE_PATHS["transactions"]
    original = path.read_text(encoding="utf-8")
    path.write_text(
        original + "\nScenario: unmanaged\n  When unsupported\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="unmanaged Scenario"):
        build_plan(root / "data" / "test_cases.xlsx", root)

    path.write_text(
        original.replace(
            "Feature: Transactions List",
            "Feature: Transactions List\n\nScenario Outline: unsupported",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="Scenario Outline is unsupported"):
        build_plan(root / "data" / "test_cases.xlsx", root)


def test_crlf_newlines_are_preserved(tmp_path: Path) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    for relative_path in MODULE_PATHS.values():
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    original = _row(rows, "TC_TXN_002")
    changed_rows = _replace_row(
        rows,
        original.scenario_id,
        replace(original, title="Transactions grouped by date updated"),
    )

    plan = build_plan_from_rows(changed_rows, root)
    rendered = plan.rendered_documents[root / MODULE_PATHS["transactions"]]

    assert "\r\n" in rendered
    assert "\n" not in rendered.replace("\r\n", "")


def test_collection_failure_rolls_back_and_cleans_lock_and_temp(
    tmp_path: Path,
) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    original = rows[0]
    changed_rows = _replace_row(
        rows,
        original.scenario_id,
        replace(original, title="Collection failure change"),
    )
    plan = build_plan_from_rows(changed_rows, root)
    before_hashes = {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    }

    with pytest.raises(SyncError, match="all changed features restored"):
        apply_plan(plan, workbook, root, _failure)

    assert {
        path: file_sha256(root / path) for path in MODULE_PATHS.values()
    } == before_hashes
    backup_dir = root / "data" / ".backup"
    assert not (backup_dir / LOCK_FILE_NAME).exists()
    assert not list((root / "tests" / "features").glob("*.tmp"))


def test_early_apply_failure_still_cleans_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _sync_root(tmp_path)
    workbook = root / "data" / "test_cases.xlsx"
    rows = parse_workbook(workbook)
    changed = replace(rows[0], title="Early apply failure")
    plan = build_plan_from_rows(
        _replace_row(rows, rows[0].scenario_id, changed),
        root,
    )

    def fail_hash(_: Path) -> str:
        raise OSError("simulated workbook read failure")

    monkeypatch.setattr(sync_engine, "file_sha256", fail_hash)

    with pytest.raises(OSError, match="simulated workbook read failure"):
        apply_plan(plan, workbook, root, _success)

    assert not (root / "data" / ".backup" / LOCK_FILE_NAME).exists()


def test_changed_nodeids_are_targeted_and_stable() -> None:
    rows = parse_workbook(REGISTRY)
    validation = _row(rows, "TC_ADD_TX_004")

    assert changed_nodeids((validation,)) == (
        "tests/step_defs/add_transaction_steps.py::"
        "test_validation__empty_amount_shows_error_and_does_not_save",
    )


def test_changed_case_success_reports_count_and_allure_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    row = _row(parse_workbook(REGISTRY), "TC_ADD_TX_001")
    monkeypatch.setattr(
        sync_engine.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )

    assert run_changed_cases((row,), root=tmp_path) == 0

    output = capsys.readouterr().out
    assert "TC_ADD_TX_001" in output
    assert "Changed-case execution PASSED: 1 scenario(s)" in output
    assert "allure-results" in output


def test_changed_case_failure_reports_debug_scope_and_exact_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    row = _row(parse_workbook(REGISTRY), "TC_ADD_TX_001")
    monkeypatch.setattr(
        sync_engine.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1),
    )

    assert run_changed_cases((row,), root=tmp_path) == 1

    output = capsys.readouterr().out
    assert "Feature changes were kept for debugging" in output
    assert "Task 13 triage" in output
    assert "YAML locators" in output
    assert "add_transaction_steps.py::test_add_expense_happy_path" in output
    assert "allure-results" in output
