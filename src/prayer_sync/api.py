from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, RootModel

from . import caldav_sync, google_calendar_sync, service
from .config import (
    CANONICAL_PRAYERS,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_GOOGLE_CALENDAR_NAME,
    DEFAULT_SCHEDULE_TIME,
    DEFAULT_STATE_FILE,
    default_prayers_section,
    is_valid_hhmm,
    load_config,
    merge_raw,
    onboarding_status,
    read_raw,
)
from .errors import PrayerSyncError
from .mawaqit import extract_conf_data, fetch_html, today_prayer_times

# Pending OAuth "state" tokens, keyed to themselves -- this is a single-user,
# single-process app (same assumption the rest of the API makes), so an
# in-memory set is enough to defend the callback against CSRF without a
# session store.
_pending_oauth_states: set[str] = set()


class ICloudSetupRequest(BaseModel):
    apple_id: str
    app_specific_password: str


class MosqueSetupRequest(BaseModel):
    slug: str


class ICloudUpdateRequest(BaseModel):
    apple_id: str | None = None
    calendar_name: str | None = None
    app_specific_password: str | None = None


class MosqueUpdateRequest(BaseModel):
    slug: str | None = None
    timezone_override: str | None = None


class PrayerUpdate(BaseModel):
    enabled: bool
    minutes_before: int


class PrayersUpdateRequest(RootModel[dict[str, PrayerUpdate]]):
    pass


class ScheduleUpdateRequest(BaseModel):
    time: str


