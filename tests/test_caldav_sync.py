from contextlib import contextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import icalendar
import pytest

from prayer_sync import caldav_sync


class FakeEvent:
    def __init__(self, ics: bytes) -> None:
        self.icalendar_instance = icalendar.Calendar.from_ical(ics)
        self.saved = False
        self.deleted = False

    @property
    def vevent(self) -> icalendar.Event:
        return next(
            c for c in self.icalendar_instance.subcomponents if c.name == "VEVENT"
        )

    @property
    def icalendar_component(self) -> icalendar.Event:
        return self.vevent

    @contextmanager
    def edit_icalendar_component(self):
        yield self.vevent

    def save(self) -> None:
        self.saved = True

    def delete(self) -> None:
        self.deleted = True


class FakeCalendar:
    def __init__(self) -> None:
        self.events_by_uid: dict[str, FakeEvent] = {}
        self.add_event_calls: list[bytes] = []

    def get_events(self) -> list[FakeEvent]:
        return list(self.events_by_uid.values())

    def add_event(self, ics: bytes) -> FakeEvent:
        event = FakeEvent(ics)
        self.add_event_calls.append(ics)
        self.events_by_uid[str(event.vevent["UID"])] = event
        return event


TZ = ZoneInfo("Europe/Paris")
DAY = date(2026, 1, 1)


def test_upsert_creates_event_with_single_alarm_when_absent() -> None:
    cal = FakeCalendar()
    iqama = datetime(2026, 1, 1, 6, 2, tzinfo=TZ)

    caldav_sync.upsert_event(cal, "fajr", DAY, iqama, minutes_before=10)

    uid = caldav_sync.deterministic_uid("fajr", DAY)
    assert len(cal.add_event_calls) == 1
    event = cal.events_by_uid[uid]
    assert event.vevent["SUMMARY"] == "Fajr"
    assert event.vevent["DTSTART"].dt == iqama

    alarms = [c for c in event.vevent.subcomponents if c.name == "VALARM"]
    assert len(alarms) == 1
    assert alarms[0]["ACTION"] == "DISPLAY"
    assert alarms[0]["TRIGGER"].dt == timedelta(minutes=-10)


def test_upsert_updates_existing_event_without_duplicating_or_creating() -> None:
    cal = FakeCalendar()
    caldav_sync.upsert_event(
        cal, "fajr", DAY, datetime(2026, 1, 1, 6, 2, tzinfo=TZ), minutes_before=10
    )
    uid = caldav_sync.deterministic_uid("fajr", DAY)
    event = cal.events_by_uid[uid]

    new_iqama = datetime(2026, 1, 1, 6, 5, tzinfo=TZ)
    caldav_sync.upsert_event(cal, "fajr", DAY, new_iqama, minutes_before=15)

    assert len(cal.events_by_uid) == 1
    assert len(cal.add_event_calls) == 1
    assert event.saved is True

    alarms = [c for c in event.vevent.subcomponents if c.name == "VALARM"]
    assert len(alarms) == 1
    assert alarms[0]["TRIGGER"].dt == timedelta(minutes=-15)
    assert event.vevent["DTSTART"].dt == new_iqama


def test_delete_event_if_exists_deletes_when_present() -> None:
    cal = FakeCalendar()
    caldav_sync.upsert_event(
        cal, "asr", DAY, datetime(2026, 1, 1, 17, 47, tzinfo=TZ), minutes_before=10
    )
    uid = caldav_sync.deterministic_uid("asr", DAY)
    event = cal.events_by_uid[uid]

    caldav_sync.delete_event_if_exists(cal, "asr", DAY)

    assert event.deleted is True


def test_delete_event_if_exists_is_noop_when_absent() -> None:
    cal = FakeCalendar()
    caldav_sync.delete_event_if_exists(cal, "isha", DAY)
    assert cal.events_by_uid == {}


def test_upsert_and_delete_never_use_uid_filtered_lookup() -> None:
    cal = FakeCalendar()
    assert not hasattr(cal, "get_event_by_uid")

    caldav_sync.upsert_event(
        cal, "fajr", DAY, datetime(2026, 1, 1, 6, 2, tzinfo=TZ), minutes_before=10
    )
    caldav_sync.delete_event_if_exists(cal, "fajr", DAY)


def test_deterministic_uid_is_stable_per_prayer_and_day() -> None:
    assert caldav_sync.deterministic_uid("fajr", DAY) == caldav_sync.deterministic_uid(
        "fajr", DAY
    )
    assert caldav_sync.deterministic_uid("fajr", DAY) != caldav_sync.deterministic_uid(
        "dhuhr", DAY
    )
    assert caldav_sync.deterministic_uid(
        "fajr", DAY
    ) != caldav_sync.deterministic_uid("fajr", date(2026, 1, 2))
