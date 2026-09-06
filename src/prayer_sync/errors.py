"""Shared exception types.

Every failure mode that should cause the CLI to log clearly and exit
non-zero (see docs/idea.md #4, "Error visibility") raises one of these
rather than letting a raw exception propagate.
"""


class PrayerSyncError(Exception):
    """Base class for all expected/handled failures in this project."""


class ConfigError(PrayerSyncError):
    """The config file is missing, unreadable, or missing required fields."""


class MawaqitError(PrayerSyncError):
    """The mosque page couldn't be fetched, or confData couldn't be parsed."""


class StateError(PrayerSyncError):
    """Local state is missing, unreadable, or stale (not today's)."""


class CalDavSyncError(PrayerSyncError):
    """Authentication or calendar operations against iCloud failed."""
