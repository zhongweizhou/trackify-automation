"""Base page primitives shared by Trackify page objects."""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

Locator = tuple[str, str]

DEFAULT_TIMEOUT = 10

_STRATEGY_TO_BY = {
    "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
    "id": AppiumBy.ID,
    "xpath": AppiumBy.XPATH,
    "predicate": AppiumBy.IOS_PREDICATE,
    "class": AppiumBy.CLASS_NAME,
    "class_chain": AppiumBy.IOS_CLASS_CHAIN,
}


class BasePage(ABC):
    """Base class exposing stable UI primitives for all page objects."""

    def __init__(self, driver: object, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Initialize a page with an Appium driver.

        Args:
            driver: Active Appium WebDriver session.
            timeout: Default explicit wait timeout in seconds.
        """
        self._driver = driver
        self._timeout = timeout

    def wait_for(self, locator: Locator, timeout: int | None = None) -> WebElement:
        """Wait until an element is visible and return it.

        Args:
            locator: Locator tuple in ``(strategy, value)`` format.
            timeout: Optional timeout override in seconds.

        Returns:
            The visible element matching the locator.
        """
        by_locator = self._to_appium_locator(locator)
        wait_timeout = timeout if timeout is not None else self._timeout
        return WebDriverWait(self._driver, wait_timeout).until(
            EC.visibility_of_element_located(by_locator)
        )

    def click(self, locator: Locator, timeout: int | None = None) -> None:
        """Wait for an element and tap it.

        Args:
            locator: Locator tuple in ``(strategy, value)`` format.
            timeout: Optional timeout override in seconds.
        """
        self.wait_for(locator, timeout).click()

    def input_text(
        self,
        locator: Locator,
        text: str,
        timeout: int | None = None,
        clear: bool = True,
    ) -> None:
        """Enter text into an input element.

        Args:
            locator: Locator tuple in ``(strategy, value)`` format.
            text: Text value to enter.
            timeout: Optional timeout override in seconds.
            clear: Whether to clear the field before typing.
        """
        element = self.wait_for(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)

    def is_visible(self, locator: Locator, timeout: int | None = None) -> bool:
        """Return whether an element becomes visible within the timeout.

        Args:
            locator: Locator tuple in ``(strategy, value)`` format.
            timeout: Optional timeout override in seconds.

        Returns:
            True when the element is visible, otherwise False.
        """
        try:
            self.wait_for(locator, timeout)
        except TimeoutException:
            return False
        return True

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 500,
    ) -> None:
        """Swipe between two screen coordinates.

        Args:
            start_x: Starting x-coordinate.
            start_y: Starting y-coordinate.
            end_x: Ending x-coordinate.
            end_y: Ending y-coordinate.
            duration_ms: Gesture duration in milliseconds.
        """
        self._driver.swipe(start_x, start_y, end_x, end_y, duration_ms)

    def screenshot(self, path: str | Path) -> Path:
        """Save a screenshot to disk.

        Args:
            path: Destination image path.

        Returns:
            The resolved screenshot path.
        """
        screenshot_path = Path(path).resolve()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._driver.save_screenshot(str(screenshot_path))
        return screenshot_path

    def _to_appium_locator(self, locator: Locator) -> tuple[str, str]:
        strategy, value = locator
        if strategy not in _STRATEGY_TO_BY:
            supported = ", ".join(sorted(_STRATEGY_TO_BY))
            raise KeyError(
                f"Unsupported locator strategy '{strategy}'. Use one of: {supported}"
            )
        return (_STRATEGY_TO_BY[strategy], value)
