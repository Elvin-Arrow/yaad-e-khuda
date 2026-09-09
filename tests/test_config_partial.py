import os
import stat

from prayer_sync.config import (
    CANONICAL_PRAYERS,
    config_exists,
    default_prayers_section,
    load_config,
    merge_raw,
    onboarding_status,
    read_raw,
    write_raw,
)


def test_onboarding_status_empty_when_no_file(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    assert not config_exists(path)
    assert onboarding_status(path) == {
        "has_icloud": False,
        "has_google": False,
        "has_mosque": False,
        "complete": False,
    }


def test_onboarding_status_after_icloud_step(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(path, {"icloud": {"apple_id": "a@b.com", "app_specific_password": "x"}})

    status = onboarding_status(path)
    assert status == {
        "has_icloud": True,
        "has_google": False,
        "has_mosque": False,
        "complete": False,
    }


def test_onboarding_status_after_both_steps(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(
        path,
        {
            "icloud": {
                "apple_id": "a@b.com",
                "app_specific_password": "x",
                "calendar_name": "Prayer Reminders",
            }
        },
    )
    merge_raw(
        path,
        {
            "mosque": {"slug": "some-mosque", "timezone_override": None},
            "prayers": default_prayers_section(),
            "state_file": "state/today.json",
            "schedule": {"time": "03:00"},
        },
    )

    assert onboarding_status(path) == {
        "has_icloud": True,
        "has_google": False,
        "has_mosque": True,
        "complete": True,
    }
    config = load_config(path)
    assert config.mosque.slug == "some-mosque"
    assert set(config.prayers.keys()) == set(CANONICAL_PRAYERS)
    assert config.schedule.time == "03:00"


def test_onboarding_status_complete_with_google_only(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(path, {"google": {"client_id": "id", "client_secret": "secret", "refresh_token": "rt"}})
    merge_raw(
        path,
        {
            "mosque": {"slug": "some-mosque", "timezone_override": None},
            "prayers": default_prayers_section(),
            "state_file": "state/today.json",
            "schedule": {"time": "03:00"},
        },
    )

    assert onboarding_status(path) == {
        "has_icloud": False,
        "has_google": True,
        "has_mosque": True,
        "complete": True,
    }
    config = load_config(path)
    assert config.icloud is None
    assert config.google.refresh_token == "rt"


def test_load_config_icloud_absent_is_none(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(
        path,
        {
            "mosque": {"slug": "some-mosque", "timezone_override": None},
            "prayers": default_prayers_section(),
            "state_file": "state/today.json",
            "schedule": {"time": "03:00"},
        },
    )

    config = load_config(path)

    assert config.icloud is None
    assert config.google is None


def test_load_config_google_round_trips_through_merge_raw(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(
        path,
        {
            "mosque": {"slug": "some-mosque", "timezone_override": None},
            "prayers": default_prayers_section(),
            "state_file": "state/today.json",
            "schedule": {"time": "03:00"},
            "google": {
                "client_id": "id-123",
                "client_secret": "secret-456",
                "calendar_name": "My Google Calendar",
            },
        },
    )

    config = load_config(path)

    assert config.google.client_id == "id-123"
    assert config.google.client_secret == "secret-456"
    assert config.google.calendar_name == "My Google Calendar"
    assert config.google.refresh_token is None


def test_merge_raw_does_not_clobber_other_sections(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(path, {"icloud": {"apple_id": "a@b.com", "app_specific_password": "x"}})
    merge_raw(path, {"mosque": {"slug": "some-mosque"}})

    raw = read_raw(path)
    assert raw["icloud"]["apple_id"] == "a@b.com"
    assert raw["mosque"]["slug"] == "some-mosque"


def test_merge_raw_updates_only_named_keys_within_a_section(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    merge_raw(
        path,
        {"icloud": {"apple_id": "a@b.com", "app_specific_password": "x", "calendar_name": "Prayer Reminders"}},
    )
    merge_raw(path, {"icloud": {"calendar_name": "My Prayers"}})

    raw = read_raw(path)
    assert raw["icloud"]["apple_id"] == "a@b.com"
    assert raw["icloud"]["app_specific_password"] == "x"
    assert raw["icloud"]["calendar_name"] == "My Prayers"


def test_write_raw_sets_permissions_600(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    write_raw(path, {"icloud": {"apple_id": "a@b.com"}})

    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_write_raw_is_atomic_and_leaves_no_tmp_file(tmp_path) -> None:
    path = str(tmp_path / "config.yaml")
    write_raw(path, {"mosque": {"slug": "x"}})

    assert not (tmp_path / "config.yaml.tmp").exists()
    assert (tmp_path / "config.yaml").exists()
