from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from googleapiclient.errors import HttpError

from prayer_sync import google_calendar_sync


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status = status
        self.reason = "not found"


def _http_error(status: int) -> HttpError:
    return HttpError(_FakeResp(status), b"{}")


class _Executable:
    def __init__(self, result=None, error: HttpError | None = None) -> None:
        self._result = result
        self._error = error

    def execute(self):
        if self._error is not None:
            raise self._error
        return self._result


class FakeCalendarList:
    def __init__(self, calendars: list[dict]) -> None:
        self._calendars = calendars

    def list(self, pageToken=None) -> _Executable:
        return _Executable({"items": self._calendars, "nextPageToken": None})


class FakeCalendarsResource:
    def __init__(self, service: "FakeService") -> None:
        self._service = service

    def insert(self, body: dict) -> _Executable:
        new_id = f"calendar-{len(self._service.calendar_entries) + 1}"
        entry = {"id": new_id, "summary": body["summary"]}
        self._service.calendar_entries.append(entry)
        return _Executable(entry)


class FakeEvents:
    def __init__(self, service: "FakeService") -> None:
        self._service = service

    def get(self, calendarId: str, eventId: str) -> _Executable:
        events = self._service.events_by_calendar.setdefault(calendarId, {})
        if eventId in events:
            return _Executable(events[eventId])
        return _Executable(error=_http_error(404))

    def insert(self, calendarId: str, body: dict) -> _Executable:
        events = self._service.events_by_calendar.setdefault(calendarId, {})
        events[body["id"]] = body
        self._service.insert_calls.append((calendarId, body))
        return _Executable(body)

    def update(self, calendarId: str, eventId: str, body: dict) -> _Executable:
        events = self._service.events_by_calendar.setdefault(calendarId, {})
        events[eventId] = body
        self._service.update_calls.append((calendarId, eventId, body))
        return _Executable(body)

    def delete(self, calendarId: str, eventId: str) -> _Executable:
        events = self._service.events_by_calendar.setdefault(calendarId, {})
        if eventId not in events:
            return _Executable(error=_http_error(404))
        del events[eventId]
        return _Executable({})


class FakeService:
    def __init__(self, calendars: list[dict] | None = None) -> None:
        self.calendar_entries = calendars if calendars is not None else []
        self.events_by_calendar: dict[str, dict] = {}
        self.insert_calls: list[tuple] = []
        self.update_calls: list[tuple] = []

    def calendarList(self) -> FakeCalendarList:
        return FakeCalendarList(self.calendar_entries)

    def calendars(self) -> FakeCalendarsResource:
        return FakeCalendarsResource(self)

    def events(self) -> FakeEvents:
        return FakeEvents(self)


TZ = ZoneInfo("Europe/Paris")
DAY = date(2026, 1, 1)


def test_get_or_create_calendar_creates_when_absent() -> None:
    service = FakeService()

    calendar_id = google_calendar_sync.get_or_create_calendar(service, "Prayer Reminders")

    assert calendar_id == "calendar-1"
    assert service.calendar_entries == [{"id": "calendar-1", "summary": "Prayer Reminders"}]


def test_get_or_create_calendar_reuses_by_name() -> None:
    service = FakeService(calendars=[{"id": "existing", "summary": "Prayer Reminders"}])

    calendar_id = google_calendar_sync.get_or_create_calendar(service, "Prayer Reminders")

    assert calendar_id == "existing"
    assert service.calendar_entries == [{"id": "existing", "summary": "Prayer Reminders"}]


def test_upsert_creates_event_with_reminder_when_absent() -> None:
    service = FakeService()
    iqama = datetime(2026, 1, 1, 6, 2, tzinfo=TZ)

    google_calendar_sync.upsert_event(service, "cal-1", "fajr", DAY, iqama, minutes_before=10)

    event_id = google_calendar_sync.deterministic_event_id("fajr", DAY)
    assert len(service.insert_calls) == 1
    event = service.events_by_calendar["cal-1"][event_id]
    assert event["summary"] == "Fajr"
    assert event["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 10}],
    }


def test_upsert_updates_existing_event_without_duplicating() -> None:
    service = FakeService()
    google_calendar_sync.upsert_event(
        service, "cal-1", "fajr", DAY, datetime(2026, 1, 1, 6, 2, tzinfo=TZ), minutes_before=10
    )

    new_iqama = datetime(2026, 1, 1, 6, 5, tzinfo=TZ)
    google_calendar_sync.upsert_event(service, "cal-1", "fajr", DAY, new_iqama, minutes_before=15)

    event_id = google_calendar_sync.deterministic_event_id("fajr", DAY)
    assert len(service.insert_calls) == 1
    assert len(service.update_calls) == 1
    event = service.events_by_calendar["cal-1"][event_id]
    assert event["reminders"]["overrides"] == [{"method": "popup", "minutes": 15}]
    assert event["start"]["dateTime"] == new_iqama.isoformat()


def test_delete_event_if_exists_deletes_when_present() -> None:
    service = FakeService()
    google_calendar_sync.upsert_event(
        service, "cal-1", "asr", DAY, datetime(2026, 1, 1, 17, 47, tzinfo=TZ), minutes_before=10
    )
    event_id = google_calendar_sync.deterministic_event_id("asr", DAY)

    google_calendar_sync.delete_event_if_exists(service, "cal-1", "asr", DAY)

    assert event_id not in service.events_by_calendar["cal-1"]


def test_delete_event_if_exists_is_noop_when_absent() -> None:
    service = FakeService()
    google_calendar_sync.delete_event_if_exists(service, "cal-1", "isha", DAY)
    assert service.events_by_calendar.get("cal-1", {}) == {}


def test_deterministic_event_id_is_stable_per_prayer_and_day() -> None:
    assert google_calendar_sync.deterministic_event_id(
        "fajr", DAY
    ) == google_calendar_sync.deterministic_event_id("fajr", DAY)
    assert google_calendar_sync.deterministic_event_id(
        "fajr", DAY
    ) != google_calendar_sync.deterministic_event_id("dhuhr", DAY)


def test_deterministic_event_id_matches_google_charset() -> None:
    import re

    event_id = google_calendar_sync.deterministic_event_id("fajr", DAY)
    assert re.fullmatch(r"[a-v0-9]{5,1024}", event_id)


def test_build_auth_url_includes_expected_params() -> None:
    url = google_calendar_sync.build_auth_url(
        "client-123", "http://localhost:8000/api/google/oauth/callback", "state-abc"
    )
    assert url.startswith(google_calendar_sync.AUTH_URI)
    assert "client_id=client-123" in url
    assert "state=state-abc" in url
    assert "access_type=offline" in url
