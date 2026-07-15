"""Business flow for Trackify's required first-run setup."""

from __future__ import annotations

from page.home_page import HomePage
from page.onboarding_page import OnboardingPage


class AppSetupFlow:
    """Orchestrate the three ordered onboarding setup stages."""

    def __init__(
        self,
        onboarding_page: OnboardingPage,
        home_page: HomePage,
    ) -> None:
        """Initialize the flow with injected page objects.

        Args:
            onboarding_page: First-run onboarding page object.
            home_page: Home page object used for final verification.
        """
        self._onboarding_page = onboarding_page
        self._home_page = home_page
        self._configured_name: str | None = None
        self._currency_symbol: str | None = None

    def enter_name_and_continue(self, name: str) -> None:
        """Complete the profile-name stage.

        Args:
            name: Profile name to save.
        """
        cleaned_name = self._required_text(name, "Name")
        self._onboarding_page.enter_name_and_continue(cleaned_name)
        self._configured_name = cleaned_name

    def configure_currency_and_budget(
        self,
        currency: str,
        monthly_budget: int | str,
    ) -> None:
        """Complete the currency and monthly-budget stage.

        Args:
            currency: Full visible currency label.
            monthly_budget: Positive monthly budget.
        """
        self._require_profile_stage()
        cleaned_currency = self._required_text(currency, "Currency")
        self._onboarding_page.select_currency(cleaned_currency)
        self._onboarding_page.set_monthly_budget(monthly_budget)
        self._onboarding_page.continue_from_budget()
        self._currency_symbol = cleaned_currency.split(maxsplit=1)[0]

    def enable_bank_sms_reader_and_finish(self) -> None:
        """Enable Bank SMS Reader, finish onboarding, and verify Home."""
        if self._currency_symbol is None:
            raise RuntimeError("Currency and budget setup must be completed first.")

        self._onboarding_page.enable_bank_sms_reader()
        assert self._onboarding_page.is_bank_sms_reader_enabled(), (
            "Bank SMS Reader was not enabled."
        )
        self._onboarding_page.tap_get_started()
        self._home_page.verify_visible()

        assert self._configured_name is not None
        assert self._home_page.has_user_name(self._configured_name), (
            f"Home did not show configured user {self._configured_name!r}."
        )
        assert self._home_page.uses_currency_symbol(self._currency_symbol), (
            f"Home did not use configured currency {self._currency_symbol!r}."
        )

    def _require_profile_stage(self) -> None:
        if self._configured_name is None:
            raise RuntimeError("Profile-name setup must be completed first.")

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError(f"{field_name} is required.")
        return cleaned_value
