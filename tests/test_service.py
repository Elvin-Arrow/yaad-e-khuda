import os
from datetime import date, datetime

import pytest

from prayer_sync import service
from prayer_sync.config import default_prayers_section, load_config, merge_raw

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "mosque_sample.html")


class _FixedDate(date):
    @classmethod
    def today(cls):
        return date(2026, 1, 1)


@pytest.fixture
def fixture_html() -> str:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def config_path(tmp_path, monkeypatch) -> str:
    monkeypatch.chdir(tmp_path)
    path = "config.yaml"
    merge_raw(
        path,
        {
            "icloud": {
                "apple_id": "a@b.com",
                "app_specific_password": "pw",
                "calendar_name": "Prayer Reminders",
            },
            "mosque": {"slug": "test-mosque", "timezone_override": None},
            "prayers": default_prayers_section(),
            "state_file": "state/today.json",
            "schedule": {"time": "03:00"},
        },
    )
    return path


def test_run_fetch_success_writes_state(config_path, fixture_html, monkeypatch) -> None:
    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)

    result = service.run_fetch(config_path)

    assert result.ok
    assert os.path.exists("state/today.json")


def test_run_fetch_failure_does_not_crash(config_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "fetch_html", lambda slug: "<html>no confData here</html>")

    result = service.run_fetch(config_path)

    assert not result.ok
    assert "fetch failed" in result.message
    assert not os.path.exists("state/today.json")


def test_run_sync_fails_without_state(config_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "date", _FixedDate)

    result = service.run_sync(config_path)

    assert not result.ok
    assert "sync failed" in result.message


def test_run_sync_upserts_all_enabled_prayers(config_path, fixture_html, monkeypatch) -> None:
    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)
    assert service.run_fetch(config_path).ok

    calls: list[tuple[str, tuple]] = []
    monkeypatch.setattr(service.caldav_sync, "connect", lambda apple_id, pw: "PRINCIPAL")
    monkeypatch.setattr(
        service.caldav_sync, "get_or_create_calendar", lambda principal, name: "CALENDAR"
    )
    monkeypatch.setattr(
        service.caldav_sync, "upsert_event", lambda *a, **k: calls.append(("upsert", a))
    )
    monkeypatch.setattr(
        service.caldav_sync,
        "delete_event_if_exists",
        lambda *a, **k: calls.append(("delete", a)),
    )

    result = service.run_sync(config_path)

    assert result.ok
    assert len([c for c in calls if c[0] == "upsert"]) == 5
    assert len([c for c in calls if c[0] == "delete"]) == 0


def test_run_daily_skips_sync_when_fetch_fails(config_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(
        service,
        "fetch_html",
        lambda slug: (_ for _ in ()).throw(Exception("network down")),
    )
    sync_calls = []
    monkeypatch.setattr(
        service,
        "run_sync",
        lambda cp: sync_calls.append(cp) or service.RunResult(ok=True, message="should not run"),
    )

    status = service.run_daily(config_path)

    assert status["ok"] is False
    assert status["fetch"]["ok"] is False
    assert status["sync"] is None
    assert sync_calls == []

    recorded = service.last_run_status()
    assert recorded["ok"] is False


def test_last_run_status_placeholder_when_never_run(config_path) -> None:
    status = service.last_run_status()
    assert status == {"ran_at": None, "fetch": None, "sync": None, "ok": None}


def test_today_preview_reports_mosque_name(
    config_path, fixture_html, monkeypatch
) -> None:
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)

    real_datetime = service.datetime

    class _FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 1, 1, 5, 0, tzinfo=tz)

    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "datetime", _FixedDateTime)

    config = load_config(config_path)
    preview = service.today_preview(config)

    assert preview["mosque_name"] == "Test Mosque"


def test_today_preview_reports_progress_before_first_prayer(
    config_path, fixture_html, monkeypatch
) -> None:
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)

    real_datetime = service.datetime

    class _FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 1, 1, 5, 0, tzinfo=tz)

    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "datetime", _FixedDateTime)

    config = load_config(config_path)
    preview = service.today_preview(config)

    next_prayer = preview["next_prayer"]
    assert next_prayer["name"] == "fajr"
    assert next_prayer["resting"] is False
    assert 0.0 < next_prayer["progress"] < 1.0


def test_today_preview_reports_progress_between_prayers(
    config_path, fixture_html, monkeypatch
) -> None:
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)

    real_datetime = service.datetime

    class _FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 1, 1, 10, 0, tzinfo=tz)

    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "datetime", _FixedDateTime)

    config = load_config(config_path)
    preview = service.today_preview(config)

    next_prayer = preview["next_prayer"]
    assert next_prayer["name"] == "dhuhr"
    assert next_prayer["previous_name"] == "fajr"
    assert next_prayer["resting"] is False
    assert 0.0 < next_prayer["progress"] < 1.0


def test_today_preview_reports_resting_after_last_prayer(
    config_path, fixture_html, monkeypatch
) -> None:
    monkeypatch.setattr(service, "fetch_html", lambda slug: fixture_html)

    real_datetime = service.datetime

    class _FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 1, 1, 23, 0, tzinfo=tz)

    monkeypatch.setattr(service, "date", _FixedDate)
    monkeypatch.setattr(service, "datetime", _FixedDateTime)

    config = load_config(config_path)
    preview = service.today_preview(config)

    next_prayer = preview["next_prayer"]
    assert next_prayer["resting"] is True
    assert next_prayer["iqama"] is None
    assert next_prayer["progress"] is None
