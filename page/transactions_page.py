"""Page object for verifying the Trackify Transactions list."""

from __future__ import annotations

import os
from collections.abc import Callable

from selenium.webdriver.support.ui import WebDriverWait

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator


class TransactionsPage(BasePage):
    """Filter and inspect saved transactions grouped by date."""

    def __init__(
        self,
        driver: object,
        platform: str | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the Transactions page object.

        Args:
            driver: Active Appium WebDriver session.
            platform: Optional platform locator section to use.
            timeout: Default explicit wait timeout in seconds.
        """
        super().__init__(driver=driver, timeout=timeout)
        self._platform = (platform or os.getenv("PLATFORM", "android")).lower()

    def verify_visible(self) -> None:
        """Wait until the Transactions page is visible."""
        self.wait_for(self._loc("page_title"))

    def is_open(self) -> bool:
        """Return whether the Transactions page is currently open."""
        return self.is_visible(self._loc("page_title"), timeout=1)

    def select_type_filter(self, filter_name: str) -> None:
        """Select a transaction type filter.

        Args:
            filter_name: Visible filter name, such as ``Expense``.
        """
        self.verify_visible()
        self.click(self._loc("type_filter", filter_label=filter_name))

    def wait_for_transaction_rows(
        self,
        predicate: Callable[[tuple[str, ...]], bool],
        timeout: int | None = None,
    ) -> tuple[str, ...]:
        """Wait until visible transaction descriptions satisfy a predicate.

        This handles Flutter exposing a date group and its only row as one
        merged semantics node, while multiple rows are exposed separately.

        Args:
            predicate: Condition evaluated against all visible row descriptions.
            timeout: Optional wait timeout in seconds.

        Returns:
            Visible transaction accessibility descriptions.
        """
        locator = self._to_appium_locator(self._loc("transaction_rows"))
        wait_timeout = timeout if timeout is not None else self._timeout

        def matching_rows(driver: object) -> tuple[str, ...] | bool:
            descriptions = tuple(
                description
                for element in driver.find_elements(*locator)
                if (description := element.get_attribute("content-desc"))
            )
            if descriptions and predicate(descriptions):
                return descriptions
            return False

        return WebDriverWait(self._driver, wait_timeout).until(matching_rows)

    def date_section_description(self, date_label: str) -> str:
        """Return the accessibility description for one date section.

        Args:
            date_label: Visible date header, such as ``Today``.

        Returns:
            Date section description containing its header and summary amount.
        """
        description = self.wait_for(
            self._loc("date_section", date_label=date_label)
        ).get_attribute("content-desc")
        if not description:
            raise AssertionError(f"Date section {date_label!r} is empty.")
        return description

    def date_section_descriptions(self) -> tuple[str, ...]:
        """Return candidate descriptions containing date summaries or rows."""
        locator = self._to_appium_locator(self._loc("date_section_candidates"))

        def visible_descriptions(driver: object) -> tuple[str, ...] | bool:
            descriptions = tuple(
                description
                for element in driver.find_elements(*locator)
                if (description := element.get_attribute("content-desc"))
            )
            return descriptions or False

        return WebDriverWait(self._driver, self._timeout).until(
            visible_descriptions
        )

    def has_transaction(
        self,
        date_label: str,
        category: str,
        amount: str,
        time: str,
    ) -> bool:
        """Return whether one row matches all expected transaction details.

        Args:
            date_label: Expected date section label, such as ``Today``.
            category: Expected saved category name.
            amount: Expected formatted amount including type sign/symbol.
            time: Expected 12-hour time shown by the list.

        Returns:
            True only when one merged row contains all four values.
        """
        return self.is_visible(
            self._loc(
                "transaction_entry",
                date_label=date_label,
                category=category,
                amount=amount,
                time=time,
            ),
            timeout=3,
        )

    def has_no_transactions(self) -> bool:
        """Return whether the Transactions empty state is visible."""
        return self.is_visible(self._loc("empty_message"), timeout=3)

    def click_home(self) -> None:
        """Return to Home using the bottom navigation tab."""
        self.click(self._loc("home_tab_from_transactions"))

    def _loc(self, key: str, **format_values: str) -> Locator:
        strategy, value = load_locator("transactions", key, self._platform)
        if format_values:
            value = value.format(**format_values)
        return strategy, value
