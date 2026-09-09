from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import yaml

from .errors import ConfigError

CANONICAL_PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")

DEFAULT_CALENDAR_NAME = "Prayer Reminders"
DEFAULT_GOOGLE_CALENDAR_NAME = "Prayer Reminders"
DEFAULT_MINUTES_BEFORE = 10
DEFAULT_STATE_FILE = "state/today.json"
DEFAULT_SCHEDULE_TIME = "03:00"

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class MosqueConfig:
    slug: str
    timezone_override: str | None = None


@dataclass(frozen=True)
class ICloudConfig:
    apple_id: str
    app_specific_password: str
    calendar_name: str

    def __repr__(self) -> str:
        return (
            f"ICloudConfig(apple_id={self.apple_id!r}, "
            f"app_specific_password='***REDACTED***', "
            f"calendar_name={self.calendar_name!r})"
        )


@dataclass(frozen=True)
class GoogleConfig:
    calendar_name: str
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    enabled: bool = True

    def __repr__(self) -> str:
        return (
            f"GoogleConfig(client_id={self.client_id!r}, "
            f"client_secret='***REDACTED***', "
            f"refresh_token='***REDACTED***', "
            f"calendar_name={self.calendar_name!r}, "
            f"enabled={self.enabled!r})"
        )


@dataclass(frozen=True)
class PrayerConfig:
    enabled: bool
    minutes_before: int


@dataclass(frozen=True)
class ScheduleConfig:
    time: str = DEFAULT_SCHEDULE_TIME


@dataclass(frozen=True)
class Config:
    mosque: MosqueConfig
    icloud: ICloudConfig | None = None
    google: GoogleConfig | None = None
    prayers: dict[str, PrayerConfig] = field(default_factory=dict)
    state_file: str = DEFAULT_STATE_FILE
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)


def is_valid_hhmm(value: str) -> bool:
    return bool(_HHMM_RE.match(value))


def _require(d: dict, key: str, context: str) -> object:
    if key not in d or d[key] in (None, ""):
        raise ConfigError(f"config: missing required field '{key}' in {context}")
    return d[key]


def load_config(path: str) -> Config:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(
            f"config file not found: {path} "
            f"(copy config.example.yaml to config.yaml to get started)"
        ) from e
    except yaml.YAMLError as e:
        raise ConfigError(f"config file is not valid YAML: {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"config file is empty or not a mapping: {path}")

    mosque_raw = raw.get("mosque") or {}
    mosque = MosqueConfig(
        slug=str(_require(mosque_raw, "slug", "mosque")),
        timezone_override=mosque_raw.get("timezone_override"),
    )

    icloud_raw = raw.get("icloud") or {}
    icloud: ICloudConfig | None = None
    if icloud_raw:
        icloud = ICloudConfig(
            apple_id=str(_require(icloud_raw, "apple_id", "icloud")),
            app_specific_password=str(
                _require(icloud_raw, "app_specific_password", "icloud")
            ),
            calendar_name=str(_require(icloud_raw, "calendar_name", "icloud")),
        )

    google_raw = raw.get("google") or {}
    google: GoogleConfig | None = None
    if google_raw:
        google = GoogleConfig(
            calendar_name=str(
                google_raw.get("calendar_name") or DEFAULT_GOOGLE_CALENDAR_NAME
            ),
            client_id=google_raw.get("client_id"),
            client_secret=google_raw.get("client_secret"),
            refresh_token=google_raw.get("refresh_token"),
            enabled=bool(google_raw.get("enabled", True)),
        )

    prayers_raw = raw.get("prayers") or {}
    prayers: dict[str, PrayerConfig] = {}
    for name in CANONICAL_PRAYERS:
        p = prayers_raw.get(name)
        if not p:
            raise ConfigError(f"config: missing 'prayers.{name}' section")
        try:
            enabled = bool(p["enabled"])
            minutes_before = int(p["minutes_before"])
        except (KeyError, TypeError, ValueError) as e:
            raise ConfigError(
                f"config: prayers.{name} needs boolean 'enabled' and "
                f"integer 'minutes_before'"
            ) from e
        if minutes_before < 0:
            raise ConfigError(
                f"config: prayers.{name}.minutes_before must be >= 0"
            )
        prayers[name] = PrayerConfig(enabled=enabled, minutes_before=minutes_before)

    state_file = str(raw.get("state_file") or DEFAULT_STATE_FILE)

    schedule_raw = raw.get("schedule") or {}
    schedule_time = str(schedule_raw.get("time") or DEFAULT_SCHEDULE_TIME)
    if not is_valid_hhmm(schedule_time):
        raise ConfigError(
            f"config: schedule.time must be 'HH:MM' 24h format, got {schedule_time!r}"
        )
    schedule = ScheduleConfig(time=schedule_time)

    return Config(
        mosque=mosque,
        icloud=icloud,
        google=google,
        prayers=prayers,
        state_file=state_file,
        schedule=schedule,
    )


def config_exists(path: str) -> bool:
    return os.path.isfile(path)


def read_raw(path: str) -> dict:
    if not config_exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"config file is not valid YAML: {path}: {e}") from e
    return raw if isinstance(raw, dict) else {}


def write_raw(path: str, data: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def merge_raw(path: str, updates: dict) -> dict:
    raw = read_raw(path)
    for section, value in updates.items():
        if isinstance(value, dict) and isinstance(raw.get(section), dict):
            raw[section] = {**raw[section], **value}
        else:
            raw[section] = value
    write_raw(path, raw)
    return raw


def onboarding_status(path: str) -> dict:
    raw = read_raw(path)
    icloud = raw.get("icloud") or {}
    google = raw.get("google") or {}
    mosque = raw.get("mosque") or {}
    has_icloud = bool(icloud.get("apple_id")) and bool(
        icloud.get("app_specific_password")
    )
    has_google = bool(google.get("refresh_token"))
    has_mosque = bool(mosque.get("slug"))
    return {
        "has_icloud": has_icloud,
        "has_google": has_google,
        "has_mosque": has_mosque,
        "complete": (has_icloud or has_google) and has_mosque,
    }


def default_prayers_section() -> dict:
    return {
        name: {"enabled": True, "minutes_before": DEFAULT_MINUTES_BEFORE}
        for name in CANONICAL_PRAYERS
    }
