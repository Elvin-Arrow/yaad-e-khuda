from datetime import date
from pathlib import Path

import pytest

from prayer_sync.errors import ProviderError
from prayer_sync.providers import get_provider
from prayer_sync.providers.mawaqit import MawaqitPrayerProvider
import prayer_sync.providers.mawaqit as mawaqit


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mosque_sample.html"


def test_mawaqit_provider_normalizes_fixture_data(monkeypatch) -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    monkeypatch.setattr(mawaqit, "fetch_html", lambda identifier: html)

    result = MawaqitPrayerProvider().fetch_prayer_times("test-mosque", date(2026, 1, 1))

    assert result.timezone == "Europe/Paris"
    assert result.mosque_name == "Test Mosque"
    assert result.prayers["fajr"].adhan.isoformat() == "2026-01-01T05:52:00+01:00"
    assert result.prayers["fajr"].iqama.isoformat() == "2026-01-01T06:02:00+01:00"


def test_registry_resolves_mawaqit() -> None:
    assert isinstance(get_provider("mawaqit"), MawaqitPrayerProvider)


def test_registry_rejects_unknown_provider() -> None:
    with pytest.raises(ProviderError, match="unknown prayer-time provider 'not-a-provider'"):
        get_provider("not-a-provider")
