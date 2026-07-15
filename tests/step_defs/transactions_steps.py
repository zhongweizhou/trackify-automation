"""Step definitions for Transactions list BDD scenarios."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from flow.transactions_flow import TransactionsFlow
from page.home_page import HomePage

scenarios("../features/transactions.feature")


@when("user navigates to the Transactions page")
def user_navigates_to_transactions(
    home_page: HomePage,
    transactions_flow: TransactionsFlow,
) -> None:
    """Open Transactions from the Home recent-transactions section.

    Args:
        home_page: Home page fixture.
        transactions_flow: Transactions business flow fixture.
    """
    home_page.verify_visible()
    home_page.click_see_all_transactions()
    transactions_flow.ensure_transactions_page()


@when(parsers.parse('user filters transactions by type "{transaction_type}"'))
def user_filters_transactions(
    transactions_flow: TransactionsFlow,
    transaction_type: str,
) -> None:
    """Apply a transaction type filter.

    Args:
        transactions_flow: Transactions business flow fixture.
        transaction_type: Type supplied by the Gherkin scenario.
    """
    transactions_flow.filter_by_type(transaction_type)


@then(parsers.parse('only transactions of type "{transaction_type}" are shown'))
def only_transaction_type_is_shown(
    transactions_flow: TransactionsFlow,
    transaction_type: str,
) -> None:
    """Assert the filter excludes every other transaction type.

    Args:
        transactions_flow: Transactions business flow fixture.
        transaction_type: Expected visible transaction type.
    """
    transactions_flow.assert_only_transaction_type(transaction_type)


@then("transactions are grouped by date with section headers")
def transactions_are_grouped_by_date(
    transactions_flow: TransactionsFlow,
) -> None:
    """Assert Transactions exposes valid date summary sections.

    Args:
        transactions_flow: Transactions business flow fixture.
    """
    transactions_flow.assert_grouped_by_date()
