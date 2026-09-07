from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from .errors import MawaqitError
from .state import PrayerTime

CANONICAL_PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")

_ADHAN_INDEX = {"fajr": 0, "dhuhr": 2, "asr": 3, "maghrib": 4, "isha": 5}

_IQAMA_INDEX = {name: i for i, name in enumerate(CANONICAL_PRAYERS)}

_CONF_DATA_MARKER = "confData = "


def fetch_html(slug_or_url: str) -> str:
    url = slug_or_url
    if not url.startswith("http"):
        url = f"https://mawaqit.net/en/{slug_or_url}"

    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "prayer-time-sync/1.0"})
    except requests.RequestException as e:
        raise MawaqitError(f"could not reach {url}: {e}") from e

    if resp.status_code != 200:
        raise MawaqitError(f"unexpected HTTP {resp.status_code} fetching {url}")

    return resp.text


def extract_conf_data(html: str) -> dict:
    marker_index = html.find(_CONF_DATA_MARKER)
    if marker_index == -1:
        raise MawaqitError(
            "could not find 'confData' in the page -- the mosque slug may be "
            "wrong, or Mawaqit's page structure has changed"
        )

    start = html.find("{", marker_index)
    if start == -1:
        raise MawaqitError("found 'confData' marker but no opening '{' after it")

    depth = 0
    end = None
    in_string = False
    escape = False
    for i in range(start, len(html)):
        c = html[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise MawaqitError("confData JSON block is not properly closed")

    raw = html[start:end]
    try:
        conf = json.loads(raw)
    except json.JSONDecodeError as e:
        raise MawaqitError(f"confData did not parse as JSON: {e}") from e

    if "calendar" not in conf or "iqamaCalendar" not in conf:
        raise MawaqitError(
            "confData is missing 'calendar' and/or 'iqamaCalendar' -- "
            "unexpected page structure, refusing to proceed with partial data"
        )

    return conf


def _resolve_iqama(prayer: str, raw_value: str, adhan_dt: datetime) -> datetime:
    if not isinstance(raw_value, str):
        raise MawaqitError(f"unparseable iqama value for {prayer}: {raw_value!r}")

    if ":" in raw_value:
        try:
            hour, minute = (int(part) for part in raw_value.split(":"))
        except ValueError as e:
            raise MawaqitError(
                f"unparseable fixed iqama time for {prayer}: {raw_value!r}"
            ) from e
        return adhan_dt.replace(hour=hour, minute=minute)

    try:
        offset_minutes = int(raw_value)
    except ValueError as e:
        raise MawaqitError(
            f"unparseable iqama offset for {prayer}: {raw_value!r}"
        ) from e
    return adhan_dt + timedelta(minutes=offset_minutes)


def today_prayer_times(
    conf: dict, today: date, tz_override: str | None = None
) -> dict[str, PrayerTime]:
    tz_name = tz_override or conf.get("timezone")
    if not tz_name:
        raise MawaqitError(
            "no timezone available: confData has no 'timezone' field and "
            "no mosque.timezone_override is set in config"
        )
    try:
        tz = ZoneInfo(tz_name)
    except Exception as e:
        raise MawaqitError(f"invalid IANA timezone {tz_name!r}: {e}") from e

    month_idx = today.month - 1
    day_key = str(today.day)

    try:
        adhan_row = conf["calendar"][month_idx][day_key]
    except (IndexError, KeyError) as e:
        raise MawaqitError(
            f"no calendar entry for {today.isoformat()} in confData"
        ) from e
    try:
        iqama_row = conf["iqamaCalendar"][month_idx][day_key]
    except (IndexError, KeyError) as e:
        raise MawaqitError(
            f"no iqamaCalendar entry for {today.isoformat()} in confData"
        ) from e

    result: dict[str, PrayerTime] = {}
    for name in CANONICAL_PRAYERS:
        try:
            adhan_str = adhan_row[_ADHAN_INDEX[name]]
            iqama_raw = iqama_row[_IQAMA_INDEX[name]]
        except IndexError as e:
            raise MawaqitError(
                f"confData row for {today.isoformat()} is shorter than expected"
            ) from e

        try:
            hour, minute = (int(part) for part in adhan_str.split(":"))
        except (ValueError, AttributeError) as e:
            raise MawaqitError(
                f"unparseable adhan time for {name}: {adhan_str!r}"
            ) from e

        adhan_dt = datetime(
            today.year, today.month, today.day, hour, minute, tzinfo=tz
        )
        iqama_dt = _resolve_iqama(name, iqama_raw, adhan_dt)
        result[name] = PrayerTime(adhan=adhan_dt, iqama=iqama_dt)

    return result
