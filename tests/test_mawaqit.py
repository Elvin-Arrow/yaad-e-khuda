import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from prayer_sync.errors import MawaqitError
from prayer_sync.mawaqit import CANONICAL_PRAYERS, extract_conf_data, today_prayer_times

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "mosque_sample.html")


@pytest.fixture
def fixture_html() -> str:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def conf(fixture_html: str) -> dict:
    return extract_conf_data(fixture_html)


def test_extract_conf_data_finds_expected_keys(conf: dict) -> None:
    assert conf["timezone"] == "Europe/Paris"
    assert "calendar" in conf
    assert "iqamaCalendar" in conf


def test_extract_conf_data_raises_when_marker_missing() -> None:
    with pytest.raises(MawaqitError):
        extract_conf_data("<html><body>no data here</body></html>")


def test_extract_conf_data_raises_on_truncated_json() -> None:
    html = "<script>var confData = {\"calendar\": [</script>"
    with pytest.raises(MawaqitError):
        extract_conf_data(html)


def test_today_prayer_times_computes_adhan_and_iqama(conf: dict) -> None:
    today = datetime(2026, 1, 1).date()
    times = today_prayer_times(conf, today)

    assert set(times.keys()) == set(CANONICAL_PRAYERS)

    tz = ZoneInfo("Europe/Paris")
    expected_adhan = {
        "fajr": datetime(2026, 1, 1, 5, 52, tzinfo=tz),
        "dhuhr": datetime(2026, 1, 1, 13, 58, tzinfo=tz),
        "asr": datetime(2026, 1, 1, 17, 32, tzinfo=tz),
        "maghrib": datetime(2026, 1, 1, 20, 12, tzinfo=tz),
        "isha": datetime(2026, 1, 1, 21, 42, tzinfo=tz),
    }
    expected_offsets = {
        "fajr": 10,
        "dhuhr": 5,
        "asr": 15,
        "maghrib": 5,
        "isha": 10,
    }

    for name in CANONICAL_PRAYERS:
        assert times[name].adhan == expected_adhan[name]
        assert times[name].adhan.tzinfo.key == "Europe/Paris"
        assert times[name].iqama == expected_adhan[name] + timedelta(
            minutes=expected_offsets[name]
        )


def test_today_prayer_times_uses_timezone_override(conf: dict) -> None:
    today = datetime(2026, 1, 1).date()
    times = today_prayer_times(conf, today, tz_override="Asia/Karachi")
    assert times["fajr"].adhan.tzinfo.key == "Asia/Karachi"


def test_today_prayer_times_raises_for_missing_day(conf: dict) -> None:
    with pytest.raises(MawaqitError):
        today_prayer_times(conf, datetime(2026, 1, 15).date())


_MIXED_SHAPE_HTML = """
<script>
var confData = {"timezone":"Europe/London","calendar":[{"1":["04:46","06:18","13:04","16:37","19:39","20:51"]}],"iqamaCalendar":[{"1":["05:15","13:30","18:00","+5","21:15"]}]};
</script>
"""


def test_today_prayer_times_handles_mixed_offset_and_fixed_iqama() -> None:
    conf = extract_conf_data(_MIXED_SHAPE_HTML)
    tz = ZoneInfo("Europe/London")
    today = datetime(2026, 1, 1).date()

    times = today_prayer_times(conf, today)

    assert times["fajr"].iqama == datetime(2026, 1, 1, 5, 15, tzinfo=tz)
    assert times["dhuhr"].iqama == datetime(2026, 1, 1, 13, 30, tzinfo=tz)
    assert times["asr"].iqama == datetime(2026, 1, 1, 18, 0, tzinfo=tz)
    assert times["isha"].iqama == datetime(2026, 1, 1, 21, 15, tzinfo=tz)

    assert times["maghrib"].adhan == datetime(2026, 1, 1, 19, 39, tzinfo=tz)
    assert times["maghrib"].iqama == datetime(2026, 1, 1, 19, 44, tzinfo=tz)
