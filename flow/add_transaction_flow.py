"""Business flow for creating Trackify transactions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from page.add_transaction_page import AddTransactionPage
from page.home_page import HomePage

SUPPORTED_TRANSACTION_TYPES = frozenset({"expense", "income", "transfer"})


@dataclass(frozen=True)
class TransactionResult:
    """Result metadata for a transaction submitted through the UI.

    Attributes:
        transaction_id: Test-side correlation ID for the submitted transaction.
        transaction_type: Submitted transaction type.
        amount: Submitted positive transaction amount.
        category: Submitted category name.
    """

    transaction_id: str
    transaction_type: str
    amount: Decimal
    category: str


class AddTransactionFlow:
    """Business workflow for adding expense, income, and transfer records."""

    def __init__(
        self,
        home_page: HomePage,
        add_transaction_page: AddTransactionPage,
        transactions_page: object | None = None,
    ) -> None:
        """Initialize the flow with page objects injected by pytest fixtures.

        Args:
            home_page: Home page object.
            add_transaction_page: Add Transaction page object.
            transactions_page: Optional Transactions page object for later tasks.
        """
        self._home_page = home_page
        self._add_transaction_page = add_transaction_page
        self._transactions_page = transactions_page

    def add_expense(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> str:
        """Add an expense transaction through the Home shortcut.

        Args:
            amount: Positive transaction amount.
            category: Existing category name.
            note: Optional note text.
            tags: Optional comma-separated tags.

        Returns:
            Test-side correlation ID for the submitted transaction.
        """
        return self.add_transaction(
            "expense", amount, category, note, tags
        ).transaction_id

    def add_income(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> str:
        """Add an income transaction through the Home shortcut.

        Args:
            amount: Positive transaction amount.
            category: Existing category name.
            note: Optional note text.
            tags: Optional comma-separated tags.

        Returns:
            Test-side correlation ID for the submitted transaction.
        """
        return self.add_transaction(
            "income", amount, category, note, tags
        ).transaction_id

    def add_transfer(
        self,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> str:
        """Add a transfer transaction through the Home shortcut.

        Args:
            amount: Positive transaction amount.
            category: Existing category name.
            note: Optional note text.
            tags: Optional comma-separated tags.

        Returns:
            Test-side correlation ID for the submitted transaction.
        """
        return self.add_transaction(
            "transfer", amount, category, note, tags
        ).transaction_id

    def add_transaction(
        self,
        transaction_type: str,
        amount: int | float | str,
        category: str,
        note: str = "",
        tags: str = "",
    ) -> TransactionResult:
        """Add a transaction of any supported type.

        Args:
            transaction_type: One of ``expense``, ``income``, or ``transfer``.
            amount: Positive transaction amount.
            category: Existing category name.
            note: Optional note text.
            tags: Optional comma-separated tags.

        Returns:
            Metadata for the submitted transaction.

        Raises:
            ValueError: If the type, amount, or category is invalid.
        """
        normalized_type = self._validate_transaction_type(transaction_type)
        parsed_amount = self._validate_amount(amount)
        cleaned_category = self._validate_category(category)

        self._open_add_transaction(normalized_type)
        self._submit_transaction(
            normalized_type,
            parsed_amount,
            cleaned_category,
            note,
            tags,
        )

        return TransactionResult(
            transaction_id=self._new_transaction_id(normalized_type),
            transaction_type=normalized_type,
            amount=parsed_amount,
            category=cleaned_category,
        )

    def _open_add_transaction(self, transaction_type: str) -> None:
        self._home_page.verify_visible()
        if transaction_type == "expense":
            self._home_page.click_add_expense()
        elif transaction_type == "income":
            self._home_page.click_add_income()
        else:
            self._home_page.click_add_transfer()

    def _submit_transaction(
        self,
        transaction_type: str,
        amount: Decimal,
        category: str,
        note: str,
        tags: str,
    ) -> None:
        amount_text = str(amount)
        if transaction_type == "expense":
            self._add_transaction_page.add_expense(amount_text, category, note, tags)
        elif transaction_type == "income":
            self._add_transaction_page.add_income(amount_text, category, note, tags)
        else:
            self._add_transaction_page.add_transfer(amount_text, category, note, tags)

    def _validate_transaction_type(self, transaction_type: str) -> str:
        normalized_type = transaction_type.strip().lower()
        if normalized_type not in SUPPORTED_TRANSACTION_TYPES:
            supported = ", ".join(sorted(SUPPORTED_TRANSACTION_TYPES))
            raise ValueError(
                f"Unsupported transaction type '{transaction_type}'. "
                f"Use one of: {supported}"
            )
        return normalized_type

    def _validate_amount(self, amount: int | float | str) -> Decimal:
        try:
            parsed_amount = Decimal(str(amount))
        except InvalidOperation as exc:
            raise ValueError("Amount must be numeric.") from exc

        if parsed_amount <= 0:
            raise ValueError("Amount must be greater than 0.")
        return parsed_amount

    def _validate_category(self, category: str) -> str:
        cleaned_category = category.strip()
        if not cleaned_category:
            raise ValueError("Category is required.")
        return cleaned_category

    def _new_transaction_id(self, transaction_type: str) -> str:
        return f"{transaction_type}-{uuid4().hex}"
