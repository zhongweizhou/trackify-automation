"""Add Transaction page object for Trackify."""

from __future__ import annotations

import os

from selenium.common.exceptions import WebDriverException

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator


class AddTransactionPage(BasePage):
    """Page object for creating expense, income, and transfer transactions."""

    def __init__(
        self,
        driver: object,
        platform: str | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the Add Transaction page object.

        Args:
            driver: Active Appium WebDriver session.
            platform: Optional platform locator section to use.
            timeout: Default explicit wait timeout in seconds.
        """
        super().__init__(driver=driver, timeout=timeout)
        self._platform = (platform or os.getenv("PLATFORM", "android")).lower()
        self._keyboard_needs_blur = False

    def verify_visible(self) -> None:
        """Wait until the Add Transaction form is visible."""
        self.wait_for(self._loc("page_title"))
        self.wait_for(self._loc("amount_input"))
        self.wait_for(self._loc("save_button"))

    def add_expense(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> None:
        """Create an expense transaction.

        Args:
            amount: Transaction amount.
            category: Category name to select.
            note: Optional note text.
            tags: Optional comma-separated tags.
        """
        self._add_transaction("expense", amount, category, note, tags)

    def add_income(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> None:
        """Create an income transaction.

        Args:
            amount: Transaction amount.
            category: Category name to select.
            note: Optional note text.
            tags: Optional comma-separated tags.
        """
        self._add_transaction("income", amount, category, note, tags)

    def add_transfer(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> None:
        """Create a transfer transaction.

        Args:
            amount: Transaction amount.
            category: Category name to select.
            note: Optional note text.
            tags: Optional comma-separated tags.
        """
        self._add_transaction("transfer", amount, category, note, tags)

    def select_type(self, transaction_type: str) -> None:
        """Select the transaction type tab.

        Args:
            transaction_type: One of ``expense``, ``income``, or ``transfer``.
        """
        normalized_type = transaction_type.strip().lower()
        locator_key = f"type_toggle_{normalized_type}"
        self._tap_locator(self._loc(locator_key))

    def enter_amount(self, amount: int | float | str) -> None:
        """Enter the transaction amount.

        Args:
            amount: Transaction amount to type into the amount field.
        """
        self._input_text(self._loc("amount_input"), str(amount))

    def select_category(self, category: str) -> None:
        """Select an existing transaction category.

        Args:
            category: Visible category name to select.
        """
        self.wait_for(self._loc("category_label"))
        self._blur_keyboard_if_needed()
        self._tap_locator(self._loc("category_option", category=category))

    def enter_note(self, note: str) -> None:
        """Enter a note for the transaction.

        Args:
            note: Note text to type.
        """
        self._input_text(self._loc("notes_input"), note)

    def enter_tags(self, tags: str) -> None:
        """Enter comma-separated tags for the transaction.

        Args:
            tags: Tags text to type.
        """
        self._input_text(self._loc("tags_input"), tags)

    def tap_save(self) -> None:
        """Submit the Add Transaction form."""
        self._blur_keyboard_if_needed()
        self._tap_locator(self._loc("save_button"))

    def is_amount_error_visible(self) -> bool:
        """Return whether the amount validation error is visible.

        Returns:
            True when the amount validation error is visible, otherwise False.
        """
        return self.is_visible(self._loc("amount_error_message"), timeout=3)

    def _add_transaction(
        self,
        transaction_type: str,
        amount: int | float | str,
        category: str,
        note: str,
        tags: str,
    ) -> None:
        self.verify_visible()
        self.select_type(transaction_type)
        self.enter_amount(amount)
        self.select_category(category)
        if note:
            self.enter_note(note)
        if tags:
            self.enter_tags(tags)
        self.tap_save()

    def _loc(self, key: str, **format_values: str) -> Locator:
        strategy, value = load_locator("add_transaction", key, self._platform)
        if format_values:
            value = value.format(**format_values)
        return strategy, value

    def _tap_locator(self, locator: Locator) -> None:
        element = self.wait_for(locator)
        center_x = element.location["x"] + element.size["width"] // 2
        center_y = element.location["y"] + element.size["height"] // 2
        try:
            self._driver.execute_script(
                "mobile: clickGesture",
                {"x": center_x, "y": center_y},
            )
        except WebDriverException:
            self._driver.tap([(center_x, center_y)], 100)

    def _input_text(self, locator: Locator, text: str) -> None:
        self._tap_locator(locator)
        element = self.wait_for(locator)
        element.clear()
        element.send_keys(text)
        self._keyboard_needs_blur = True

    def _blur_keyboard_if_needed(self) -> None:
        if not self._keyboard_needs_blur:
            return
        self._tap_locator(self._loc("page_title"))
        self._keyboard_needs_blur = False
