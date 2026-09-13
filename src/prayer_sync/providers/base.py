from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from ..state import PrayerTime


@dataclass(frozen=True)
class DailyPrayerTimes:
    """Normalized prayer times and source metadata for one mosque day."""

    day: date
    timezone: str
    prayers: dict[str, PrayerTime]
    mosque_name: str | None = None


class PrayerProvider(ABC):
    """A source capable of returning normalized daily mosque prayer times."""

    @abstractmethod
    def fetch_prayer_times(
        self,
        mosque_identifier: str,
        day: date,
        *,
        timezone_override: str | None = None,
    ) -> DailyPrayerTimes:
        """Fetch and normalize prayer times for ``day``."""
