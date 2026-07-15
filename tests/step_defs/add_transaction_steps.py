"""Step definitions for Add Transaction BDD scenarios."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from flow.add_transaction_flow import AddTransactionFlow

scenarios("../features/add_transaction.feature")


@given("app is launched with a clean database")
def app_launched_with_clean_database() -> None:
    """Document the clean app state provided by the autouse reset fixture."""


@given("user is on the Home page")
def user_is_on_home_page(add_transaction_flow: AddTransactionFlow) -> None:
    """Verify the Home page is ready for the scenario.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.ensure_home_page()


@when(parsers.parse('user taps "{shortcut_name}"'))
def user_taps_shortcut(
    add_transaction_flow: AddTransactionFlow,
    shortcut_name: str,
) -> None:
    """Tap an Add Transaction shortcut.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        shortcut_name: Shortcut visible name from the Gherkin step.
    """
    add_transaction_flow.tap_add_shortcut(shortcut_name)


@when(parsers.parse('user enters amount "{amount}"'))
def user_enters_amount(
    add_transaction_flow: AddTransactionFlow,
    amount: str,
) -> None:
    """Enter the transaction amount.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        amount: Amount from the Gherkin step.
    """
    add_transaction_flow.enter_amount(amount)


@when(parsers.parse('user selects category "{category}"'))
def user_selects_category(
    add_transaction_flow: AddTransactionFlow,
    category: str,
) -> None:
    """Select the transaction category.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        category: Category from the Gherkin step.
    """
    add_transaction_flow.select_category(category)


@when(parsers.parse('user enters note "{note}"'))
def user_enters_note(
    add_transaction_flow: AddTransactionFlow,
    note: str,
) -> None:
    """Enter the transaction note.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        note: Note from the Gherkin step.
    """
    add_transaction_flow.enter_note(note)


@when("user taps Save")
def user_taps_save(add_transaction_flow: AddTransactionFlow) -> None:
    """Submit the Add Transaction form.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.tap_save()


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
