class PrayerSyncError(Exception):
    pass


class ConfigError(PrayerSyncError):
    pass


class MawaqitError(PrayerSyncError):
    pass


class StateError(PrayerSyncError):
    pass


class CalDavSyncError(PrayerSyncError):
    pass


class GoogleCalendarSyncError(PrayerSyncError):
    pass
