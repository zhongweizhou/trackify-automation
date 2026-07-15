"""Step definitions for Add Transaction BDD scenarios."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from flow.add_transaction_flow import AddTransactionFlow
from flow.app_setup_flow import AppSetupFlow

scenarios("../features/add_transaction.feature")


@given("app is launched with a clean database")
def app_launched_with_clean_database() -> None:
    """Document the clean app state provided by the autouse reset fixture."""


@given(parsers.parse('user enters name "{name}" and continues'))
def user_enters_name_and_continues(
    app_setup_flow: AppSetupFlow,
    name: str,
) -> None:
    """Save the first-run profile name and continue.

    Args:
        app_setup_flow: First-run setup flow fixture.
        name: Profile name from the Gherkin step.
    """
    app_setup_flow.enter_name_and_continue(name)


@given(
    parsers.parse(
        'user selects currency "{currency}" and sets monthly budget "{monthly_budget}"'
    )
)
def user_configures_currency_and_budget(
    app_setup_flow: AppSetupFlow,
    currency: str,
    monthly_budget: str,
) -> None:
    """Configure currency and monthly budget during onboarding.

    Args:
        app_setup_flow: First-run setup flow fixture.
        currency: Visible currency label from the Gherkin step.
        monthly_budget: Monthly budget from the Gherkin step.
    """
    app_setup_flow.configure_currency_and_budget(currency, monthly_budget)


@given("user enables Bank SMS Reader and gets started")
def user_enables_bank_sms_reader(app_setup_flow: AppSetupFlow) -> None:
    """Enable Bank SMS Reader and finish onboarding.

    Args:
        app_setup_flow: First-run setup flow fixture.
    """
    app_setup_flow.enable_bank_sms_reader_and_finish()


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
