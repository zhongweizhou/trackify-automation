"""Unit tests for strict multi-environment onboarding profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.environment_profile import (
    EnvironmentProfileError,
    load_environment_profile,
    resolve_environment,
)

pytestmark = pytest.mark.unit


def test_committed_profiles_resolve_exact_values() -> None:
    test = load_environment_profile("test")
    preprod = load_environment_profile("preprod")
    prod = load_environment_profile("prod")

    assert (test.name, test.currency, test.bank_sms_reader_enabled) == (
        "Rose",
        "$ US Dollar",
        True,
    )
    assert (preprod.name, preprod.currency, preprod.bank_sms_reader_enabled) == (
        "Kimbal",
        "$ US Dollar",
        True,
    )
    assert (prod.name, prod.currency, prod.bank_sms_reader_enabled) == (
        "Kimi",
        "$ US Dollar",
        True,
    )


def test_resolve_environment_precedence() -> None:
    assert resolve_environment("prod", {"TEST_ENV": "test"}) == "prod"
    assert resolve_environment(None, {"TEST_ENV": "test"}) == "test"
    assert resolve_environment(None, {}) == "preprod"


@pytest.mark.parametrize("environment", ["", "qa", "production", "PREPROD"])
def test_unknown_environment_is_rejected(environment: str) -> None:
    with pytest.raises(EnvironmentProfileError, match="Unsupported environment"):
        resolve_environment(environment, {})


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        (
            'schema_version: 2\nname: Rose\ncurrency: "$ US Dollar"\n'
            "bank_sms_reader_enabled: true\n",
            "schema_version",
        ),
        (
            'schema_version: 1\nname: ""\ncurrency: "$ US Dollar"\n'
            "bank_sms_reader_enabled: true\n",
            "name",
        ),
        (
            'schema_version: 1\nname: Rose\ncurrency: "$ US Dollar"\n'
            'bank_sms_reader_enabled: "true"\n',
            "bank_sms_reader_enabled",
        ),
        (
            'schema_version: 1\nname: Rose\ncurrency: "$ US Dollar"\n'
            "bank_sms_reader_enabled: true\nextra: value\n",
            "unknown field",
        ),
    ],
)
def test_invalid_profile_is_rejected(
    tmp_path: Path,
    yaml_text: str,
    message: str,
) -> None:
    (tmp_path / "test.yaml").write_text(yaml_text, encoding="utf-8")

    with pytest.raises(EnvironmentProfileError, match=message):
        load_environment_profile("test", directory=tmp_path)


def test_missing_profile_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentProfileError, match="does not exist"):
        load_environment_profile("test", directory=tmp_path)
