from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

from . import caldav_sync, google_calendar_sync
from .config import CANONICAL_PRAYERS, Config, load_config
from .errors import PrayerSyncError
from .mawaqit import extract_conf_data, fetch_html, today_prayer_times
from .state import PrayerTime, State, load_state, save_state

LAST_RUN_FILE = "state/last_run.json"


@dataclass(frozen=True)
class RunResult:
    ok: bool
    message: str


def run_fetch(config_path: str) -> RunResult:
    try:
        config = load_config(config_path)
        today = date.today()
        html = fetch_html(config.mosque.slug)
        conf = extract_conf_data(html)
        prayer_times = today_prayer_times(
            conf, today, tz_override=config.mosque.timezone_override
        )
        tz_name = config.mosque.timezone_override or conf.get("timezone")
        save_state(config.state_file, today, tz_name, prayer_times)
    except PrayerSyncError as e:
        return RunResult(ok=False, message=f"fetch failed: {e}")
    except Exception as e:
        return RunResult(ok=False, message=f"fetch failed with an unexpected error: {e}")

    return RunResult(
        ok=True,
        message=f"fetched {len(prayer_times)} prayer times for {today} -> {config.state_file}",
    )


def _sync_icloud(config: Config, today: date, state: State) -> RunResult:
    try:
        principal = caldav_sync.connect(
            config.icloud.apple_id, config.icloud.app_specific_password
        )
        calendar = caldav_sync.get_or_create_calendar(
            principal, config.icloud.calendar_name
        )

        for name in CANONICAL_PRAYERS:
            prayer_cfg = config.prayers[name]
            if prayer_cfg.enabled:
                pt = state.prayers[name]
                caldav_sync.upsert_event(
                    calendar, name, today, pt.iqama, prayer_cfg.minutes_before
                )
            else:
                caldav_sync.delete_event_if_exists(calendar, name, today)
    except PrayerSyncError as e:
        return RunResult(ok=False, message=f"iCloud sync failed: {e}")
    except Exception as e:
        return RunResult(ok=False, message=f"iCloud sync failed with an unexpected error: {e}")

    return RunResult(
        ok=True, message=f"synced iCloud calendar {config.icloud.calendar_name!r} for {today}"
    )


def _sync_google(config: Config, today: date, state: State) -> RunResult:
    try:
        service = google_calendar_sync.build_service(
            config.google.client_id, config.google.client_secret, config.google.refresh_token
        )
        calendar_id = google_calendar_sync.get_or_create_calendar(
            service, config.google.calendar_name
        )

        for name in CANONICAL_PRAYERS:
            prayer_cfg = config.prayers[name]
            if prayer_cfg.enabled:
                pt = state.prayers[name]
                google_calendar_sync.upsert_event(
                    service, calendar_id, name, today, pt.iqama, prayer_cfg.minutes_before
                )
            else:
                google_calendar_sync.delete_event_if_exists(service, calendar_id, name, today)
    except PrayerSyncError as e:
        return RunResult(ok=False, message=f"Google sync failed: {e}")
    except Exception as e:
        return RunResult(ok=False, message=f"Google sync failed with an unexpected error: {e}")

    return RunResult(
        ok=True, message=f"synced Google calendar {config.google.calendar_name!r} for {today}"
    )


def run_sync(config_path: str) -> RunResult:
    try:
        config = load_config(config_path)
        today = date.today()
        state = load_state(config.state_file, today)
    except PrayerSyncError as e:
        return RunResult(ok=False, message=f"sync failed: {e}")
    except Exception as e:
        return RunResult(ok=False, message=f"sync failed with an unexpected error: {e}")

    results: list[RunResult] = []
    if config.icloud:
        results.append(_sync_icloud(config, today, state))
    if config.google and config.google.refresh_token:
        results.append(_sync_google(config, today, state))

    if not results:
        return RunResult(
            ok=False,
            message="sync failed, no calendar connected (connect iCloud or Google Calendar in Settings)",
        )

    return RunResult(
        ok=all(r.ok for r in results),
        message="; ".join(r.message for r in results),
    )


def run_daily(config_path: str) -> dict:
    fetch_result = run_fetch(config_path)
    sync_result: RunResult | None = None
    if fetch_result.ok:
        sync_result = run_sync(config_path)

    status = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "fetch": asdict(fetch_result),
        "sync": asdict(sync_result) if sync_result is not None else None,
        "ok": fetch_result.ok and (sync_result.ok if sync_result is not None else False),
    }
    _write_last_run(status)
    return status


def _write_last_run(status: dict) -> None:
    parent = os.path.dirname(LAST_RUN_FILE)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = f"{LAST_RUN_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, LAST_RUN_FILE)


def last_run_status() -> dict:
    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ran_at": None, "fetch": None, "sync": None, "ok": None}


def today_preview(config: Config) -> dict:
    today = date.today()
    html = fetch_html(config.mosque.slug)
    conf = extract_conf_data(html)
    prayer_times = today_prayer_times(
        conf, today, tz_override=config.mosque.timezone_override
    )
    tz_name = config.mosque.timezone_override or conf.get("timezone")

    now = datetime.now(prayer_times["fajr"].iqama.tzinfo)
    next_prayer = _find_next_prayer(config, prayer_times, now)

    return {
        "date": today.isoformat(),
        "timezone": tz_name,
        "mosque_name": conf.get("name"),
        "prayers": {
            name: {"adhan": pt.adhan.isoformat(), "iqama": pt.iqama.isoformat()}
            for name, pt in prayer_times.items()
        },
        "next_prayer": next_prayer,
    }


def _find_next_prayer(
    config: Config, prayer_times: dict[str, PrayerTime], now: datetime
) -> dict | None:
    enabled_in_order = [
        (name, prayer_times[name])
        for name in CANONICAL_PRAYERS
        if config.prayers[name].enabled
    ]
    if not enabled_in_order:
        return None

    upcoming = [(name, pt) for name, pt in enabled_in_order if pt.iqama > now]
    passed = [(name, pt) for name, pt in enabled_in_order if pt.iqama <= now]

    if not upcoming:
        return {
            "resting": True,
            "name": enabled_in_order[0][0],
            "iqama": None,
            "previous_name": passed[-1][0] if passed else None,
            "previous_iqama": passed[-1][1].iqama.isoformat() if passed else None,
            "progress": None,
        }

    next_name, next_pt = upcoming[0]
    if not passed:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        span = (next_pt.iqama - midnight).total_seconds()
        elapsed = (now - midnight).total_seconds()
        progress = max(0.0, min(1.0, elapsed / span)) if span > 0 else 0.0
        return {
            "resting": False,
            "name": next_name,
            "iqama": next_pt.iqama.isoformat(),
            "previous_name": None,
            "previous_iqama": None,
            "progress": progress,
        }

    prev_name, prev_pt = passed[-1]
    span = (next_pt.iqama - prev_pt.iqama).total_seconds()
    elapsed = (now - prev_pt.iqama).total_seconds()
    progress = max(0.0, min(1.0, elapsed / span)) if span > 0 else 0.0

    return {
        "resting": False,
        "name": next_name,
        "iqama": next_pt.iqama.isoformat(),
        "previous_name": prev_name,
        "previous_iqama": prev_pt.iqama.isoformat(),
        "progress": progress,
    }
