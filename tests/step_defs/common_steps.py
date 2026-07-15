"""Shared pytest-bdd steps for Trackify setup and transaction entry."""

from __future__ import annotations

from pytest_bdd import given, parsers, when

from flow.add_transaction_flow import AddTransactionFlow
from flow.app_setup_flow import AppSetupFlow


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
        'user selects currency "{currency}" and sets monthly budget "{budget}"'
    )
)
def user_configures_currency_and_budget(
    app_setup_flow: AppSetupFlow,
    currency: str,
    budget: str,
) -> None:
    """Configure currency and monthly budget during onboarding.

    Args:
        app_setup_flow: First-run setup flow fixture.
        currency: Visible currency label from the Gherkin step.
        budget: Monthly budget from the Gherkin step.
    """
    app_setup_flow.configure_currency_and_budget(currency, budget)


@given("user enables Bank SMS Reader and gets started")
def user_enables_bank_sms_reader(app_setup_flow: AppSetupFlow) -> None:
    """Enable Bank SMS Reader and finish onboarding.

    Args:
        app_setup_flow: First-run setup flow fixture.
    """
    app_setup_flow.enable_bank_sms_reader_and_finish()


@given("user is on the Home page")
def user_is_on_home_page(add_transaction_flow: AddTransactionFlow) -> None:
    """Verify the Home page and capture its monthly summary baseline.

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


@when(parsers.parse('user enters tags "{tags}"'))
def user_enters_tags(
    add_transaction_flow: AddTransactionFlow,
    tags: str,
) -> None:
    """Enter comma-separated transaction tags.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        tags: Tags supplied by the Gherkin scenario.
    """
    add_transaction_flow.enter_tags(tags)


@when(parsers.parse('user selects transaction date and time "{date_time}"'))
def user_selects_transaction_date_time(
    add_transaction_flow: AddTransactionFlow,
    date_time: str,
) -> None:
    """Select an explicit transaction date and time.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
        date_time: Date/time supplied by the Gherkin scenario.
    """
    add_transaction_flow.select_date_time(date_time)


@when("user taps Save")
def user_taps_save(add_transaction_flow: AddTransactionFlow) -> None:
    """Submit the Add Transaction form.

    Args:
        add_transaction_flow: Add Transaction business flow fixture.
    """
    add_transaction_flow.tap_save()
