"""Config loading.

Re-read fresh on every call to load_config() -- never cache across runs
(docs/idea.md #3.3), so an edit to config.yaml always takes effect on the
next fetch/sync without needing a restart of anything.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import yaml

from .errors import ConfigError

CANONICAL_PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")

DEFAULT_CALENDAR_NAME = "Prayer Reminders"
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

    def __repr__(self) -> str:  # never let the password leak into a log/print
        return (
            f"ICloudConfig(apple_id={self.apple_id!r}, "
            f"app_specific_password='***REDACTED***', "
            f"calendar_name={self.calendar_name!r})"
        )


@dataclass(frozen=True)
class PrayerConfig:
    enabled: bool
    minutes_before: int


@dataclass(frozen=True)
class ScheduleConfig:
    time: str = DEFAULT_SCHEDULE_TIME  # "HH:MM", 24h, local to the server's clock


@dataclass(frozen=True)
class Config:
    mosque: MosqueConfig
    icloud: ICloudConfig
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
    icloud = ICloudConfig(
        apple_id=str(_require(icloud_raw, "apple_id", "icloud")),
        app_specific_password=str(
            _require(icloud_raw, "app_specific_password", "icloud")
        ),
        calendar_name=str(_require(icloud_raw, "calendar_name", "icloud")),
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
        prayers=prayers,
        state_file=state_file,
        schedule=schedule,
    )


# --- Partial-config helpers, used only by the onboarding endpoints in
# api.py. A fresh install has no config.yaml at all, and step 1 of setup
# writes only the `icloud` block -- neither state is something the
# strict load_config() above is meant to tolerate, so onboarding reads
# and writes the raw YAML dict directly instead. ---------------------


def config_exists(path: str) -> bool:
    return os.path.isfile(path)


def read_raw(path: str) -> dict:
    """Read config.yaml as a raw dict, or {} if it doesn't exist yet."""
    if not config_exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"config file is not valid YAML: {path}: {e}") from e
    return raw if isinstance(raw, dict) else {}


def write_raw(path: str, data: dict) -> None:
    """Atomically write a raw config dict, chmod 600 (it holds a secret)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def merge_raw(path: str, updates: dict) -> dict:
    """Shallow-merge `updates` into the existing raw config one section
    at a time (e.g. updates={"icloud": {...}} only touches the `icloud`
    key, leaving `mosque`/`prayers`/etc. untouched), write it back, and
    return the merged dict.
    """
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
    mosque = raw.get("mosque") or {}
    has_icloud = bool(icloud.get("apple_id")) and bool(
        icloud.get("app_specific_password")
    )
    has_mosque = bool(mosque.get("slug"))
    return {
        "has_icloud": has_icloud,
        "has_mosque": has_mosque,
        "complete": has_icloud and has_mosque,
    }


def default_prayers_section() -> dict:
    return {
        name: {"enabled": True, "minutes_before": DEFAULT_MINUTES_BEFORE}
        for name in CANONICAL_PRAYERS
    }
