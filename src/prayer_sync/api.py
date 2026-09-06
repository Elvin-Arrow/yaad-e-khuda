"""FastAPI backend for the Settings UI.

`create_app(config_path)` is a factory rather than a module-level `app`
singleton so tests (and `cli.cmd_serve`) can point it at an arbitrary
config.yaml path -- see docs/idea.md's "re-read fresh, no caching"
requirement, which this inherits by simply calling load_config()/
read_raw() fresh inside every request handler, same as the CLI always
did.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, RootModel

from . import caldav_sync, service
from .config import (
    CANONICAL_PRAYERS,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_SCHEDULE_TIME,
    DEFAULT_STATE_FILE,
    default_prayers_section,
    is_valid_hhmm,
    load_config,
    merge_raw,
    onboarding_status,
)
from .errors import PrayerSyncError
from .mawaqit import extract_conf_data, fetch_html, today_prayer_times


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

    # --- Onboarding -----------------------------------------------------

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

    # --- Settings (config assumed complete from here down) ---------------

    @app.get("/api/config")
    def get_config():
        config = load_config(config_path)
        return {
            "mosque": {
                "slug": config.mosque.slug,
                "timezone_override": config.mosque.timezone_override,
            },
            "icloud": {
                "apple_id": config.icloud.apple_id,
                "calendar_name": config.icloud.calendar_name,
                "has_password": True,
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
        apple_id = body.apple_id or config.icloud.apple_id
        calendar_name = body.calendar_name or config.icloud.calendar_name
        password = body.app_specific_password or config.icloud.app_specific_password

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
            extract_conf_data(fetch_html(slug))  # raises MawaqitError if bad

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

        from . import scheduler  # lazy: avoids importing apscheduler under plain CLI use

        scheduler.reschedule(body.time)
        return {"ok": True}

    # --- Live data / actions ---------------------------------------------

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

    # --- Serve the built Svelte app in production ------------------------

    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
