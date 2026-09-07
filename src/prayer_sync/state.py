from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .errors import StateError


@dataclass(frozen=True)
class PrayerTime:
    adhan: datetime
    iqama: datetime


@dataclass(frozen=True)
class State:
    date: date
    tz_name: str
    prayers: dict[str, PrayerTime]


def _to_naive_iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat()


def save_state(
    path: str, day: date, tz_name: str, prayer_times: dict[str, PrayerTime]
) -> None:
    payload = {
        "date": day.isoformat(),
        "timezone": tz_name,
        "prayers": {
            name: {
                "adhan": _to_naive_iso(pt.adhan),
                "iqama": _to_naive_iso(pt.iqama),
            }
            for name, pt in prayer_times.items()
        },
    }

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)


def load_state(path: str, expected_date: date) -> State:
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError as e:
        raise StateError(
            f"state file not found: {path} (has the fetcher been run today?)"
        ) from e
    except json.JSONDecodeError as e:
        raise StateError(f"state file is not valid JSON: {path}: {e}") from e

    try:
        state_date = date.fromisoformat(payload["date"])
        tz_name = payload["timezone"]
        tz = ZoneInfo(tz_name)
        prayers = {
            name: PrayerTime(
                adhan=datetime.fromisoformat(times["adhan"]).replace(tzinfo=tz),
                iqama=datetime.fromisoformat(times["iqama"]).replace(tzinfo=tz),
            )
            for name, times in payload["prayers"].items()
        }
    except (KeyError, ValueError) as e:
        raise StateError(f"state file is malformed: {path}: {e}") from e

    if state_date != expected_date:
        raise StateError(
            f"state file is for {state_date.isoformat()}, not "
            f"{expected_date.isoformat()} -- run the fetcher again for today "
            f"before running the calendar sync"
        )

    return State(date=state_date, tz_name=tz_name, prayers=prayers)
