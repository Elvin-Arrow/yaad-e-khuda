from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from prayer_sync.errors import StateError
from prayer_sync.state import PrayerTime, load_state, save_state


def test_save_load_round_trip_preserves_wallclock_and_zone(tmp_path) -> None:
    """Regression test for the exact pitfall docs/idea.md calls out:
    datetime.fromisoformat() on a round-tripped UTC-offset string loses
    the IANA zone name. This must survive save -> load with the zone
    identity intact, not just the correct UTC instant.
    """
    path = str(tmp_path / "today.json")
    tz = ZoneInfo("Europe/Paris")
    day = date(2026, 7, 1)  # July: Europe/Paris is in DST (+02:00)

    prayer_times = {
        "fajr": PrayerTime(
            adhan=datetime(2026, 7, 1, 5, 52, tzinfo=tz),
            iqama=datetime(2026, 7, 1, 6, 2, tzinfo=tz),
        ),
    }

    save_state(path, day, "Europe/Paris", prayer_times)
    loaded = load_state(path, day)

    assert loaded.tz_name == "Europe/Paris"
    assert loaded.prayers["fajr"].adhan == prayer_times["fajr"].adhan
    assert loaded.prayers["fajr"].iqama == prayer_times["fajr"].iqama
    # Not just "same instant" -- the zone name itself must have survived.
    assert loaded.prayers["fajr"].adhan.tzinfo.key == "Europe/Paris"
    assert loaded.prayers["fajr"].iqama.tzinfo.key == "Europe/Paris"


def test_load_state_rejects_stale_date(tmp_path) -> None:
    path = str(tmp_path / "today.json")
    tz = ZoneInfo("Europe/Paris")
    yesterday = date(2026, 7, 1)
    today = date(2026, 7, 2)

    prayer_times = {
        "fajr": PrayerTime(
            adhan=datetime(2026, 7, 1, 5, 52, tzinfo=tz),
            iqama=datetime(2026, 7, 1, 6, 2, tzinfo=tz),
        ),
    }
    save_state(path, yesterday, "Europe/Paris", prayer_times)

    with pytest.raises(StateError):
        load_state(path, today)


def test_load_state_missing_file_raises(tmp_path) -> None:
    with pytest.raises(StateError):
        load_state(str(tmp_path / "does-not-exist.json"), date(2026, 7, 1))


def test_save_state_is_atomic_and_leaves_no_tmp_file(tmp_path) -> None:
    path = str(tmp_path / "today.json")
    tz = ZoneInfo("Europe/Paris")
    day = date(2026, 7, 1)
    prayer_times = {
        "fajr": PrayerTime(
            adhan=datetime(2026, 7, 1, 5, 52, tzinfo=tz),
            iqama=datetime(2026, 7, 1, 6, 2, tzinfo=tz),
        ),
    }
    save_state(path, day, "Europe/Paris", prayer_times)
    assert not (tmp_path / "today.json.tmp").exists()
    assert (tmp_path / "today.json").exists()
