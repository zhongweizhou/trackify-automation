"""Add Transaction page object for Trackify."""

from __future__ import annotations

import os
from calendar import month_name
from datetime import datetime

from selenium.common.exceptions import TimeoutException, WebDriverException

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
        self._amount_left_empty = False
        self._save_attempted = False

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
        self._complete_keyboard_input()
        self._amount_left_empty = False

    def leave_amount_empty(self) -> None:
        """Ensure the amount field has no entered value."""
        amount_input = self.wait_for(self._loc("amount_input"))
        if amount_input.get_attribute("text"):
            amount_input.clear()
        self._amount_left_empty = True

    def select_category(self, category: str) -> None:
        """Select an existing transaction category.

        Args:
            category: Visible category name to select.
        """
        self.wait_for(self._loc("category_label"))
        self._blur_keyboard_if_needed()
        category_locator = self._loc("category_option", category=category)
        self._scroll_category_into_view(category_locator)
        self._tap_locator(category_locator)

    def tap_add_new_category(self) -> None:
        """Swipe to the New category tile and open the creation form."""
        self._blur_keyboard_if_needed()
        new_category_locator = self._loc("new_category_button")
        self._scroll_category_into_view(new_category_locator)
        self._tap_locator(new_category_locator)
        self.wait_for(self._loc("manage_categories_title"))
        self._tap_locator(self._loc("add_category_button"))
        self.wait_for(self._loc("new_category_title"))

    def create_custom_category(self, name: str) -> None:
        """Create a category with default icon/color and select it.

        Args:
            name: Custom category name.
        """
        self._tap_locator(self._loc("custom_category_name_input"))
        name_input = self.wait_for(self._loc("custom_category_name_input"))
        name_input.clear()
        name_input.send_keys(name)
        self._complete_keyboard_input()
        entered_name = self.wait_for(
            self._loc("custom_category_name_input")
        ).get_attribute("text")
        if entered_name != name:
            raise AssertionError(
                f"Custom category input contains {entered_name!r}, expected {name!r}."
            )
        self._tap_locator(self._loc("new_category_title"))
        self._keyboard_needs_blur = False
        self._tap_locator(self._loc("create_category_button"))
        self.wait_for(self._loc("manage_categories_title"))
        self._tap_locator(self._loc("back_from_categories_button"))
        self.verify_visible()
        self._select_custom_category(name)

    def enter_note(self, note: str) -> None:
        """Enter a note for the transaction.

        Args:
            note: Note text to type.
        """
        self._input_text(self._loc("notes_input"), note)
        self._complete_keyboard_input()

    def enter_tags(self, tags: str) -> None:
        """Enter comma-separated tags for the transaction.

        Args:
            tags: Tags text to type.
        """
        self._input_text(self._loc("tags_input"), tags)
        self._complete_keyboard_input()

    def selected_date_time(self) -> str:
        """Return the date and time currently selected on the form."""
        value = self.wait_for(self._loc("date_picker_trigger")).get_attribute(
            "content-desc"
        )
        if not value:
            raise AssertionError("Add Transaction date/time is empty.")
        return value

    def select_date_time(self, selected_at: datetime) -> None:
        """Set an exact transaction date and time through the native pickers.

        Args:
            selected_at: Target local date and time, precise to the minute.

        Raises:
            AssertionError: If the form does not retain the selected value.
        """
        target = selected_at.replace(second=0, microsecond=0)
        current = datetime.strptime(
            " ".join(self.selected_date_time().split()),
            "%d/%m/%Y %H:%M",
        )
        self._blur_keyboard_if_needed()
        self._tap_locator(self._loc("date_picker_trigger"))
        self.wait_for(self._loc("date_dialog"))
        self._select_calendar_date(current, target)
        self._select_clock_time(target)

        actual = datetime.strptime(
            " ".join(self.selected_date_time().split()),
            "%d/%m/%Y %H:%M",
        )
        if actual != target:
            raise AssertionError(
                f"Date/time picker retained {actual!s}, expected {target!s}."
            )
        self.wait_for(self._loc("save_button"))

    def tap_save(self) -> None:
        """Submit the Add Transaction form."""
        self._blur_keyboard_if_needed()
        self._tap_locator(self._loc("save_button"))
        self._save_attempted = True

    def is_amount_error_visible(self, message: str) -> bool:
        """Return whether empty-amount validation rejected the save.

        The current Android build silently keeps the invalid form open instead
        of exposing its validation copy to accessibility. A visible message is
        preferred; the fallback verifies the attempted form remains open with
        an empty amount.

        Args:
            message: Expected validation message.

        Returns:
            True when the amount validation error is visible, otherwise False.
        """
        if self.is_visible(
            self._loc("amount_error_message", message=message), timeout=1
        ):
            return True
        if not self._amount_left_empty or not self._save_attempted:
            return False
        if not self.is_open():
            return False
        amount_text = self.wait_for(self._loc("amount_input")).get_attribute("text")
        return not amount_text

    def is_open(self) -> bool:
        """Return whether the Add Transaction form is currently open."""
        return self.is_visible(self._loc("page_title"), timeout=1)

    def close(self) -> None:
        """Close Add Transaction without saving."""
        self._blur_keyboard_if_needed()
        self._tap_locator(self._loc("close_button"))

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

    def _scroll_category_into_view(self, locator: Locator) -> None:
        for _ in range(4):
            if self.is_visible(locator, timeout=1):
                return

            category_scroll = self.wait_for(self._loc("category_scroll"))
            start_x = (
                category_scroll.location["x"]
                + category_scroll.size["width"] * 9 // 10
            )
            end_x = (
                category_scroll.location["x"]
                + category_scroll.size["width"] // 10
            )
            center_y = (
                category_scroll.location["y"]
                + category_scroll.size["height"] // 2
            )
            self.swipe(start_x, center_y, end_x, center_y, duration_ms=600)

        self.wait_for(locator, timeout=2)

    def _select_custom_category(self, name: str) -> None:
        category_locator = self._loc("category_option", category=name)
        try:
            self._scroll_category_into_view(category_locator)
        except TimeoutException:
            visible_label = name.split(maxsplit=1)[0]
            if visible_label == name:
                raise
            category_locator = self._loc(
                "category_option", category=visible_label
            )
            self._scroll_category_into_view(category_locator)
        self._tap_locator(category_locator)

    def _select_calendar_date(self, current: datetime, target: datetime) -> None:
        current_month_year = self._month_year(current.month, current.year)
        if current.year != target.year:
            self._tap_locator(
                self._loc("select_year_button", month_year=current_month_year)
            )
            self._tap_locator(self._loc("year_option", year=str(target.year)))
            current_month_year = self._month_year(current.month, target.year)
            self.wait_for(
                self._loc("select_year_button", month_year=current_month_year)
            )

        month_delta = target.month - current.month
        month_locator_key = (
            "next_month_button" if month_delta > 0 else "previous_month_button"
        )
        direction = 1 if month_delta > 0 else -1
        for step in range(abs(month_delta)):
            self._tap_locator(self._loc(month_locator_key))
            displayed_month = current.month + direction * (step + 1)
            self.wait_for(
                self._loc(
                    "select_year_button",
                    month_year=self._month_year(displayed_month, target.year),
                )
            )

        day_label = (
            f"{target.day}, {target.strftime('%A, %B')} "
            f"{target.day}, {target.year}"
        )
        self._tap_locator(self._loc("day_option", day_label=day_label))
        self._tap_locator(self._loc("dialog_ok_button"))
        self.wait_for(self._loc("time_text_mode_button"))

    def _select_clock_time(self, target: datetime) -> None:
        self._tap_locator(self._loc("time_text_mode_button"))
        hour = target.strftime("%I").lstrip("0")
        self._replace_time_value(self._loc("time_hour_input"), hour)
        self._replace_time_value(
            self._loc("time_minute_input"),
            target.strftime("%M"),
        )
        self._tap_locator(
            self._loc("time_meridiem_option", meridiem=target.strftime("%p"))
        )
        self._tap_locator(self._loc("dialog_ok_button"))

    def _replace_time_value(self, locator: Locator, value: str) -> None:
        element = self.wait_for(locator)
        element.click()
        if self._platform == "android":
            element.clear()
            element.send_keys(value)
            self._driver.execute_script(
                "mobile: performEditorAction",
                {"action": "done"},
            )
            updated_value = self.wait_for(locator).get_attribute("text")
            if updated_value != value:
                raise AssertionError(
                    f"Time field contains {updated_value!r}, expected {value!r}."
                )
            return
        element.clear()
        element.send_keys(value)

    def _complete_keyboard_input(self) -> None:
        if self._platform != "android":
            return
        self._driver.execute_script(
            "mobile: performEditorAction",
            {"action": "done"},
        )
        self._keyboard_needs_blur = False

    @staticmethod
    def _month_year(month: int, year: int) -> str:
        return f"{month_name[month]} {year}"

    def _blur_keyboard_if_needed(self) -> None:
        if not self._keyboard_needs_blur:
            return
        self._tap_locator(self._loc("page_title"))
        self._keyboard_needs_blur = False
