from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from prayer_sync import scheduler
from prayer_sync.errors import ConfigError


def _next_fire(trigger):
    return trigger.get_next_fire_time(None, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))


def test_trigger_for_valid_time() -> None:
    trigger = scheduler._trigger_for("03:15")
    fire = _next_fire(trigger)
    assert (fire.hour, fire.minute) == (3, 15)


@pytest.mark.parametrize("bad", ["25:00", "03:60", "not-a-time", "3:15", ""])
def test_trigger_for_rejects_bad_format(bad: str) -> None:
    with pytest.raises(ConfigError):
        scheduler._trigger_for(bad)


def test_reschedule_calls_scheduler_reschedule_job(monkeypatch) -> None:
    fake_scheduler = MagicMock()
    monkeypatch.setattr(scheduler, "_scheduler", fake_scheduler)

    scheduler.reschedule("04:30")

    assert fake_scheduler.reschedule_job.called
    args, kwargs = fake_scheduler.reschedule_job.call_args
    assert args[0] == scheduler.JOB_ID
    fire = _next_fire(kwargs["trigger"])
    assert (fire.hour, fire.minute) == (4, 30)


def test_reschedule_is_noop_when_scheduler_not_started(monkeypatch) -> None:
    monkeypatch.setattr(scheduler, "_scheduler", None)
    scheduler.reschedule("05:00")
