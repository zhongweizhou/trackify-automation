"""Resolve the tested app version from explicit and platform metadata."""

from __future__ import annotations

import os
import plistlib
import re
import subprocess
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

_ANDROID_PACKAGE = "com.blixcode.trackify"
_ANDROID_VERSION_PATTERN = re.compile(r"^\s*versionName\s*=\s*(\S.*?)\s*$", re.MULTILINE)
_CAPABILITY_KEYS = (
    "appium:appVersion",
    "appVersion",
    "appium:versionName",
    "versionName",
    "CFBundleShortVersionString",
)


class AppVersionError(RuntimeError):
    """The tested app version could not be determined reliably."""


class AppMetadataConfig(Protocol):
    """Configuration fields required by app-version discovery."""

    platform: str
    app_path: Path
    device_udid: str | None
    android_package: str | None


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def resolve_app_version(
    driver: Any,
    config: AppMetadataConfig,
    *,
    environ: Mapping[str, str] = os.environ,
    command_runner: CommandRunner = subprocess.run,
    adb_path: str | None = None,
) -> str:
    """Return a non-empty tested app version using deterministic precedence."""
    if override := _normalized_version(environ.get("APP_VERSION")):
        return override

    capabilities = getattr(driver, "capabilities", {})
    if isinstance(capabilities, Mapping):
        for key in _CAPABILITY_KEYS:
            if version := _normalized_version(capabilities.get(key)):
                return version

    platform = config.platform.strip().lower()
    if platform == "android":
        return _resolve_android_version(
            config,
            command_runner=command_runner,
            adb_path=adb_path or _adb(),
        )
    if platform == "ios":
        return _resolve_ios_version(config.app_path)

    raise AppVersionError(
        f"Unsupported platform {config.platform!r} during app-version discovery; "
        "set APP_VERSION to the tested release version."
    )


def parse_android_version(output: str) -> str:
    """Extract ``versionName`` from ``adb dumpsys package`` output."""
    match = _ANDROID_VERSION_PATTERN.search(output)
    if match and (version := _normalized_version(match.group(1))):
        return version
    raise AppVersionError("Android package metadata did not contain versionName")


def _resolve_android_version(
    config: AppMetadataConfig,
    *,
    command_runner: CommandRunner,
    adb_path: str,
) -> str:
    package = config.android_package or _ANDROID_PACKAGE
    command = [adb_path]
    if config.device_udid:
        command.extend(["-s", config.device_udid])
    command.extend(["shell", "dumpsys", "package", package])

    try:
        result = command_runner(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return parse_android_version(result.stdout)
    except (OSError, subprocess.SubprocessError, AppVersionError) as exc:
        raise AppVersionError(
            "Could not resolve Android installed-package metadata for the selected "
            "device; verify adb/package routing or set APP_VERSION explicitly."
        ) from exc


def _resolve_ios_version(app_path: Path) -> str:
    path = Path(app_path).expanduser()
    try:
        if path.is_dir() and path.suffix.lower() == ".app":
            with (path / "Info.plist").open("rb") as stream:
                payload = plistlib.load(stream)
        elif path.is_file() and path.suffix.lower() == ".ipa":
            payload = _read_ipa_plist(path)
        else:
            raise AppVersionError("iOS app path is not a readable .app or .ipa")
    except (
        OSError,
        plistlib.InvalidFileException,
        zipfile.BadZipFile,
        KeyError,
        AppVersionError,
    ) as exc:
        raise AppVersionError(
            "Could not read iOS app metadata from the selected .app or .ipa; "
            "verify APP_PATH or set APP_VERSION explicitly."
        ) from exc

    version = _normalized_version(payload.get("CFBundleShortVersionString"))
    if version:
        return version
    raise AppVersionError(
        "iOS app metadata does not contain CFBundleShortVersionString; "
        "set APP_VERSION explicitly."
    )


def _read_ipa_plist(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        candidates = sorted(
            name
            for name in archive.namelist()
            if _is_ipa_info_plist(name)
        )
        if not candidates:
            raise KeyError("Payload/*.app/Info.plist")
        with archive.open(candidates[0]) as stream:
            payload = plistlib.load(stream)
    if not isinstance(payload, dict):
        raise plistlib.InvalidFileException("Info.plist root must be a mapping")
    return payload


def _is_ipa_info_plist(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return (
        len(parts) >= 3
        and parts[0] == "Payload"
        and parts[-1] == "Info.plist"
        and any(part.endswith(".app") for part in parts[1:-1])
    )


def _normalized_version(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    normalized = str(value).strip()
    return normalized or None


def _adb() -> str:
    sdk_root = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
    candidates = []
    if sdk_root:
        candidates.append(Path(sdk_root) / "platform-tools" / "adb")
    candidates.append(
        Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "adb"
