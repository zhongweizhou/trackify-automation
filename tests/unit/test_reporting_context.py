"""Allure execution-context reporting tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import conftest
from ai.triage import TriageResult

pytestmark = pytest.mark.unit


def _context() -> dict[str, str]:
    return {
        "environment": "test",
        "app_version": "1.2.3",
        "platform": "Android",
        "device_name": "Pixel 9",
        "device_udid": "emulator-5554",
        "os_version": "16",
    }


def test_execution_context_contains_selected_environment_and_app_version() -> None:
    driver = SimpleNamespace(
        capabilities={
            "platformName": "Android",
            "appium:deviceName": "Pixel 9",
            "appium:udid": "emulator-5554",
            "appium:platformVersion": "16",
        }
    )

    assert conftest._execution_context(
        driver,
        environment="test",
        app_version="1.2.3",
        environ={},
    ) == _context()


def test_environment_properties_include_environment_and_app_version(
    tmp_path: Path,
) -> None:
    pytestconfig = SimpleNamespace(
        option=SimpleNamespace(allure_report_dir=str(tmp_path))
    )

    conftest._write_allure_environment(pytestconfig, _context())

    text = (tmp_path / "environment.properties").read_text(encoding="utf-8")
    assert "Test.Environment=test" in text
    assert "App.Version=1.2.3" in text
    assert "Device.OS.Version=16" in text


def test_full_allure_context_includes_app_version(monkeypatch: pytest.MonkeyPatch) -> None:
    parameter = MagicMock()
    monkeypatch.setattr(conftest.allure.dynamic, "parameter", parameter)

    conftest._attach_allure_context(_context(), include_app_version=True)

    parameter.assert_any_call("Environment", "test")
    parameter.assert_any_call("App Version", "1.2.3")
    parameter.assert_any_call("OS Version", "16")


def test_call_phase_only_adds_app_version_to_existing_allure_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_suite = MagicMock()
    suite = MagicMock()
    host = MagicMock()
    parameter = MagicMock()
    monkeypatch.setattr(conftest.allure.dynamic, "parent_suite", parent_suite)
    monkeypatch.setattr(conftest.allure.dynamic, "suite", suite)
    monkeypatch.setattr(conftest.allure.dynamic, "label", host)
    monkeypatch.setattr(conftest.allure.dynamic, "parameter", parameter)

    context = _context()
    conftest._attach_allure_context(context, include_app_version=False)
    item = SimpleNamespace(
        config=SimpleNamespace(stash={conftest._EXECUTION_CONTEXT: context})
    )

    conftest.pytest_runtest_call(item)

    parent_suite.assert_called_once_with("test")
    suite.assert_called_once_with("Android - Pixel 9")
    host.assert_called_once_with("host", "emulator-5554")
    parameter.assert_any_call("App Version", "1.2.3")


def test_unit_items_disable_global_reruns() -> None:
    unit_item = MagicMock()
    mobile_item = MagicMock()
    unit_item.get_closest_marker.side_effect = (
        lambda name: object() if name == "unit" else None
    )
    mobile_item.get_closest_marker.return_value = None

    conftest.pytest_collection_modifyitems([unit_item, mobile_item])

    added = unit_item.add_marker.call_args.args[0]
    assert added.name == "flaky"
    assert added.kwargs == {"reruns": 0}
    mobile_item.add_marker.assert_not_called()


def test_bdd_step_error_captures_attempt_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = SimpleNamespace(
        name="test_transfer[param.value]",
        execution_count=2,
        stash=pytest.Stash(),
    )
    driver = MagicMock(page_source="<hierarchy />")
    driver.save_screenshot.side_effect = (
        lambda path: Path(path).write_bytes(b"png") > 0
    )
    request = SimpleNamespace(
        node=item,
        getfixturevalue=MagicMock(return_value=driver),
    )
    file_attachment = MagicMock()
    monkeypatch.setattr(conftest, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(conftest.allure.attach, "file", file_attachment)

    conftest.pytest_bdd_step_error(
        request=request,
        step=SimpleNamespace(keyword="And", name="user taps Save"),
        exception=RuntimeError("home did not appear"),
    )

    evidence = item.stash[conftest._FAILURE_EVIDENCE][2]
    assert evidence.screenshot_path.name.endswith("attempt-2.png")
    assert evidence.page_source_path.name.endswith("attempt-2.xml")
    assert evidence.failed_step == "And user taps Save"
    assert evidence.screenshot_path.is_file()
    assert evidence.page_source_path.read_text(encoding="utf-8") == "<hierarchy />"
    assert file_attachment.call_count == 2


def _triage_result() -> TriageResult:
    return TriageResult(
        category="Script",
        confidence=0.9,
        reasoning="Final failure classified.",
        next_action="Review the final attempt.",
        classifier="local",
        matched_signatures=("python_contract",),
    )


@pytest.mark.parametrize(
    ("attempt", "reruns", "triage_calls"),
    ((1, 2, 0), (2, 2, 0), (3, 2, 1)),
)
def test_triage_runs_only_after_reruns_are_exhausted(
    attempt: int,
    reruns: int,
    triage_calls: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter = SimpleNamespace(write_line=MagicMock())
    item = SimpleNamespace(
        name="test_transfer",
        nodeid="tests/mobile.py::test_transfer",
        execution_count=attempt,
        funcargs={},
        stash=pytest.Stash(),
        config=SimpleNamespace(
            pluginmanager=SimpleNamespace(
                getplugin=lambda name: (
                    reporter if name == "terminalreporter" else None
                )
            )
        ),
    )
    item.stash[conftest._FAILURE_EVIDENCE] = {
        attempt: conftest.FailureEvidence(
            attempt=attempt,
            failed_step="And user taps Save",
            screenshot_path=Path(f"/tmp/test-transfer-attempt-{attempt}.png"),
            page_source_path=Path(f"/tmp/test-transfer-attempt-{attempt}.xml"),
        )
    }
    excinfo = SimpleNamespace(
        value=TypeError("bad call"),
        getrepr=lambda style: "Traceback: TypeError: bad call",
    )
    call = SimpleNamespace(excinfo=excinfo)
    report = SimpleNamespace(failed=True, when="call")
    outcome = SimpleNamespace(get_result=lambda: report)
    triage = MagicMock(return_value=_triage_result())
    monkeypatch.setattr(conftest, "_configured_reruns", lambda current: reruns, raising=False)
    monkeypatch.setattr(conftest, "_capture_failure_screenshot", lambda current: None)
    monkeypatch.setattr(conftest, "triage_failure", triage)
    monkeypatch.setattr(conftest.allure, "attach", MagicMock())

    hook = conftest.pytest_runtest_makereport(item, call)
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(outcome)

    assert triage.call_count == triage_calls
    if triage_calls:
        payload = triage.call_args.args[0]
        assert payload["attempt"] == 3
        assert payload["max_attempts"] == 3
        assert payload["failed_step"] == "And user taps Save"
        assert payload["screenshot_path"].name == "test-transfer-attempt-3.png"


def test_passing_retry_does_not_triage(monkeypatch: pytest.MonkeyPatch) -> None:
    item = SimpleNamespace(
        name="test_transfer",
        nodeid="tests/mobile.py::test_transfer",
        execution_count=2,
        funcargs={},
        stash=pytest.Stash(),
    )
    call = SimpleNamespace(excinfo=None)
    report = SimpleNamespace(failed=False, passed=True, when="call")
    outcome = SimpleNamespace(get_result=lambda: report)
    triage = MagicMock()
    monkeypatch.setattr(conftest, "triage_failure", triage)

    hook = conftest.pytest_runtest_makereport(item, call)
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(outcome)

    triage.assert_not_called()
