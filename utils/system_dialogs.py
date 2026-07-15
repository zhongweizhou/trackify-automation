"""Handlers for system dialogs that may interrupt app automation."""

from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException

PERMISSION_MESSAGE_ID = "com.android.permissioncontroller:id/permission_message"
PERMISSION_ALLOW_ID = "com.android.permissioncontroller:id/permission_allow_button"
NOTIFICATION_PROMPT_FRAGMENT = "send you notifications"


def allow_notification_permission_if_present(driver: object) -> bool:
    """Allow Trackify's Android notification prompt when it is visible.

    Other permission dialogs, including SMS permissions, are intentionally left
    untouched so their test flows retain control of those decisions.

    Args:
        driver: Active Appium WebDriver session.

    Returns:
        True when the notification prompt was found and accepted.
    """
    platform_name = str(
        getattr(driver, "capabilities", {}).get("platformName", "")
    ).lower()
    if platform_name != "android":
        return False

    try:
        messages = driver.find_elements(AppiumBy.ID, PERMISSION_MESSAGE_ID)
        notification_prompt = any(
            NOTIFICATION_PROMPT_FRAGMENT in (message.text or "").lower()
            for message in messages
        )
        if not notification_prompt:
            return False

        allow_buttons = driver.find_elements(AppiumBy.ID, PERMISSION_ALLOW_ID)
        if not allow_buttons:
            return False
        allow_buttons[0].click()
        return True
    except WebDriverException:
        return False
