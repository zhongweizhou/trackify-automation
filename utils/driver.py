"""Appium driver factory for Trackify mobile automation."""

from __future__ import annotations

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from appium.webdriver.webdriver import WebDriver

from utils.config import AppiumConfig, load_config


class AppiumDriverFactory:
    """Create Appium WebDriver sessions for supported Trackify platforms."""

    def __init__(
        self,
        platform: str = "android",
        config: AppiumConfig | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            platform: Target platform when an explicit config is not supplied.
            config: Optional pre-resolved Appium configuration.
        """
        self._config = config or load_config(platform=platform)

    def create(self) -> WebDriver:
        """Create and return a live Appium WebDriver session.

        Returns:
            The Appium WebDriver session.
        """
        if self._config.platform == "android":
            options = self._android_options()
        else:
            options = self._ios_options()

        return webdriver.Remote(
            command_executor=self._config.appium_server_url,
            options=options,
        )

    def _android_options(self) -> UiAutomator2Options:
        capabilities = {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": self._config.device_name,
            "app": str(self._config.app_path.resolve()),
            "autoGrantPermissions": True,
            "newCommandTimeout": 120,
            "noReset": False,
        }
        if self._config.android_package:
            capabilities["appPackage"] = self._config.android_package
        if self._config.android_activity:
            capabilities["appActivity"] = self._config.android_activity
        if self._config.device_udid:
            capabilities["udid"] = self._config.device_udid
        if self._config.system_port is not None:
            capabilities["systemPort"] = self._config.system_port
        return UiAutomator2Options().load_capabilities(capabilities)

    def _ios_options(self) -> XCUITestOptions:
        capabilities = {
            "platformName": "iOS",
            "automationName": "XCUITest",
            "deviceName": self._config.device_name,
            "app": str(self._config.app_path.resolve()),
            "newCommandTimeout": 120,
            "noReset": False,
        }
        if self._config.device_udid:
            capabilities["udid"] = self._config.device_udid
        if self._config.wda_local_port is not None:
            capabilities["wdaLocalPort"] = self._config.wda_local_port
        if self._config.mjpeg_server_port is not None:
            capabilities["mjpegServerPort"] = self._config.mjpeg_server_port
        if self._config.derived_data_path is not None:
            capabilities["derivedDataPath"] = str(self._config.derived_data_path)
        return XCUITestOptions().load_capabilities(capabilities)
