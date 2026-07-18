"""Environment-aware pytest and onboarding runtime behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import conftest
from flow.app_setup_flow import AppSetupFlow
from tests.step_defs import common_steps
from utils.environment_profile import EnvironmentProfile, SUPPORTED_ENVIRONMENTS

pytestmark = pytest.mark.unit


class _OptionParser:
    """Capture one pytest option registration without constructing pytest internals."""

    def __init__(self) -> None:
        self.names: tuple[str, ...] = ()
        self.options: dict[str, object] = {}

    def addoption(self, *names: str, **options: object) -> None:
        self.names = names
        self.options = options


def _profile(*, sms_enabled: bool = True) -> EnvironmentProfile:
    return EnvironmentProfile(
        environment="test",
        name="Rose",
        currency="$ US Dollar",
        bank_sms_reader_enabled=sms_enabled,
    )


def test_pytest_env_option_is_explicit_and_validated() -> None:
    parser = _OptionParser()

    conftest.pytest_addoption(parser)

    assert parser.names == ("--env",)
    assert parser.options["choices"] == SUPPORTED_ENVIRONMENTS
    assert parser.options["default"] is None
    assert parser.options["dest"] == "trackify_environment"


def test_configured_environment_steps_delegate_profile_values() -> None:
    app_setup_flow = MagicMock()
    profile = _profile()

    common_steps.user_enters_configured_environment_name(app_setup_flow, profile)
    common_steps.user_configures_environment_currency_and_budget(
        app_setup_flow,
        profile,
        "30000",
    )
    common_steps.user_applies_environment_sms_setting(app_setup_flow, profile)

    app_setup_flow.enter_name_and_continue.assert_called_once_with("Rose")
    app_setup_flow.configure_currency_and_budget.assert_called_once_with(
        "$ US Dollar",
        "30000",
    )
    app_setup_flow.configure_bank_sms_reader_and_finish.assert_called_once_with(True)


@pytest.mark.parametrize("sms_enabled", [True, False])
def test_setup_flow_applies_requested_sms_state(sms_enabled: bool) -> None:
    onboarding_page = MagicMock()
    onboarding_page.is_bank_sms_reader_enabled.return_value = sms_enabled
    home_page = MagicMock()
    home_page.has_user_name.return_value = True
    home_page.uses_currency_symbol.return_value = True
    flow = AppSetupFlow(onboarding_page, home_page)
    flow.enter_name_and_continue("Rose")
    flow.configure_currency_and_budget("$ US Dollar", "30000")

    flow.configure_bank_sms_reader_and_finish(sms_enabled)

    onboarding_page.set_bank_sms_reader_enabled.assert_called_once_with(sms_enabled)
    onboarding_page.tap_get_started.assert_called_once_with()
    home_page.verify_visible.assert_called_once_with()
