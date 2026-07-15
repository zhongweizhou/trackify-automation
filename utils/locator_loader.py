"""Locator loader with a strategy fallback chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

Locator = tuple[str, str]

_STRATEGY_PRIORITY = (
    "accessibility_id",
    "id",
    "class_chain",
    "class",
    "xpath",
    "predicate",
)

_cache: dict[tuple[str, str, str], Locator] = {}


def load_locator(page: str, key: str, platform: str = "android") -> Locator:
    """Return the first available locator strategy and value.

    Args:
        page: Locator YAML filename without the ``.yaml`` suffix.
        key: Locator key inside the page YAML file.
        platform: Platform section to read, such as ``android`` or ``ios``.

    Returns:
        The locator as a ``(strategy, value)`` tuple.

    Raises:
        KeyError: If the page, key, platform, or supported locator strategy is
            missing.
    """
    normalized_platform = platform.strip().lower()
    cache_key = (page, key, normalized_platform)
    if cache_key in _cache:
        return _cache[cache_key]

    data = _load_yaml(page)
    entry = _read_platform_entry(data, page, key, normalized_platform)

    for strategy in _STRATEGY_PRIORITY:
        value = entry.get(strategy)
        if value:
            locator = (strategy, str(value))
            _cache[cache_key] = locator
            return locator

    raise KeyError(
        f"No supported locator strategy for {page}.{key} on "
        f"{normalized_platform}. Available keys: {list(entry.keys())}"
    )


def clear_cache() -> None:
    """Drop cached locators so YAML files are read again."""
    _cache.clear()


def _load_yaml(page: str) -> dict[str, Any]:
    yaml_path = Path(__file__).resolve().parent.parent / "locator" / f"{page}.yaml"
    if not yaml_path.exists():
        raise KeyError(f"Locator file not found: {yaml_path}")

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise KeyError(f"Locator file is empty or invalid: {yaml_path}")
    return data


def _read_platform_entry(
    data: dict[str, Any],
    page: str,
    key: str,
    platform: str,
) -> dict[str, Any]:
    if key not in data:
        raise KeyError(f"Locator key not found: {page}.{key}")

    locator_entry = data[key]
    if not isinstance(locator_entry, dict):
        raise KeyError(f"Locator entry must be a mapping: {page}.{key}")

    if platform not in locator_entry:
        raise KeyError(f"Platform '{platform}' not found for locator: {page}.{key}")

    platform_entry = locator_entry[platform]
    if not isinstance(platform_entry, dict):
        raise KeyError(f"Platform entry must be a mapping: {page}.{key}.{platform}")

    return platform_entry
