from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import caldav
import icalendar
from caldav.lib.error import AuthorizationError

from .errors import CalDavSyncError

ICLOUD_URL = "https://caldav.icloud.com/"

EVENT_DURATION = timedelta(minutes=5)
UID_DOMAIN = "prayer-time-sync.local"


def connect(apple_id: str, app_specific_password: str) -> caldav.Principal:
    client = caldav.DAVClient(
        url=ICLOUD_URL, username=apple_id, password=app_specific_password
    )
    try:
        return client.principal()
    except AuthorizationError as e:
        raise CalDavSyncError(
            "iCloud authentication failed -- check icloud.apple_id and "
            "icloud.app_specific_password in config.yaml (this must be an "
            "app-specific password, not your real Apple ID password)"
        ) from e
    except Exception as e:
        raise CalDavSyncError(f"could not connect to iCloud CalDAV: {e}") from e


def get_or_create_calendar(
    principal: caldav.Principal, name: str
) -> caldav.Calendar:
    try:
        existing = principal.calendars()
    except Exception as e:
        raise CalDavSyncError(f"could not list iCloud calendars: {e}") from e

    for cal in existing:
        if cal.get_display_name() == name:
            return cal

    try:
        return principal.make_calendar(name=name)
    except Exception as e:
        raise CalDavSyncError(
            f"could not create calendar {name!r} on iCloud ({e}). "
            f"iCloud's CalDAV server is known to be finicky about calendar "
            f"creation -- as a one-time workaround, create a calendar named "
            f"exactly {name!r} yourself in the Calendar app or at "
            f"icloud.com/calendar, then rerun."
        ) from e


def deterministic_uid(prayer: str, day: date) -> str:
    return f"prayer-sync-{prayer}-{day:%Y%m%d}@{UID_DOMAIN}"


def _find_event_by_uid(calendar: caldav.Calendar, uid: str) -> caldav.Event | None:
    try:
        events = calendar.get_events()
    except Exception as e:
        raise CalDavSyncError(f"could not list events on iCloud calendar: {e}") from e

    for event in events:
        try:
            event_uid = str(event.icalendar_component.get("UID", ""))
        except Exception as e:
            raise CalDavSyncError(f"could not read an event's UID: {e}") from e
        if event_uid == uid:
            return event
    return None


def _build_alarm(minutes_before: int, description: str) -> icalendar.Alarm:
    alarm = icalendar.Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", description)
    alarm.add("trigger", timedelta(minutes=-minutes_before))
    return alarm


def _build_event_ics(
    uid: str, summary: str, iqama_dt: datetime, minutes_before: int
) -> bytes:
    cal = icalendar.Calendar()
    cal.add("prodid", "-//prayer-time-sync//EN")
    cal.add("version", "2.0")

    event = icalendar.Event()
    event.add("uid", uid)
    event.add("summary", summary)
    event.add("dtstart", iqama_dt)
    event.add("dtend", iqama_dt + EVENT_DURATION)
    event.add("dtstamp", datetime.now(timezone.utc))
    event.add_component(_build_alarm(minutes_before, summary))

    cal.add_component(event)
    return cal.to_ical()


def upsert_event(
    calendar: caldav.Calendar,
    prayer: str,
    day: date,
    iqama_dt: datetime,
    minutes_before: int,
) -> None:
    uid = deterministic_uid(prayer, day)
    summary = f"{prayer.title()}"

    event = _find_event_by_uid(calendar, uid)

    if event is not None:
        with event.edit_icalendar_component() as ev:
            for key in ("dtstart", "dtend", "dtstamp"):
                ev.pop(key, None)
            ev.add("dtstart", iqama_dt)
            ev.add("dtend", iqama_dt + EVENT_DURATION)
            ev.add("dtstamp", datetime.now(timezone.utc))
            ev.subcomponents = [
                c for c in ev.subcomponents if c.name != "VALARM"
            ]
            ev.add_component(_build_alarm(minutes_before, summary))
        event.save()
    else:
        ics = _build_event_ics(uid, summary, iqama_dt, minutes_before)
        calendar.add_event(ics)


def delete_event_if_exists(calendar: caldav.Calendar, prayer: str, day: date) -> None:
    uid = deterministic_uid(prayer, day)
    event = _find_event_by_uid(calendar, uid)
    if event is not None:
        event.delete()
