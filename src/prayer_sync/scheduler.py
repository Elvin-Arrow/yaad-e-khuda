"""In-process daily scheduler, started by `python -m prayer_sync serve`.

Replaces cron as the primary way the daily fetch-then-sync runs: as long
as the server process is up, this fires service.run_daily() once a day
at config.schedule.time. Cron remains available as a fallback for anyone
who'd rather not keep the server running (see README) -- it just calls
the same `fetch`/`sync` CLI subcommands it always did.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import service
from .config import DEFAULT_SCHEDULE_TIME, is_valid_hhmm, load_config
from .errors import ConfigError

JOB_ID = "daily-prayer-sync"

_scheduler: BackgroundScheduler | None = None
_config_path: str | None = None


def _trigger_for(hhmm: str) -> CronTrigger:
    if not is_valid_hhmm(hhmm):
        raise ConfigError(f"schedule time must be 'HH:MM' 24h format, got {hhmm!r}")
    hour, minute = (int(part) for part in hhmm.split(":"))
    return CronTrigger(hour=hour, minute=minute)


def _run_job() -> None:
    # config_path is fixed at start(); the config file itself (mosque,
    # icloud, prayers) is still re-read fresh on every fire, same as the
    # CLI always did -- only the schedule *time* needs an explicit
    # reschedule() call to change without restarting the process.
    service.run_daily(_config_path)


def start(config_path: str) -> BackgroundScheduler:
    """Start the scheduler. Safe to call even before onboarding is
    complete: falls back to the default time, and a job firing against
    an incomplete config just records a ConfigError in last_run.json
    (via run_daily -> run_fetch) rather than crashing anything.
    """
    global _scheduler, _config_path
    _config_path = config_path

    try:
        time_str = load_config(config_path).schedule.time
    except Exception:
        time_str = DEFAULT_SCHEDULE_TIME

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_job, trigger=_trigger_for(time_str), id=JOB_ID, replace_existing=True
    )
    _scheduler.start()
    return _scheduler


def reschedule(new_time: str) -> None:
    """Move the daily job to a new time without restarting the server.
    Called by PUT /api/config/schedule right after it persists the new
    time to config.yaml.
    """
    if _scheduler is None:
        return  # not started (e.g. under tests importing api.py directly)
    _scheduler.reschedule_job(JOB_ID, trigger=_trigger_for(new_time))


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
