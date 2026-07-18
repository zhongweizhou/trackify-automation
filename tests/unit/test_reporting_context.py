"""Allure execution-context reporting tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import conftest

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