class GoogleUpdateRequest(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    calendar_name: str | None = None


def _prayer_times_response(prayer_times: dict) -> dict:
    return {
        name: {"adhan": pt.adhan.isoformat(), "iqama": pt.iqama.isoformat()}
        for name, pt in prayer_times.items()
    }


def create_app(config_path: str = "config.yaml") -> FastAPI:
    app = FastAPI(title="Prayer Time Sync")

    @app.exception_handler(PrayerSyncError)
    async def _handle_prayer_sync_error(_request, exc: PrayerSyncError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/api/setup/status")
    def setup_status():
        return onboarding_status(config_path)

    @app.post("/api/setup/icloud")
    def setup_icloud(body: ICloudSetupRequest):
        caldav_sync.connect(body.apple_id, body.app_specific_password)
        merge_raw(
            config_path,
            {
                "icloud": {
                    "apple_id": body.apple_id,
                    "app_specific_password": body.app_specific_password,
                    "calendar_name": DEFAULT_CALENDAR_NAME,
                }
            },
        )
        return {"ok": True}

    @app.post("/api/setup/mosque")
    def setup_mosque(body: MosqueSetupRequest):
        html = fetch_html(body.slug)
        conf = extract_conf_data(html)
        prayer_times = today_prayer_times(conf, date.today())

        merge_raw(
            config_path,
            {
                "mosque": {"slug": body.slug, "timezone_override": None},
                "prayers": default_prayers_section(),
                "state_file": DEFAULT_STATE_FILE,
                "schedule": {"time": DEFAULT_SCHEDULE_TIME},
            },
        )
        return {
            "ok": True,
            "timezone": conf.get("timezone"),
            "preview": _prayer_times_response(prayer_times),
        }

    @app.get("/api/config")
    def get_config():
        config = load_config(config_path)
        return {
            "mosque": {
                "slug": config.mosque.slug,
                "timezone_override": config.mosque.timezone_override,
            },
            "icloud": (
                {
                    "apple_id": config.icloud.apple_id,
                    "calendar_name": config.icloud.calendar_name,
                    "has_password": True,
                }
                if config.icloud
                else None
            ),
            "google": {
                "configured": bool(config.google and config.google.client_id and config.google.client_secret),
                "connected": bool(config.google and config.google.refresh_token),
                "calendar_name": config.google.calendar_name if config.google else DEFAULT_GOOGLE_CALENDAR_NAME,
                "client_id": config.google.client_id if config.google else None,
            },
            "prayers": {
                name: {"enabled": p.enabled, "minutes_before": p.minutes_before}
                for name, p in config.prayers.items()
            },
            "schedule": {"time": config.schedule.time},
        }

    @app.put("/api/config/icloud")
    def update_icloud(body: ICloudUpdateRequest):
        config = load_config(config_path)
        apple_id = body.apple_id or (config.icloud.apple_id if config.icloud else None)
        calendar_name = body.calendar_name or (
            config.icloud.calendar_name if config.icloud else DEFAULT_CALENDAR_NAME
        )
        password = body.app_specific_password or (
            config.icloud.app_specific_password if config.icloud else None
        )
        if not apple_id or not password:
            raise HTTPException(400, "apple_id and app_specific_password are required")

        caldav_sync.connect(apple_id, password)
        merge_raw(
            config_path,
            {
                "icloud": {
                    "apple_id": apple_id,
                    "calendar_name": calendar_name,
                    "app_specific_password": password,
                }
            },
        )
        return {"ok": True}

    @app.put("/api/config/google")
    def update_google(body: GoogleUpdateRequest):
        raw = read_raw(config_path)
        existing = raw.get("google") or {}
        client_id = body.client_id or existing.get("client_id")
        client_secret = body.client_secret or existing.get("client_secret")
        calendar_name = body.calendar_name or existing.get("calendar_name") or DEFAULT_GOOGLE_CALENDAR_NAME

        merge_raw(
            config_path,
            {
                "google": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "calendar_name": calendar_name,
                }
            },
        )
        return {"ok": True}

    @app.get("/api/google/oauth/start")
    def google_oauth_start(request: Request):
        raw = read_raw(config_path)
        google_raw = raw.get("google") or {}
        client_id = google_raw.get("client_id")
        client_secret = google_raw.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(
                400, "save a Google Client ID and Client Secret before connecting"
            )

        redirect_uri = str(request.base_url) + "api/google/oauth/callback"
        state = secrets.token_urlsafe(24)
        _pending_oauth_states.add(state)

        auth_url = google_calendar_sync.build_auth_url(client_id, redirect_uri, state)
        return RedirectResponse(auth_url)

    @app.get("/api/google/oauth/callback")
    def google_oauth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
        if error:
            raise HTTPException(400, f"Google declined the connection: {error}")
        if not state or state not in _pending_oauth_states:
            raise HTTPException(400, "invalid or expired OAuth state")
        _pending_oauth_states.discard(state)
        if not code:
            raise HTTPException(400, "Google did not return an authorization code")

        raw = read_raw(config_path)
        google_raw = raw.get("google") or {}
        client_id = google_raw.get("client_id")
        client_secret = google_raw.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(400, "Google Client ID/Secret are no longer configured")

        redirect_uri = str(request.base_url) + "api/google/oauth/callback"
        tokens = google_calendar_sync.exchange_code(client_id, client_secret, code, redirect_uri)
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                400,
                "Google did not return a refresh token -- disconnect this app's access at "
                "myaccount.google.com/permissions and try connecting again",
            )

        merge_raw(config_path, {"google": {"refresh_token": refresh_token, "enabled": True}})
        return RedirectResponse("/?google=connected")

    @app.post("/api/config/google/disconnect")
    def disconnect_google():
        raw = read_raw(config_path)
        google_raw = raw.get("google") or {}
        refresh_token = google_raw.get("refresh_token")
        if refresh_token:
            google_calendar_sync.revoke(refresh_token)
        merge_raw(config_path, {"google": {"refresh_token": None, "enabled": False}})
        return {"ok": True}

    @app.put("/api/config/mosque")
    def update_mosque(body: MosqueUpdateRequest):
        config = load_config(config_path)
        slug = body.slug or config.mosque.slug
        timezone_override = (
            body.timezone_override
            if body.timezone_override is not None
            else config.mosque.timezone_override
        )

        if slug != config.mosque.slug:
            extract_conf_data(fetch_html(slug))

        merge_raw(
            config_path,
            {"mosque": {"slug": slug, "timezone_override": timezone_override}},
        )
        return {"ok": True}

    @app.put("/api/config/prayers")
    def update_prayers(body: PrayersUpdateRequest):
        updates = body.root
        for name in updates:
            if name not in CANONICAL_PRAYERS:
                raise HTTPException(400, f"unknown prayer {name!r}")
        for name, p in updates.items():
            if p.minutes_before < 0:
                raise HTTPException(400, f"{name}.minutes_before must be >= 0")

        merge_raw(
            config_path,
            {
                "prayers": {
                    name: {"enabled": p.enabled, "minutes_before": p.minutes_before}
                    for name, p in updates.items()
                }
            },
        )
        return {"ok": True}

    @app.put("/api/config/schedule")
    def update_schedule(body: ScheduleUpdateRequest):
        if not is_valid_hhmm(body.time):
            raise HTTPException(400, "time must be 'HH:MM' 24h format")

        merge_raw(config_path, {"schedule": {"time": body.time}})

        from . import scheduler

        scheduler.reschedule(body.time)
        return {"ok": True}

    @app.get("/api/prayer-times/today")
    def prayer_times_today():
        config = load_config(config_path)
        return service.today_preview(config)

    @app.get("/api/sync/status")
    def sync_status():
        return service.last_run_status()

    @app.post("/api/sync/run")
    def sync_run():
        return service.run_daily(config_path)

    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
