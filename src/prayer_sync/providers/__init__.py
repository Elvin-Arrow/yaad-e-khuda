"""Prayer timetable providers and provider resolution."""

from .base import DailyPrayerTimes, PrayerProvider
from .registry import get_provider

__all__ = ("DailyPrayerTimes", "PrayerProvider", "get_provider")
