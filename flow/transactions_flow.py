"""Business flow for filtering and verifying Trackify transactions."""

from __future__ import annotations

import re

from page.transactions_page import TransactionsPage

SUPPORTED_TRANSACTION_FILTERS = frozenset({"expense", "income", "transfer"})
TRANSACTION_TYPE_MARKERS = {
    "expense": "-$",
    "income": "+$",
    "transfer": "\u2194 $",
}
DATE_SECTION_PATTERN = re.compile(r"^(?:Today|Yesterday|\d{2} [A-Z][a-z]{2} \d{4})$")


class TransactionsFlow:
    """Orchestrate Transactions filters and list-level assertions."""

    def __init__(self, transactions_page: TransactionsPage) -> None:
        """Initialize the flow with an injected Transactions page.

        Args:
            transactions_page: Transactions page object.
        """
        self._transactions_page = transactions_page

    def ensure_transactions_page(self) -> None:
        """Verify that the Transactions page and filter bar are ready."""
        self._transactions_page.verify_visible()

    def filter_by_type(self, transaction_type: str) -> None:
        """Apply an Expense, Income, or Transfer filter.

        Args:
            transaction_type: Supported transaction type.
        """
        normalized_type = self._validate_transaction_type(transaction_type)
        self._transactions_page.select_type_filter(normalized_type.title())

    def assert_only_transaction_type(self, transaction_type: str) -> None:
        """Assert every visible row has the expected transaction type.

        Args:
            transaction_type: Expected visible transaction type.

        Raises:
            AssertionError: If no matching row appears before the UI timeout.
        """
        normalized_type = self._validate_transaction_type(transaction_type)
        expected_marker = TRANSACTION_TYPE_MARKERS[normalized_type]
        descriptions = self._transactions_page.wait_for_transaction_rows(
            lambda rows: all(expected_marker in row for row in rows)
        )
        assert descriptions, (
            f"No {normalized_type} transactions were visible after filtering."
        )

        unexpected_markers = {
            marker
            for row_type, marker in TRANSACTION_TYPE_MARKERS.items()
            if row_type != normalized_type
        }
        assert all(
            marker not in row
            for row in descriptions
            for marker in unexpected_markers
        ), (
            f"Transactions filter {normalized_type!r} showed another type: "
            f"{descriptions!r}."
        )

    def assert_grouped_by_date(self, date_label: str | None = None) -> None:
        """Assert visible transactions are presented under a date summary.

        Args:
            date_label: Optional exact date header for the test transactions.

        Raises:
            AssertionError: If the date header or section amount is malformed.
        """
        cleaned_date_label = date_label.strip() if date_label is not None else None
        if date_label is not None and not cleaned_date_label:
            raise ValueError("Date label cannot be empty.")

        sections = tuple(
            description
            for description in self._transactions_page.date_section_descriptions()
            if self._is_date_section(description, cleaned_date_label)
        )
        assert sections, (
            f"No transaction date section matched {cleaned_date_label!r}."
        )

        for description in sections:
            lines = self._description_lines(description)
            assert lines[1].startswith("$"), (
                f"Date section {lines[0]!r} has invalid summary {lines[1]!r}."
            )
        self._transactions_page.wait_for_transaction_rows(lambda rows: bool(rows))

    @staticmethod
    def _is_date_section(description: str, date_label: str | None) -> bool:
        lines = TransactionsFlow._description_lines(description)
        if len(lines) < 2 or not DATE_SECTION_PATTERN.fullmatch(lines[0]):
            return False
        return date_label is None or lines[0] == date_label

    @staticmethod
    def _description_lines(description: str) -> tuple[str, ...]:
        return tuple(line.strip() for line in description.splitlines() if line.strip())

    @staticmethod
    def _validate_transaction_type(transaction_type: str) -> str:
        normalized_type = transaction_type.strip().lower()
        if normalized_type not in SUPPORTED_TRANSACTION_FILTERS:
            supported = ", ".join(sorted(SUPPORTED_TRANSACTION_FILTERS))
            raise ValueError(
                f"Unsupported transaction filter {transaction_type!r}. "
                f"Use one of: {supported}."
            )
        return normalized_type
