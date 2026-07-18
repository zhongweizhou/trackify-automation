"""Strict environment selection and onboarding profile loading."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENVIRONMENT_DIRECTORY = ROOT / "data" / "environments"
SUPPORTED_ENVIRONMENTS = ("test", "preprod", "prod")
_PROFILE_KEYS = {
    "schema_version",
    "name",
    "currency",
    "bank_sms_reader_enabled",
}


class EnvironmentProfileError(ValueError):
    """An environment name or profile file is invalid."""


@dataclass(frozen=True)
class EnvironmentProfile:
    """Validated, non-secret onboarding data for one environment."""

    environment: str
    name: str
    currency: str
    bank_sms_reader_enabled: bool


def resolve_environment(
    cli_value: str | None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Resolve and validate CLI, process, and default environment precedence."""
    value = cli_value if cli_value is not None else environ.get("TEST_ENV", "preprod")
    if value not in SUPPORTED_ENVIRONMENTS:
        supported = ", ".join(SUPPORTED_ENVIRONMENTS)
        raise EnvironmentProfileError(
            f"Unsupported environment {value!r}; expected one of: {supported}"
        )
    return value


def load_environment_profile(
    environment: str,
    directory: Path = DEFAULT_ENVIRONMENT_DIRECTORY,
) -> EnvironmentProfile:
    """Load one environment file and reject schema drift before Appium setup."""
    resolved_environment = resolve_environment(environment, {})
    path = directory / f"{resolved_environment}.yaml"
    if not path.is_file():
        raise EnvironmentProfileError(
            f"Environment profile for {resolved_environment!r} does not exist: {path}"
        )

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise EnvironmentProfileError(
            f"Could not read environment profile {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise EnvironmentProfileError(f"Environment profile {path} must be a mapping")

    unknown = sorted(set(payload) - _PROFILE_KEYS)
    missing = sorted(_PROFILE_KEYS - set(payload))
    if unknown:
        raise EnvironmentProfileError(
            f"Environment profile {path} has unknown field(s): {', '.join(unknown)}"
        )
    if missing:
        raise EnvironmentProfileError(
            f"Environment profile {path} is missing field(s): {', '.join(missing)}"
        )
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise EnvironmentProfileError(
            f"Environment profile {path} schema_version must be integer 1"
        )

    name = _required_text(payload["name"], "name", path)
    currency = _required_text(payload["currency"], "currency", path)
    sms_enabled = payload["bank_sms_reader_enabled"]
    if type(sms_enabled) is not bool:
        raise EnvironmentProfileError(
            f"Environment profile {path} bank_sms_reader_enabled must be boolean"
        )

    return EnvironmentProfile(
        environment=resolved_environment,
        name=name,
        currency=currency,
        bank_sms_reader_enabled=sms_enabled,
    )


def _required_text(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvironmentProfileError(
            f"Environment profile {path} {field} must be a non-empty string"
        )
    return value.strip()
