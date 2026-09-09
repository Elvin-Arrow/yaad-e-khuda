from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from .errors import GoogleCalendarSyncError

TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
REVOKE_URI = "https://oauth2.googleapis.com/revoke"
SCOPE = "https://www.googleapis.com/auth/calendar"

EVENT_DURATION = timedelta(minutes=5)
UID_DOMAIN = "prayer-time-sync.local"


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    try:
        resp = requests.post(
            TOKEN_URI,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
    except requests.RequestException as e:
        raise GoogleCalendarSyncError(f"could not reach Google to exchange the auth code: {e}") from e

    if not resp.ok:
        raise GoogleCalendarSyncError(
            f"Google rejected the auth code exchange ({resp.status_code}): {resp.text}"
        )
    return resp.json()


def revoke(token: str) -> None:
    try:
        requests.post(REVOKE_URI, params={"token": token}, timeout=15)
    except requests.RequestException:
        pass


def build_service(client_id: str, client_secret: str, refresh_token: str) -> Resource:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[SCOPE],
    )
    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        raise GoogleCalendarSyncError(f"could not connect to Google Calendar: {e}") from e


def get_or_create_calendar(service: Resource, name: str) -> str:
    try:
        page_token = None
        while True:
            page = service.calendarList().list(pageToken=page_token).execute()
            for entry in page.get("items", []):
                if entry.get("summary") == name:
                    return entry["id"]
            page_token = page.get("nextPageToken")
            if not page_token:
                break
    except HttpError as e:
        raise GoogleCalendarSyncError(f"could not list Google calendars: {e}") from e

    try:
        created = service.calendars().insert(body={"summary": name}).execute()
        return created["id"]
    except HttpError as e:
        raise GoogleCalendarSyncError(
            f"could not create calendar {name!r} on Google Calendar: {e}"
        ) from e


def deterministic_event_id(prayer: str, day: date) -> str:
    digest = hashlib.sha1(f"prayer-sync-{prayer}-{day:%Y%m%d}@{UID_DOMAIN}".encode()).hexdigest()
    return digest


def _event_body(summary: str, iqama_dt: datetime, minutes_before: int) -> dict:
    tz_name = str(iqama_dt.tzinfo) if iqama_dt.tzinfo else None
    return {
        "summary": summary,
        "start": {"dateTime": iqama_dt.isoformat()},
        "end": {"dateTime": (iqama_dt + EVENT_DURATION).isoformat()},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": minutes_before}],
        },
    }


def upsert_event(
    service: Resource,
    calendar_id: str,
    prayer: str,
    day: date,
    iqama_dt: datetime,
    minutes_before: int,
) -> None:
    event_id = deterministic_event_id(prayer, day)
    summary = prayer.title()
    body = _event_body(summary, iqama_dt, minutes_before)

    try:
        service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        exists = True
    except HttpError as e:
        if e.resp.status == 404:
            exists = False
        else:
            raise GoogleCalendarSyncError(f"could not read Google Calendar event: {e}") from e

    try:
        if exists:
            service.events().update(
                calendarId=calendar_id, eventId=event_id, body=body
            ).execute()
        else:
            body["id"] = event_id
            service.events().insert(calendarId=calendar_id, body=body).execute()
    except HttpError as e:
        raise GoogleCalendarSyncError(f"could not save Google Calendar event: {e}") from e


def delete_event_if_exists(service: Resource, calendar_id: str, prayer: str, day: date) -> None:
    event_id = deterministic_event_id(prayer, day)
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as e:
        if e.resp.status in (404, 410):
            return
        raise GoogleCalendarSyncError(f"could not delete Google Calendar event: {e}") from e
