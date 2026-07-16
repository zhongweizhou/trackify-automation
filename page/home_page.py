"""Home page object for Trackify."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.support.ui import WebDriverWait

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator

_MONTHLY_SUMMARY_PATTERN = re.compile(
    r"This Month\s*\n"
    r"(?P<balance>\$-?[\d,.]+)\s*\n"
    r"Income\s*\n(?P<income>\$[\d,.]+)\s*\n"
    r"Expense\s*\n(?P<expense>\$[\d,.]+)\s*\n"
    r"(?P<percent>\d+)%"
)


@dataclass(frozen=True)
class MonthlySummary:
    """Numeric values displayed by the Home This Month panel."""

    balance: Decimal
    income: Decimal
    expense: Decimal
    percent: int


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

    def monthly_summary(self) -> MonthlySummary:
        """Parse and return all values from the This Month panel.

        Raises:
            AssertionError: If the panel's accessibility text is unexpected.
        """
        attribute = "label" if self._platform == "ios" else "content-desc"
        description = self.wait_for(self._loc("monthly_summary")).get_attribute(
            attribute
        )
        match = _MONTHLY_SUMMARY_PATTERN.search(description or "")
        if not match:
            raise AssertionError(
                f"Could not parse This Month summary from {description!r}."
            )
        return MonthlySummary(
            balance=self._parse_usd(match.group("balance")),
            income=self._parse_usd(match.group("income")),
            expense=self._parse_usd(match.group("expense")),
            percent=int(match.group("percent")),
        )

    def wait_for_monthly_summary(
        self, expected: MonthlySummary, timeout: int | None = None
    ) -> MonthlySummary:
        """Wait for the animated This Month values to reach their final state."""
        wait_timeout = timeout if timeout is not None else self._timeout
        return WebDriverWait(self._driver, wait_timeout).until(
            lambda _: (
                summary
                if (summary := self.monthly_summary()) == expected
                else False
            )
        )

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
        if self._platform == "ios":
            return not self.is_visible(self._loc("recent_transaction_rows"), timeout=1)
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

    @staticmethod
    def _parse_usd(value: str) -> Decimal:
        return Decimal(value.replace("$", "").replace(",", ""))
