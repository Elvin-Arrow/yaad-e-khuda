"""The actual fetch/sync business logic, shared by the CLI, the API, and
the in-process scheduler.

Deliberately has no logging or sys.exit side effects (unlike the old
cli.py, which owned both) -- callers get a plain result back and decide
what to do with it: cli.py logs it and maps it to an exit code, api.py
turns it into a JSON response, scheduler.py writes it to last_run.json.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

from . import caldav_sync
from .config import CANONICAL_PRAYERS, Config, load_config
from .errors import PrayerSyncError
from .mawaqit import extract_conf_data, fetch_html, today_prayer_times
from .state import PrayerTime, load_state, save_state

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
    except Exception as e:  # noqa: BLE001 - never let an unanticipated error propagate raw
        return RunResult(ok=False, message=f"fetch failed with an unexpected error: {e}")

    return RunResult(
        ok=True,
        message=f"fetched {len(prayer_times)} prayer times for {today} -> {config.state_file}",
    )


def run_sync(config_path: str) -> RunResult:
    try:
        config = load_config(config_path)
        today = date.today()
        state = load_state(config.state_file, today)

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
        return RunResult(ok=False, message=f"sync failed: {e}")
    except Exception as e:  # noqa: BLE001 - never let an unanticipated error propagate raw
        return RunResult(ok=False, message=f"sync failed with an unexpected error: {e}")

    return RunResult(
        ok=True,
        message=f"synced calendar {config.icloud.calendar_name!r} for {today}",
    )


def run_daily(config_path: str) -> dict:
    """Fetch, then sync only if the fetch succeeded -- mirrors the `&&`
    chaining the cron setup used, now owned by the scheduler/API instead.
    Always records the outcome to LAST_RUN_FILE so the UI has something
    to show even for a run nobody was watching live.
    """
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
    """Live snapshot of today's prayer times for display in the UI --
    fetched fresh, independent of state.json (which exists purely to
    hand today's numbers from the fetcher to the calendar sync).
    """
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
        "prayers": {
            name: {"adhan": pt.adhan.isoformat(), "iqama": pt.iqama.isoformat()}
            for name, pt in prayer_times.items()
        },
        "next_prayer": next_prayer,
    }


def _find_next_prayer(
    config: Config, prayer_times: dict[str, PrayerTime], now: datetime
) -> dict | None:
    """Which enabled prayer is next, and which was previous -- computed
    within today only (see the plan's noted scope cut: no fetching
    tomorrow's row). Returns None if no prayer is enabled at all, or a
    dict with a "resting" state if we're before the first or after the
    last enabled prayer of the day.
    """
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
        return {
            "resting": True,
            "name": next_name,
            "iqama": next_pt.iqama.isoformat(),
            "previous_name": None,
            "previous_iqama": None,
            "progress": None,
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
