from __future__ import annotations

from .base import PrayerProvider
from .mawaqit import MawaqitPrayerProvider
from ..errors import ProviderError

_PROVIDERS: dict[str, PrayerProvider] = {"mawaqit": MawaqitPrayerProvider()}


def get_provider(name: str) -> PrayerProvider:
    """Resolve a configured timetable provider by its stable name."""
    provider = _PROVIDERS.get(name.lower())
    if provider is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise ProviderError(
            f"unknown prayer-time provider {name!r}; available providers: {available}"
        )
    return provider
