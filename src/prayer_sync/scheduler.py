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
    service.run_daily(_config_path)


def start(config_path: str) -> BackgroundScheduler:
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
    if _scheduler is None:
        return
    _scheduler.reschedule_job(JOB_ID, trigger=_trigger_for(new_time))


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
