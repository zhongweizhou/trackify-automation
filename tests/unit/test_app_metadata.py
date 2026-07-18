"""Cross-platform app-version metadata resolution."""

from __future__ import annotations

import plistlib
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from utils.app_metadata import (
    AppVersionError,
    parse_android_version,
    resolve_app_version,
)

pytestmark = pytest.mark.unit


def _config(
    platform: str,
    app_path: Path,
    *,
    device_udid: str | None = None,
    android_package: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        platform=platform,
        app_path=app_path,
        device_udid=device_udid,
        android_package=android_package,
    )


def _driver(**capabilities: object) -> SimpleNamespace:
    return SimpleNamespace(capabilities=capabilities)


def test_override_has_highest_priority(tmp_path: Path) -> None:
    driver = _driver(appVersion="1.0.0")

    version = resolve_app_version(
        driver,
        _config("ios", tmp_path / "missing.app"),
        environ={"APP_VERSION": " 9.8.7 "},
    )

    assert version == "9.8.7"


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        ({"appium:appVersion": "2.3.4"}, "2.3.4"),
        ({"appVersion": "3.4.5"}, "3.4.5"),
        ({"versionName": "4.5.6"}, "4.5.6"),
    ],
)
def test_capability_version_precedes_platform_fallback(
    tmp_path: Path,
    capabilities: dict[str, str],
    expected: str,
) -> None:
    assert (
        resolve_app_version(
            _driver(**capabilities),
            _config("ios", tmp_path / "missing.app"),
            environ={},
        )
        == expected
    )


def test_parse_android_version_name() -> None:
    output = "Packages:\n  versionCode=42 minSdk=23\n  versionName=1.2.3-rc.1\n"

    assert parse_android_version(output) == "1.2.3-rc.1"


def test_android_version_uses_selected_udid_and_package(tmp_path: Path) -> None:
    runner = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="versionName=5.6.7\n",
            stderr="",
        )
    )

    version = resolve_app_version(
        _driver(),
        _config(
            "android",
            tmp_path / "app.apk",
            device_udid="emulator-5554",
            android_package="com.example.trackify",
        ),
        environ={},
        command_runner=runner,
        adb_path="/sdk/adb",
    )

    assert version == "5.6.7"
    runner.assert_called_once_with(
        [
            "/sdk/adb",
            "-s",
            "emulator-5554",
            "shell",
            "dumpsys",
            "package",
            "com.example.trackify",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_ios_app_reads_short_bundle_version(tmp_path: Path) -> None:
    app_path = tmp_path / "Runner.app"
    app_path.mkdir()
    with (app_path / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleShortVersionString": "6.7.8"}, stream)

    assert (
        resolve_app_version(
            _driver(),
            _config("ios", app_path),
            environ={},
        )
        == "6.7.8"
    )


def test_ios_ipa_reads_short_bundle_version(tmp_path: Path) -> None:
    ipa_path = tmp_path / "Trackify.ipa"
    payload = plistlib.dumps({"CFBundleShortVersionString": "7.8.9"})
    with zipfile.ZipFile(ipa_path, "w") as archive:
        archive.writestr("Payload/Runner.app/Info.plist", payload)

    assert (
        resolve_app_version(
            _driver(),
            _config("ios", ipa_path),
            environ={},
        )
        == "7.8.9"
    )


def test_unresolved_version_has_actionable_override(tmp_path: Path) -> None:
    with pytest.raises(AppVersionError, match="set APP_VERSION") as exc_info:
        resolve_app_version(
            _driver(),
            _config("ios", tmp_path / "missing.app"),
            environ={},
        )

    assert "iOS app metadata" in str(exc_info.value)
