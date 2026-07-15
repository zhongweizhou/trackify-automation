"""Global pytest fixtures for the Trackify automation suite."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Generator
from typing import Any

import pytest

PKG = "com.trackify.app"


@pytest.fixture(scope="session")
def driver() -> Generator[Any, None, None]:
    """Create one Appium driver session for the pytest run.

    Yields:
        The live Appium driver instance created by ``AppiumDriverFactory``.
    """
    from utils.driver import AppiumDriverFactory

    platform = os.getenv("PLATFORM", "android")
    appium_driver = AppiumDriverFactory(platform=platform).create()
    try:
        yield appium_driver
    finally:
        appium_driver.quit()


@pytest.fixture(autouse=True)
def reset_app_state(driver: Any) -> Generator[None, None, None]:
    """Wipe Trackify local data before every test for deterministic state.

    Args:
        driver: The active Appium driver fixture.

    Yields:
        None after relaunching the app under test.
    """
    subprocess.run(["adb", "shell", "pm", "clear", PKG], check=True, timeout=10)
    driver.launch_app()
    yield


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: int | pytest.ExitCode,
) -> None:
    """Allow bootstrap collect-only verification before test files exist.

    Args:
        session: Completed pytest session.
        exitstatus: Pytest exit status before this hook adjusts it.
    """
    if (
        session.config.option.collectonly
        and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED
    ):
        session.exitstatus = pytest.ExitCode.OK
