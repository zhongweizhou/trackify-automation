"""Home page object for Trackify."""

from __future__ import annotations

import os

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator


class HomePage(BasePage):
    """Page object for the Home page and Add Transaction shortcuts."""

    def __init__(
        self,
        driver: object,
        platform: str | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the Home page object.

        Args:
            driver: Active Appium WebDriver session.
            platform: Optional platform locator section to use.
            timeout: Default explicit wait timeout in seconds.
        """
        super().__init__(driver=driver, timeout=timeout)
        self._platform = (platform or os.getenv("PLATFORM", "android")).lower()

    def verify_visible(self) -> None:
        """Wait until the Home page is visible."""
        self.wait_for(self._loc("home_tab"))
        self.wait_for(self._loc("recent_transactions_title"))

    def click_add_expense(self) -> None:
        """Open Add Transaction with Expense selected."""
        self.click(self._loc("add_expense_button"))

    def click_add_income(self) -> None:
        """Open Add Transaction with Income selected."""
        self.click(self._loc("add_income_button"))

    def click_add_transfer(self) -> None:
        """Open Add Transaction with Transfer selected."""
        self.click(self._loc("add_transfer_button"))

    def click_add_transaction(self) -> None:
        """Open Add Transaction from the floating action button."""
        self.click(self._loc("add_transaction_button"))

    def click_see_all_transactions(self) -> None:
        """Open the Transactions page from the Recent Transactions section."""
        self.click(self._loc("see_all_transactions_button"))

    def has_recent_transactions_section(self) -> bool:
        """Return whether the Recent Transactions section is visible.

        Returns:
            True when the section header is visible, otherwise False.
        """
        return self.is_visible(self._loc("recent_transactions_title"))

    def has_recent_transaction_amount(self, amount: str) -> bool:
        """Return whether a recent transaction contains the amount.

        Args:
            amount: Formatted amount substring to search for.

        Returns:
            True when a recent transaction row contains the amount.
        """
        return self.is_visible(self._loc("recent_transaction_amount", amount=amount))

    def has_recent_transaction_category(self, category: str) -> bool:
        """Return whether a recent transaction contains a category.

        Args:
            category: Category name expected in the recent transaction row.

        Returns:
            True when the category is visible, otherwise False.
        """
        return self.is_visible(
            self._loc("recent_transaction_category", category=category),
            timeout=3,
        )

    def has_empty_transactions_message(self) -> bool:
        """Return whether the empty Recent Transactions state is visible.

        Returns:
            True when the empty state is visible, otherwise False.
        """
        return self.is_visible(self._loc("empty_transactions_message"), timeout=3)

    def has_user_name(self, name: str) -> bool:
        """Return whether Home shows the configured user name.

        Args:
            name: Expected profile name.

        Returns:
            True when the greeting contains the name, otherwise False.
        """
        return self.is_visible(self._loc("user_name", name=name), timeout=3)

    def uses_currency_symbol(self, symbol: str) -> bool:
        """Return whether the Home summary uses the configured currency.

        Args:
            symbol: Expected currency symbol.

        Returns:
            True when the monthly summary contains the symbol, otherwise False.
        """
        return self.is_visible(
            self._loc("currency_summary", symbol=symbol), timeout=3
        )

    def _loc(self, key: str, **format_values: str) -> Locator:
        strategy, value = load_locator("home", key, self._platform)
        if format_values:
            value = value.format(**format_values)
        return strategy, value
