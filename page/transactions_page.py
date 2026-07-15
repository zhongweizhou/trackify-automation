"""Page object for verifying the Trackify Transactions list."""

from __future__ import annotations

import os

from page.base_page import BasePage
from utils.locator_loader import Locator, load_locator


class TransactionsPage(BasePage):
    """Inspect saved transaction rows and navigate back to Home."""

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
