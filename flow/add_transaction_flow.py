"""Business flow for creating Trackify transactions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from uuid import uuid4

from page.add_transaction_page import AddTransactionPage
from page.home_page import HomePage, MonthlySummary
from page.transactions_page import TransactionsPage

SUPPORTED_TRANSACTION_TYPES = frozenset({"expense", "income", "transfer"})
CATEGORY_DISPLAY_NAMES = {
    "Food": "Food & Dining",
    "Bills": "Bills & Utilities",
}
TRANSACTION_DATE_TIME_FORMATS = (
    "%Y%m%d %I:%M %p",
    "%Y-%m-%d %I:%M %p",
)


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


@dataclass(frozen=True)
class SavedTransactionExpectation:
    """UI values captured before a transaction is submitted."""

    transaction_type: str
    amount: Decimal
    category: str
    selected_at: datetime


class AddTransactionFlow:
    """Business workflow for adding expense, income, and transfer records."""

    def __init__(
        self,
        home_page: HomePage,
        add_transaction_page: AddTransactionPage,
        transactions_page: TransactionsPage | None = None,
    ) -> None:
        """Initialize the flow with page objects injected by pytest fixtures.

        Args:
            home_page: Home page object.
            add_transaction_page: Add Transaction page object.
            transactions_page: Optional Transactions page for list assertions.
        """
        self._home_page = home_page
        self._add_transaction_page = add_transaction_page
        self._transactions_page = transactions_page
        self._baseline_summary: MonthlySummary | None = None
        self._draft_type: str | None = None
        self._draft_amount: Decimal | None = None
        self._draft_category: str | None = None
        self._saved_transaction: SavedTransactionExpectation | None = None

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

    def ensure_home_page(self) -> None:
        """Verify the preconfigured Home page is visible."""
        self._home_page.verify_visible()
        self._baseline_summary = self._home_page.monthly_summary()

    def tap_add_shortcut(self, shortcut_name: str) -> None:
        """Tap a Home shortcut that opens the Add Transaction form.

        Args:
            shortcut_name: One of ``Add Expense``, ``Add Income``, or
                ``Add Transfer``; ``Add new category`` is supported while the
                Add Transaction form is open.

        Raises:
            ValueError: If the shortcut name is unsupported.
        """
        normalized_name = shortcut_name.strip().lower()
        if normalized_name == "add expense":
            self._home_page.click_add_expense()
            self._add_transaction_page.select_type("expense")
            self._begin_draft("expense")
        elif normalized_name == "add income":
            self._home_page.click_add_income()
            self._add_transaction_page.select_type("income")
            self._begin_draft("income")
        elif normalized_name == "add transfer":
            self._home_page.click_add_transfer()
            self._add_transaction_page.select_type("transfer")
            self._begin_draft("transfer")
        elif normalized_name == "add new category":
            self._add_transaction_page.tap_add_new_category()
        else:
            raise ValueError(f"Unsupported Add Transaction shortcut: {shortcut_name}")

    def select_type(self, transaction_type: str) -> None:
        """Select a transaction type on the open form.

        Args:
            transaction_type: Supported transaction type.
        """
        normalized_type = self._validate_transaction_type(transaction_type)
        self._add_transaction_page.select_type(normalized_type)
        self._draft_type = normalized_type

    def enter_amount(self, amount: int | float | str) -> None:
        """Enter the amount on the Add Transaction form.

        Args:
            amount: Positive transaction amount.
        """
        parsed_amount = self._validate_amount(amount)
        self._add_transaction_page.enter_amount(str(parsed_amount))
        self._draft_amount = parsed_amount

    def leave_amount_empty(self) -> None:
        """Leave the Add Transaction amount field empty."""
        self._add_transaction_page.leave_amount_empty()
        self._draft_amount = None

    def select_category(self, category: str) -> None:
        """Select a category on the Add Transaction form.

        Args:
            category: Existing category name.
        """
        cleaned_category = self._validate_category(category)
        self._add_transaction_page.select_category(cleaned_category)
        self._draft_category = cleaned_category

    def enter_note(self, note: str) -> None:
        """Enter a note on the Add Transaction form.

        Args:
            note: Note text.
        """
        self._add_transaction_page.enter_note(note)

    def enter_tags(self, tags: str) -> None:
        """Enter comma-separated transaction tags.

        Args:
            tags: Tags text such as ``food,breakfast``.
        """
        cleaned_tags = tags.strip()
        if not cleaned_tags:
            raise ValueError("Tags cannot be empty.")
        self._add_transaction_page.enter_tags(cleaned_tags)

    def select_date_time(self, value: str) -> None:
        """Select an explicit transaction date and time.

        Args:
            value: Date/time such as ``20250506 9:00 AM``.
        """
        self._add_transaction_page.select_date_time(
            self._parse_transaction_date_time(value)
        )

    def create_custom_category(self, name: str) -> None:
        """Create and select a custom expense category.

        Args:
            name: Custom category name.
        """
        cleaned_name = self._validate_category(name)
        self._add_transaction_page.create_custom_category(cleaned_name)
        self._draft_category = cleaned_name

    def tap_save(self) -> None:
        """Submit the Add Transaction form."""
        expectation = self._build_saved_expectation()
        self._add_transaction_page.tap_save()
        self._saved_transaction = expectation

    def assert_amount_error(self, message: str) -> None:
        """Assert that an empty amount was rejected.

        Args:
            message: Expected validation copy when exposed by the app.

        Raises:
            AssertionError: If the save was not rejected.
        """
        assert self._add_transaction_page.is_amount_error_visible(message), (
            f"Amount validation did not reject the form with message {message!r}."
        )

    def assert_recent_transaction_amount(self, amount: int | float | str) -> None:
        """Assert that Recent Transactions contains the submitted amount.

        Args:
            amount: Amount expected in the recent transaction row.

        Raises:
            AssertionError: If the formatted amount is not visible.
        """
        self._home_page.verify_visible()
        formatted_amount = self._format_recent_amount(self._validate_amount(amount))
        assert self._home_page.has_recent_transaction_amount(formatted_amount), (
            f"Recent Transactions did not show amount {formatted_amount}"
        )

    def assert_no_recent_transactions(self) -> None:
        """Assert that Recent Transactions is empty.

        Raises:
            AssertionError: If the empty state is not visible.
        """
        if self._add_transaction_page.is_open():
            self._add_transaction_page.close()
        self._home_page.verify_visible()
        assert self._home_page.has_empty_transactions_message(), (
            "Recent Transactions was expected to be empty."
        )

    def assert_recent_transaction_category(self, category: str) -> None:
        """Assert that Recent Transactions shows a category.

        Args:
            category: Expected category name.

        Raises:
            AssertionError: If the category is missing.
        """
        cleaned_category = self._validate_category(category)
        self._home_page.verify_visible()
        assert self._home_page.has_recent_transaction_category(cleaned_category), (
            f"Recent Transactions did not show category {cleaned_category!r}."
        )

    def assert_saved_transaction_details(self) -> None:
        """Assert date, amount, category, and time on Transactions."""
        expectation = self._require_saved_transaction()
        transactions_page = self._require_transactions_page()
        self._open_transactions()

        category = CATEGORY_DISPLAY_NAMES.get(
            expectation.category,
            expectation.category,
        )
        amount = self._format_list_amount(
            expectation.transaction_type,
            expectation.amount,
        )
        time = expectation.selected_at.strftime("%I:%M %p").lstrip("0")
        date_label = self._format_list_date(expectation.selected_at)
        assert transactions_page.has_transaction(
            date_label=date_label,
            category=category,
            amount=amount,
            time=time,
        ), (
            "Transactions did not show one matching row: "
            f"date={date_label!r}, category={category!r}, amount={amount!r}, "
            f"time={time!r}."
        )

    def assert_transactions_empty(self) -> None:
        """Assert that the Transactions page contains no rows."""
        transactions_page = self._require_transactions_page()
        self._open_transactions()
        assert transactions_page.has_no_transactions(), (
            "Transactions page was expected to be empty."
        )

    def assert_monthly_summary(self, budget: int | float | str) -> None:
        """Assert This Month values using transaction and budget rules.

        Args:
            budget: Positive configured monthly budget.

        Raises:
            AssertionError: If any displayed summary value is incorrect.
        """
        parsed_budget = self._validate_amount(budget)
        baseline = self._require_baseline_summary()
        income = baseline.income
        expense = baseline.expense

        if self._is_in_current_month(self._saved_transaction):
            assert self._saved_transaction is not None
            if self._saved_transaction.transaction_type == "income":
                income += self._saved_transaction.amount
            elif self._saved_transaction.transaction_type == "expense":
                expense += self._saved_transaction.amount

        expected = MonthlySummary(
            balance=income - expense,
            income=income,
            expense=expense,
            percent=int(
                (expense / parsed_budget * Decimal("100")).to_integral_value(
                    rounding=ROUND_HALF_UP
                )
            ),
        )
        self._return_to_home()
        actual = self._home_page.monthly_summary()
        assert actual == expected, (
            "This Month summary mismatch. "
            f"Expected {expected}, displayed {actual}; percentage formula is "
            "expense / budget * 100 rounded to the nearest integer, half up."
        )

    def _open_add_transaction(self, transaction_type: str) -> None:
        self._home_page.verify_visible()
        if transaction_type == "expense":
            self._home_page.click_add_expense()
        elif transaction_type == "income":
            self._home_page.click_add_income()
        else:
            self._home_page.click_add_transfer()

    def _begin_draft(self, transaction_type: str) -> None:
        self._draft_type = transaction_type
        self._draft_amount = None
        self._draft_category = None
        self._saved_transaction = None

    def _build_saved_expectation(self) -> SavedTransactionExpectation | None:
        if (
            self._draft_type is None
            or self._draft_amount is None
            or self._draft_category is None
        ):
            return None
        selected_date_time = " ".join(
            self._add_transaction_page.selected_date_time().split()
        )
        return SavedTransactionExpectation(
            transaction_type=self._draft_type,
            amount=self._draft_amount,
            category=self._draft_category,
            selected_at=datetime.strptime(
                selected_date_time,
                "%d/%m/%Y %H:%M",
            ),
        )

    def _open_transactions(self) -> None:
        transactions_page = self._require_transactions_page()
        if transactions_page.is_open():
            return
        self._home_page.verify_visible()
        self._home_page.click_see_all_transactions()
        transactions_page.verify_visible()

    def _return_to_home(self) -> None:
        if self._transactions_page is not None and self._transactions_page.is_open():
            self._transactions_page.click_home()

    def _require_transactions_page(self) -> TransactionsPage:
        if self._transactions_page is None:
            raise AssertionError("TransactionsPage was not injected into the flow.")
        return self._transactions_page

    def _require_saved_transaction(self) -> SavedTransactionExpectation:
        if self._saved_transaction is None:
            raise AssertionError("No successfully submitted transaction was captured.")
        return self._saved_transaction

    def _require_baseline_summary(self) -> MonthlySummary:
        if self._baseline_summary is None:
            raise AssertionError("Home baseline summary was not captured.")
        return self._baseline_summary

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

    def _parse_transaction_date_time(self, value: str) -> datetime:
        cleaned_value = " ".join(value.strip().upper().split())
        for date_time_format in TRANSACTION_DATE_TIME_FORMATS:
            try:
                return datetime.strptime(cleaned_value, date_time_format)
            except ValueError:
                continue
        raise ValueError(
            f"Unsupported transaction date/time {value!r}. "
            "Use YYYYMMDD h:mm AM/PM."
        )

    def _new_transaction_id(self, transaction_type: str) -> str:
        return f"{transaction_type}-{uuid4().hex}"

    def _format_recent_amount(self, amount: Decimal) -> str:
        return f"{amount:,.2f}"

    def _format_list_amount(
        self,
        transaction_type: str,
        amount: Decimal,
    ) -> str:
        formatted = self._format_recent_amount(amount)
        if transaction_type == "expense":
            return f"-${formatted}"
        if transaction_type == "income":
            return f"+${formatted}"
        return f"\u2194 ${formatted}"

    @staticmethod
    def _format_list_date(selected_at: datetime) -> str:
        selected_date = selected_at.date()
        today = date.today()
        if selected_date == today:
            return "Today"
        if selected_date == today - timedelta(days=1):
            return "Yesterday"
        return selected_at.strftime("%d %b %Y")

    @staticmethod
    def _is_in_current_month(
        transaction: SavedTransactionExpectation | None,
    ) -> bool:
        if transaction is None:
            return False
        now = datetime.now()
        return (
            transaction.selected_at.year == now.year
            and transaction.selected_at.month == now.month
        )
