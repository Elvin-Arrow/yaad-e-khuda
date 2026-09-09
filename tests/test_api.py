import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

from prayer_sync import api as api_module
from prayer_sync.config import onboarding_status
from prayer_sync.errors import CalDavSyncError, MawaqitError

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
    return "config.yaml"


@pytest.fixture
def client(config_path) -> TestClient:
    return TestClient(api_module.create_app(config_path))


def test_setup_status_empty_on_fresh_install(client: TestClient) -> None:
    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "has_icloud": False,
        "has_google": False,
        "has_mosque": False,
        "complete": False,
    }


def test_setup_icloud_validates_before_saving(client, config_path, monkeypatch) -> None:
    def fake_connect(apple_id, password):
        raise CalDavSyncError("bad credentials")

    monkeypatch.setattr(api_module.caldav_sync, "connect", fake_connect)

    resp = client.post(
        "/api/setup/icloud",
        json={"apple_id": "a@b.com", "app_specific_password": "wrong"},
    )

    assert resp.status_code == 400
    assert "bad credentials" in resp.json()["detail"]
    assert onboarding_status(config_path)["has_icloud"] is False


def test_setup_icloud_saves_on_success(client, config_path, monkeypatch) -> None:
    monkeypatch.setattr(api_module.caldav_sync, "connect", lambda a, p: "PRINCIPAL")

    resp = client.post(
        "/api/setup/icloud",
        json={"apple_id": "a@b.com", "app_specific_password": "correct"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert onboarding_status(config_path) == {
        "has_icloud": True,
        "has_google": False,
        "has_mosque": False,
        "complete": False,
    }


def test_setup_mosque_rejects_bad_slug(client, config_path, monkeypatch) -> None:
    def fake_fetch_html(slug):
        raise MawaqitError("mosque not found")

    monkeypatch.setattr(api_module, "fetch_html", fake_fetch_html)

    resp = client.post("/api/setup/mosque", json={"slug": "does-not-exist"})

    assert resp.status_code == 400
    assert onboarding_status(config_path)["has_mosque"] is False


def test_setup_mosque_saves_and_returns_preview(
    client, config_path, fixture_html, monkeypatch
) -> None:
    monkeypatch.setattr(api_module, "fetch_html", lambda slug: fixture_html)
    monkeypatch.setattr(api_module, "date", _FixedDate)

    resp = client.post("/api/setup/mosque", json={"slug": "test-mosque"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["timezone"] == "Europe/Paris"
    assert set(body["preview"].keys()) == {"fajr", "dhuhr", "asr", "maghrib", "isha"}
    assert onboarding_status(config_path)["has_mosque"] is True


def _complete_onboarding(client: TestClient, fixture_html: str, monkeypatch) -> None:
    monkeypatch.setattr(api_module.caldav_sync, "connect", lambda a, p: "PRINCIPAL")
    client.post(
        "/api/setup/icloud", json={"apple_id": "a@b.com", "app_specific_password": "pw"}
    )
    monkeypatch.setattr(api_module, "fetch_html", lambda slug: fixture_html)
    monkeypatch.setattr(api_module, "date", _FixedDate)
    monkeypatch.setattr(api_module.service, "date", _FixedDate)
    client.post("/api/setup/mosque", json={"slug": "test-mosque"})


def test_get_config_never_includes_the_password(
    client, fixture_html, monkeypatch
) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    resp = client.get("/api/config")

    assert resp.status_code == 200
    assert "app_specific_password" not in resp.text
    body = resp.json()
    assert body["icloud"]["has_password"] is True
    assert body["mosque"]["slug"] == "test-mosque"
    assert body["schedule"]["time"] == "03:00"


def test_update_prayers_persists_and_validates(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    resp = client.put(
        "/api/config/prayers",
        json={"fajr": {"enabled": False, "minutes_before": 20}},
    )
    assert resp.status_code == 200

    config = client.get("/api/config").json()
    assert config["prayers"]["fajr"] == {"enabled": False, "minutes_before": 20}
    assert config["prayers"]["dhuhr"] == {"enabled": True, "minutes_before": 10}


def test_update_prayers_rejects_negative_minutes(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    resp = client.put(
        "/api/config/prayers", json={"fajr": {"enabled": True, "minutes_before": -5}}
    )

    assert resp.status_code == 400
    config = client.get("/api/config").json()
    assert config["prayers"]["fajr"]["minutes_before"] == 10


def test_update_schedule_validates_format(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    bad = client.put("/api/config/schedule", json={"time": "not-a-time"})
    assert bad.status_code == 400

    good = client.put("/api/config/schedule", json={"time": "04:30"})
    assert good.status_code == 200
    assert client.get("/api/config").json()["schedule"]["time"] == "04:30"


def test_update_icloud_revalidates_and_keeps_password_if_omitted(
    client, fixture_html, monkeypatch
) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    seen_passwords = []

    def fake_connect(apple_id, password):
        seen_passwords.append(password)
        return "PRINCIPAL"

    monkeypatch.setattr(api_module.caldav_sync, "connect", fake_connect)

    resp = client.put("/api/config/icloud", json={"calendar_name": "My Prayers"})

    assert resp.status_code == 200
    assert seen_passwords == ["pw"]
    assert client.get("/api/config").json()["icloud"]["calendar_name"] == "My Prayers"


def test_prayer_times_today(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)
    monkeypatch.setattr(api_module.service, "fetch_html", lambda slug: fixture_html)

    resp = client.get("/api/prayer-times/today")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body["prayers"].keys()) == {"fajr", "dhuhr", "asr", "maghrib", "isha"}


def test_sync_status_placeholder_before_any_run(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)

    resp = client.get("/api/sync/status")

    assert resp.status_code == 200
    assert resp.json()["ok"] is None


def test_update_google_persists_client_credentials(client, config_path) -> None:
    resp = client.put(
        "/api/config/google",
        json={"client_id": "id-123", "client_secret": "secret-456"},
    )

    assert resp.status_code == 200
    from prayer_sync.config import read_raw

    raw = read_raw(config_path)
    assert raw["google"]["client_id"] == "id-123"
    assert raw["google"]["client_secret"] == "secret-456"
    assert raw["google"]["calendar_name"] == "Prayer Reminders"


def test_update_google_keeps_secret_when_omitted(client, config_path) -> None:
    client.put("/api/config/google", json={"client_id": "id-123", "client_secret": "secret-456"})

    resp = client.put("/api/config/google", json={"calendar_name": "My Google Prayers"})

    assert resp.status_code == 200
    from prayer_sync.config import read_raw

    raw = read_raw(config_path)
    assert raw["google"]["client_id"] == "id-123"
    assert raw["google"]["client_secret"] == "secret-456"
    assert raw["google"]["calendar_name"] == "My Google Prayers"


def test_google_oauth_start_requires_client_credentials(client) -> None:
    resp = client.get("/api/google/oauth/start", follow_redirects=False)
    assert resp.status_code == 400


def test_google_oauth_start_redirects_with_derived_redirect_uri(client) -> None:
    client.put("/api/config/google", json={"client_id": "id-123", "client_secret": "secret-456"})

    resp = client.get("/api/google/oauth/start", follow_redirects=False)

    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert "accounts.google.com" in location
    assert "client_id=id-123" in location
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(location).query)
    assert query["redirect_uri"][0] == "http://testserver/api/google/oauth/callback"


def test_google_oauth_callback_rejects_unknown_state(client) -> None:
    resp = client.get(
        "/api/google/oauth/callback", params={"code": "abc", "state": "not-issued"}
    )
    assert resp.status_code == 400


def test_google_oauth_callback_saves_refresh_token(client, config_path, monkeypatch) -> None:
    client.put("/api/config/google", json={"client_id": "id-123", "client_secret": "secret-456"})
    start_resp = client.get("/api/google/oauth/start", follow_redirects=False)
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(start_resp.headers["location"]).query)["state"][0]

    monkeypatch.setattr(
        api_module.google_calendar_sync,
        "exchange_code",
        lambda client_id, client_secret, code, redirect_uri: {"refresh_token": "rt-789"},
    )

    resp = client.get(
        "/api/google/oauth/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/?google=connected"

    from prayer_sync.config import read_raw

    raw = read_raw(config_path)
    assert raw["google"]["refresh_token"] == "rt-789"
    assert onboarding_status(config_path)["has_google"] is True


def test_google_oauth_callback_state_is_single_use(client, config_path, monkeypatch) -> None:
    client.put("/api/config/google", json={"client_id": "id-123", "client_secret": "secret-456"})
    start_resp = client.get("/api/google/oauth/start", follow_redirects=False)
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(start_resp.headers["location"]).query)["state"][0]
    monkeypatch.setattr(
        api_module.google_calendar_sync,
        "exchange_code",
        lambda client_id, client_secret, code, redirect_uri: {"refresh_token": "rt-789"},
    )
    client.get(
        "/api/google/oauth/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    resp = client.get(
        "/api/google/oauth/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code == 400


def test_disconnect_google_clears_refresh_token(client, config_path, monkeypatch) -> None:
    from prayer_sync.config import merge_raw, read_raw

    merge_raw(
        config_path,
        {"google": {"client_id": "id", "client_secret": "secret", "refresh_token": "rt"}},
    )
    monkeypatch.setattr(api_module.google_calendar_sync, "revoke", lambda token: None)

    resp = client.post("/api/config/google/disconnect")

    assert resp.status_code == 200
    raw = read_raw(config_path)
    assert raw["google"]["refresh_token"] is None
    assert onboarding_status(config_path)["has_google"] is False


def test_onboarding_completes_with_google_only(client, config_path, fixture_html, monkeypatch) -> None:
    from prayer_sync.config import merge_raw

    merge_raw(
        config_path,
        {"google": {"client_id": "id", "client_secret": "secret", "refresh_token": "rt"}},
    )
    monkeypatch.setattr(api_module, "fetch_html", lambda slug: fixture_html)
    monkeypatch.setattr(api_module, "date", _FixedDate)

    resp = client.post("/api/setup/mosque", json={"slug": "test-mosque"})

    assert resp.status_code == 200
    assert client.get("/api/setup/status").json()["complete"] is True


def test_get_config_reports_icloud_as_none_when_not_connected(
    client, config_path, fixture_html, monkeypatch
) -> None:
    from prayer_sync.config import merge_raw

    merge_raw(
        config_path,
        {"google": {"client_id": "id", "client_secret": "secret", "refresh_token": "rt"}},
    )
    monkeypatch.setattr(api_module, "fetch_html", lambda slug: fixture_html)
    monkeypatch.setattr(api_module, "date", _FixedDate)
    client.post("/api/setup/mosque", json={"slug": "test-mosque"})

    resp = client.get("/api/config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["icloud"] is None
    assert body["google"]["connected"] is True
    assert "client_secret" not in resp.text
    assert "rt" not in resp.text


def test_sync_run_invokes_service(client, fixture_html, monkeypatch) -> None:
    _complete_onboarding(client, fixture_html, monkeypatch)
    monkeypatch.setattr(
        api_module.service,
        "run_daily",
        lambda config_path: {"ok": True, "fetch": None, "sync": None, "ran_at": "now"},
    )

    resp = client.post("/api/sync/run")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
