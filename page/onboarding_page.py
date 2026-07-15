"""Page object for Trackify's first-run onboarding flow."""

from __future__ import annotations

import os
import re

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator

MAX_BUDGET_ADJUSTMENTS = 50


class OnboardingPage(BasePage):
    """Interact with the three first-run setup pages."""

    def __init__(
        self,
        driver: object,
        platform: str | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the onboarding page object.

        Args:
            driver: Active Appium WebDriver session.
            platform: Optional platform locator section to use.
            timeout: Default explicit wait timeout in seconds.
        """
        super().__init__(driver=driver, timeout=timeout)
        self._platform = (platform or os.getenv("PLATFORM", "android")).lower()

    def enter_name_and_continue(self, name: str) -> None:
        """Save the user's name and open the budget setup page.

        Args:
            name: Non-empty profile name.
        """
        self.wait_for(self._loc("name_page"))
        self._tap_locator(self._loc("name_input"))
        name_input = self.wait_for(self._loc("name_input"))
        name_input.clear()
        name_input.send_keys(name)
        self._tap_locator(self._loc("name_page"))
        self._hide_keyboard_if_present()
        self._tap_locator(self._loc("continue_button"))
        self.wait_for(self._loc("budget_page"))

    def select_currency(self, currency: str) -> None:
        """Select a currency on the budget setup page.

        Args:
            currency: Full visible currency label, such as ``$ US Dollar``.
        """
        self.wait_for(self._loc("budget_page"))
        self._tap_locator(self._loc("currency_selector"))
        self._tap_locator(self._loc("currency_option", currency=currency))
        self.wait_for(self._loc("currency_option", currency=currency))

    def set_monthly_budget(self, monthly_budget: int | str) -> None:
        """Adjust the monthly budget slider to an exact displayed value.

        The Flutter slider exposes only its thumb bounds, not its full track.
        Feedback from the displayed budget keeps the adjustment independent of
        a fixed screen coordinate.

        Args:
            monthly_budget: Positive target budget shown by the app.

        Raises:
            AssertionError: If the slider cannot reach the target value.
            ValueError: If the requested budget is invalid.
        """
        target = self._parse_budget(monthly_budget)
        current = self.monthly_budget()
        stagnant_adjustments = 0

        for _ in range(MAX_BUDGET_ADJUSTMENTS):
            if current == target:
                return

            slider = self.wait_for(self._loc("budget_slider"))
            center_x = slider.location["x"] + slider.size["width"] // 2
            center_y = slider.location["y"] + slider.size["height"] // 2
            direction = 1 if target > current else -1
            distance = max(
                1,
                min(
                    20,
                    abs(target - current) // 1000 + stagnant_adjustments,
                ),
            )
            self._tap_point(center_x + direction * distance, center_y)
            updated_budget = self.monthly_budget()
            if updated_budget == current:
                stagnant_adjustments += 1
            else:
                stagnant_adjustments = 0
            current = updated_budget

        raise AssertionError(
            f"Monthly budget did not reach {target}; current value is {current}."
        )

    def monthly_budget(self) -> int:
        """Return the monthly budget currently displayed on the setup page."""
        description = self.wait_for(self._loc("budget_page")).get_attribute(
            "content-desc"
        )
        match = re.search(r"Monthly Budget\s+\D*([\d,]+)", description or "")
        if not match:
            raise AssertionError(
                f"Could not read Monthly Budget from: {description!r}"
            )
        return int(match.group(1).replace(",", ""))

    def continue_from_budget(self) -> None:
        """Continue from budget setup to Stay on Track."""
        self._tap_locator(self._loc("continue_button"))
        self.wait_for(self._loc("tracking_page"))

    def enable_bank_sms_reader(self) -> None:
        """Enable Bank SMS Reader and verify that the switch is checked."""
        self.wait_for(self._loc("tracking_page"))
        if not self.is_bank_sms_reader_enabled():
            self._tap_locator(self._loc("bank_sms_reader_switch"))

        by_locator = self._to_appium_locator(self._loc("bank_sms_reader_switch"))
        WebDriverWait(self._driver, self._timeout).until(
            lambda driver: str(
                driver.find_element(*by_locator).get_attribute("checked")
            ).lower()
            == "true"
        )

    def is_bank_sms_reader_enabled(self) -> bool:
        """Return whether the Bank SMS Reader switch is checked."""
        checked = self.wait_for(
            self._loc("bank_sms_reader_switch")
        ).get_attribute("checked")
        return str(checked).lower() == "true"

    def tap_get_started(self) -> None:
        """Finish onboarding and leave the setup flow."""
        self._tap_locator(self._loc("get_started_button"))

    def _loc(self, key: str, **format_values: str) -> Locator:
        strategy, value = load_locator("onboarding", key, self._platform)
        if format_values:
            value = value.format(**format_values)
        return strategy, value

    def _tap_locator(self, locator: Locator) -> None:
        element = self.wait_for(locator)
        center_x = element.location["x"] + element.size["width"] // 2
        center_y = element.location["y"] + element.size["height"] // 2
        try:
            self._tap_point(center_x, center_y)
        except WebDriverException:
            element.click()

    def _tap_point(self, x: int, y: int) -> None:
        self._driver.execute_script("mobile: clickGesture", {"x": x, "y": y})

    def _hide_keyboard_if_present(self) -> None:
        try:
            if self._driver.is_keyboard_shown():
                self._driver.hide_keyboard()
        except WebDriverException:
            pass

    @staticmethod
    def _parse_budget(monthly_budget: int | str) -> int:
        try:
            parsed_budget = int(str(monthly_budget).replace(",", ""))
        except ValueError as exc:
            raise ValueError("Monthly budget must be a whole number.") from exc
        if parsed_budget <= 0:
            raise ValueError("Monthly budget must be greater than 0.")
        return parsed_budget
