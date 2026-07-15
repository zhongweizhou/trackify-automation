"""Step definitions for Add Transaction BDD scenarios."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from flow.add_transaction_flow import AddTransactionFlow

scenarios("../features/add_transaction.feature")


@when(parsers.parse('user selects type "{transaction_type}"'))
def user_selects_type(
    add_transaction_flow: AddTransactionFlow,
    transaction_type: str,
) -> None:
    """Select a transaction type on the open form.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        transaction_type: Type from the Gherkin step.
    """
    add_transaction_flow.select_type(transaction_type)


@when("user leaves amount empty")
def user_leaves_amount_empty(
    add_transaction_flow: AddTransactionFlow,
) -> None:
    """Keep the transaction amount empty.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.leave_amount_empty()


@when(parsers.parse('user creates custom category "{name}"'))
def user_creates_custom_category(
    add_transaction_flow: AddTransactionFlow,
    name: str,
) -> None:
    """Create a custom category and select it on the transaction form.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        name: New category name from the Gherkin step.
    """
    add_transaction_flow.create_custom_category(name)


@then(
    parsers.parse('transaction appears in Recent transactions with amount "{amount}"')
)
def transaction_appears_with_amount(
    add_transaction_flow: AddTransactionFlow,
    amount: str,
) -> None:
    """Assert the submitted amount appears in Recent Transactions.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        amount: Expected amount from the Gherkin step.
    """
    add_transaction_flow.assert_recent_transaction_amount(amount)


@then(parsers.parse('error message "{message}" is shown for amount'))
def amount_error_is_shown(
    add_transaction_flow: AddTransactionFlow,
    message: str,
) -> None:
    """Assert that empty-amount validation rejected the form.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        message: Expected validation copy from the Gherkin step.
    """
    add_transaction_flow.assert_amount_error(message)


@then("no transaction appears in Recent transactions")
def no_transaction_appears(
    add_transaction_flow: AddTransactionFlow,
) -> None:
    """Assert that no transaction was saved.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.assert_no_recent_transactions()


@then(
    parsers.parse(
        'no transaction appears in Recent transactions with category '
        '"{category}" missing'
    )
)
def transaction_category_is_not_missing(
    add_transaction_flow: AddTransactionFlow,
    category: str,
) -> None:
    """Assert that the recent transaction shows its custom category.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        category: Expected custom category.
    """
    add_transaction_flow.assert_recent_transaction_category(category)


@then(
    "Transactions shows the saved transaction with matching date, amount, "
    "category, and time"
)
def transactions_shows_saved_transaction(
    add_transaction_flow: AddTransactionFlow,
) -> None:
    """Verify all required values in one Transactions list row.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.assert_saved_transaction_details()


@then("Transactions contains no transactions")
def transactions_contains_no_transactions(
    add_transaction_flow: AddTransactionFlow,
) -> None:
    """Verify that an invalid submission did not create a list row.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.assert_transactions_empty()


@then(parsers.parse('This Month summary is correct for budget "{budget}"'))
def this_month_summary_is_correct(
    add_transaction_flow: AddTransactionFlow,
    budget: str,
) -> None:
    """Verify balance, income, expense, and rounded percentage.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        budget: Configured monthly budget from the Gherkin step.
    """
    add_transaction_flow.assert_monthly_summary(budget)
