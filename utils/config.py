"""Configuration helpers for Trackify Appium sessions."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_APPIUM_SERVER_URL = "http://127.0.0.1:4723"
DEFAULT_ANDROID_DEVICE_NAME = "Android Emulator"
DEFAULT_IOS_DEVICE_NAME = "iPhone Simulator"

_CONFIG_SECTION = "trackify"


@dataclass(frozen=True)
class AppiumConfig:
    """Resolved configuration for creating an Appium driver session.

    Attributes:
        platform: Target mobile platform, either ``android`` or ``ios``.
        appium_server_url: Appium server endpoint.
        device_name: Emulator, simulator, or real device name.
        app_path: Local path to the app bundle or APK under test.
        android_package: Optional Android application package name override.
        android_activity: Optional Android launch activity override.
    """

    platform: str
    appium_server_url: str
    device_name: str
    app_path: Path
    android_package: str | None = None
    android_activity: str | None = None


def load_config(
    platform: str | None = None,
    ini_path: Path | None = None,
) -> AppiumConfig:
    """Load Appium configuration from pytest.ini, environment, and defaults.

    Explicit function arguments take precedence over environment variables;
    environment variables take precedence over optional ``[trackify]`` values
    in ``pytest.ini``; built-in defaults are used last.

    Args:
        platform: Optional explicit target platform.
        ini_path: Optional path to a pytest.ini-style configuration file.

    Returns:
        Resolved Appium configuration.
    """
    ini_values = _read_ini_values(ini_path)
    resolved_platform = _normalize_platform(
        platform
        or os.getenv("PLATFORM")
        or ini_values.get("platform")
        or "android"
    )
    default_app_path = _default_app_path(resolved_platform)
    app_path = Path(
        os.getenv("APP_PATH") or ini_values.get("app_path") or default_app_path
    ).expanduser()

    return AppiumConfig(
        platform=resolved_platform,
        appium_server_url=(
            os.getenv("APPIUM_SERVER_URL")
            or ini_values.get("appium_server_url")
            or DEFAULT_APPIUM_SERVER_URL
        ),
        device_name=(
            os.getenv("DEVICE_NAME")
            or ini_values.get("device_name")
            or _default_device_name(resolved_platform)
        ),
        app_path=app_path,
        android_package=os.getenv("ANDROID_PACKAGE")
        or ini_values.get("android_package"),
        android_activity=os.getenv("ANDROID_ACTIVITY")
        or ini_values.get("android_activity"),
    )


def _read_ini_values(ini_path: Path | None = None) -> dict[str, str]:
    config_path = ini_path or Path(__file__).resolve().parent.parent / "pytest.ini"
    parser = configparser.ConfigParser()
    parser.read(config_path)
    if not parser.has_section(_CONFIG_SECTION):
        return {}
    return {
        key: value.strip()
        for key, value in parser.items(_CONFIG_SECTION)
        if value.strip()
    }


def _normalize_platform(platform: str) -> str:
    normalized = platform.strip().lower()
    if normalized not in {"android", "ios"}:
        raise ValueError("Platform must be either 'android' or 'ios'.")
    return normalized


def _default_app_path(platform: str) -> Path:
    app_dir = Path(__file__).resolve().parent.parent / "app"
    if platform == "ios":
        return app_dir / "Runner.app"
    return app_dir / "app-release.apk"


def _default_device_name(platform: str) -> str:
    if platform == "ios":
        return DEFAULT_IOS_DEVICE_NAME
    return DEFAULT_ANDROID_DEVICE_NAME
