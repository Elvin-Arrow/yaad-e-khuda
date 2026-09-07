# Engineering Notes

Rationale, gotchas, and non-obvious decisions that used to live as
comments/docstrings directly in the source. Pulled out here so the code
itself stays comment-free; this is where "why is it done this way"
questions get answered instead.

## `config.py`

- `load_config()` re-reads the file fresh on every call — never cached
  across runs (see `docs/idea.md` §3.3), so an edit to `config.yaml`
  always takes effect on the next `fetch`/`sync`/API call without
  needing a restart of anything.
- `config_exists` / `read_raw` / `write_raw` / `merge_raw` /
  `onboarding_status` are used **only** by the onboarding endpoints in
  `api.py`. A fresh install has no `config.yaml` at all, and step 1 of
  setup writes only the `icloud` block — neither state is something the
  strict `load_config()` is meant to tolerate, so onboarding reads and
  writes the raw YAML dict directly instead of going through the
  dataclass loader.
- `ICloudConfig.__repr__` is overridden so the password never leaks into
  an accidental log/print of the config object.

## `mawaqit.py`

- Deliberately does **not** depend on the `py-mawaqit`/`mawaqit` PyPI
  packages. One pulls in `requests_html` + `pyppeteer` (a headless
  Chromium downloaded at runtime) just to render a page whose `confData`
  is already present in the plain server-rendered HTML; the other
  requires a separate MAWAQIT account login. Confirmed directly against
  a real mosque page that a plain GET is enough — see `docs/idea.md` and
  the planning history for the investigation.
- `confData["calendar"][month-1][str(day)]` is a 6-element list of
  `"HH:MM"` strings: `[fajr, shuruq, dhuhr, asr, maghrib, isha]`. Shuruq
  (index 1) is not a prayer and is skipped, per `docs/idea.md` §3.1.
- `confData["iqamaCalendar"][month-1][str(day)]` is a 5-element list,
  one per canonical prayer in that same order — but each mosque
  configures, per prayer, whether Mawaqit reports iqama as a fixed clock
  time or as an offset from adhan, so the array holds a **mix of both
  shapes** depending on that mosque's own setup:
  - a signed-minutes-offset string, e.g. `"+0"`, `"+15"`, `"-5"`
  - an absolute `"HH:MM"` clock time, e.g. `"05:15"` (common for prayers
    with a fixed iqama that doesn't track adhan's daily drift)

  Confirmed against two real mosques exhibiting each shape (see
  `_resolve_iqama`). `docs/idea.md` originally assumed the offset-only
  shape; that turned out not to hold universally, and this was found by
  actually running the fetcher against a real mosque, not by inspection.
- `_resolve_iqama`'s fixed-`"HH:MM"` branch assumes the iqama falls on
  the same calendar day as adhan (no midnight rollover) — true for all
  five prayers in practice, since none of them are ever configured with
  a fixed iqama that lands after midnight relative to their own adhan.
- `extract_conf_data` finds the `confData = ` marker, then brace-matches
  from the following `{` to its balanced closing `}` (string-aware, so a
  `}` inside a quoted JSON string doesn't end the match early) — robust
  to the surrounding JS formatting, unlike matching on a fixed trailing
  string.

## `state.py`

Timezone-preservation fix (`docs/idea.md` §4): a tz-aware `datetime`'s
`isoformat()` serializes to a UTC *offset* (e.g. `"+01:00"`), not the
IANA *zone name* (`"Europe/Paris"`). Round-tripping that through
`datetime.fromisoformat()` gives back a fixed-offset `tzinfo` with no
zone identity — it looks tz-aware but has silently lost the zone. So
`state.py` never stores an offset-bearing timestamp: it stores the naive
wall-clock time plus the zone name once, and re-attaches
`ZoneInfo(zone_name)` explicitly on load. There is no path through this
file where a round-tripped offset string is the only record of the zone.

`save_state` writes to a `.tmp` file and `os.replace`s it into place —
atomic, so a crash mid-write can't corrupt or truncate the previous good
state file.

## `caldav_sync.py`

Idempotent by construction: every prayer/day pair maps to one
deterministic UID (`deterministic_uid`), so reruns update the existing
`VEVENT` instead of creating a duplicate (`docs/idea.md` §2
"Idempotency", §3.2, §6).

`_find_event_by_uid` deliberately does **not** use
`calendar.get_event_by_uid()` / `calendar.search(uid=...)`: those send a
server-side REPORT with a UID filter, which iCloud rejects with `412
Precondition Failed` — a known `python-caldav`/iCloud incompatibility
(iCloud has no compatibility preset in that library as of writing,
confirmed by hitting this error against a real account). The plain
"list every event" REPORT that `get_events()` sends has no such problem,
and the calendar only ever holds a handful of events (one per enabled
prayer), so listing everything and filtering by UID locally is cheap and
reliable.

`get_or_create_calendar`: iCloud's CalDAV server has a history of
`MKCALENDAR` quirks in `python-caldav`. If creation fails, the raised
error is actionable: create a calendar with the exact name yourself in
the Calendar app or at icloud.com/calendar, then rerun — the find-by-name
path works from then on regardless of how the calendar came to exist.

## `service.py` / `scheduler.py` / `cli.py`

`service.py` holds the actual fetch/sync/preview business logic, with no
logging or `sys.exit` side effects — callers get a plain result back and
decide what to do with it: `cli.py` logs it and maps it to an exit code,
`api.py` turns it into a JSON response, `scheduler.py`/`run_daily`
writes it to `state/last_run.json`. This exists so the CLI, the HTTP
API, and the in-process daily scheduler all run the identical logic
instead of three copies of it.

`run_daily` fetches, then syncs only if the fetch succeeded — mirrors
the `&&` chaining the cron setup used before the scheduler existed, so a
fetch failure never gets papered over by a sync reusing stale state.

`scheduler.py` replaces cron as the *primary* way the daily job runs: as
long as the server process is up, it fires `service.run_daily()` once a
day at `config.schedule.time`. Cron remains available as a documented
fallback for anyone who'd rather not keep the server running — it just
calls the same `fetch`/`sync` CLI subcommands it always did.
`reschedule()` moves the job without restarting the process, called
right after `PUT /api/config/schedule` persists a new time. The
scheduler is safe to start even before onboarding is complete: it falls
back to the default time, and a job firing against an incomplete config
just records a `ConfigError` in `last_run.json` rather than crashing.

`api.py`'s `create_app(config_path)` is a factory rather than a
module-level `app` singleton so tests (and `cli.cmd_serve`) can point it
at an arbitrary `config.yaml` path — it inherits the "re-read fresh, no
caching" requirement by simply calling `load_config()`/`read_raw()`
fresh inside every request handler, same as the CLI always did.

`cli.py`'s `yaad` command is registered via `pyproject.toml`'s
`[project.scripts]`; `python -m prayer_sync ...` still works too (same
`main()`, via `__main__.py`) — it's just not the documented name
anymore. `fastapi`/`uvicorn`/`apscheduler` are imported lazily inside
`cmd_serve`, so the plain `fetch`/`sync` CLI path doesn't need them
installed.

## Frontend

### Svelte 5 + `structuredClone` — a real bug, not a style choice

`PrayersCard.svelte` originally seeded its local editable copy of the
prayers map with `structuredClone(config.prayers)`. `config` is itself a
Svelte 5 `$state` in `Settings.svelte`, so `config.prayers` read from a
child component is a reactive **Proxy** — and the browser's structured-
clone algorithm explicitly rejects Proxies
(`DOMException: Proxy object could not be cloned`), which only surfaces
at runtime in an actual browser, not at `npm run build` (compile-time
only). Fixed with `$state.snapshot(config.prayers)`, Svelte 5's
purpose-built plain-object snapshot for exactly this situation. If you
ever need to clone a value derived from a `$state` object, reach for
`$state.snapshot()`, not `structuredClone()`.

Several settings cards (`MosqueCard`, `ICloudCard`, `ScheduleCard`,
`PrayersCard`) intentionally seed a local editable `$state` from a prop
**once**, so a background poll refreshing `config` every 60s doesn't
clobber an in-progress edit. Svelte's compiler flags this pattern
(`state_referenced_locally`) since it's usually a mistake; here it's
deliberate.

### Theming

Dark (true-black canvas) is the default/primary appearance, per the
Apple Fitness design guide this UI was built against. A light variant is
layered on top via `[data-theme="light"]` on `<html>`, set by
`theme.js` (`initTheme()` reads `localStorage`, falling back to
`prefers-color-scheme`, and is called before mounting to avoid a flash
of the wrong theme). The three ring/accent colors never restyle between
themes — only canvas/surface/label tokens change, per the guide's own
"ring colors are sacred" rule. Theme choice is a per-browser preference
(`localStorage`), not a server-side `config.yaml` value.

One real light-mode bug found by actually sweeping every component for
hardcoded (non-token) colors: `Button.svelte`'s `.filled` variant had
hardcoded white text over the translucent `--fill-neutral` background.
That reads fine on the dark canvas (gray-on-black is dark enough for
white text) but goes pale-gray-on-white in light mode, making the text
nearly invisible. Fixed to use `--label-primary` like everything else,
so it flips correctly with the theme.

### `frontend/Caddyfile` directive ordering

Bare top-level directives in a Caddyfile are **not** executed in the
order you write them — Caddy reorders them by its own fixed internal
directive priority. A first version with `reverse_proxy /api/*` and
`try_files`/`file_server` as sibling top-level directives sent every
request, including `/api/*`, through to `index.html`, because
`file_server` won the internal priority over `reverse_proxy`. The fix is
wrapping them in an explicit `route { ... }` block, which forces
literal, as-written order. Found by actually running the containers and
curling `/api/*` through the frontend, not by reading the Caddyfile.

## Docker / Compose

- `Dockerfile.backend` installs `requirements.txt` **before** copying
  `src/` and installing the package itself (`pip install --no-deps .`):
  a source-only change doesn't bust the slower dependency-install layer.
  `config.yaml`/`state/`/`last_run.json` deliberately live on a mounted
  volume, not baked into the image.
- `docker-compose.yml`'s backend service sets `working_dir: /data` with
  a `./data:/data` bind mount, rather than mounting a specific
  `config.yaml` file path. That sidesteps a classic Docker footgun
  (bind-mounting a path that doesn't exist yet on the host creates a
  *directory* there, not a file) and means every existing relative-path
  default (`config.yaml`, `state/today.json`, `state/last_run.json`)
  just lands under the persisted volume with zero code changes — the
  onboarding wizard can create `config.yaml` fresh inside `/data` on
  first visit exactly like it does outside Docker.
- Host ports `8100` (backend) / `8180` (frontend) aren't significant —
  just whatever was free on the machine this was set up on. Change the
  host side of `ports:` in `docker-compose.yml` if either collides with
  something else.
- `data/` is gitignored except a `.gitkeep` placeholder (same pattern as
  `state/`/`logs/`) since it holds the same real secret `config.yaml`
  does outside Docker.
- The Caddy directive-ordering gotcha (`route { ... }` block) is covered
  under "Frontend" above.

## Testing approach

- `date.today()` / `datetime.now()` are frozen in tests by monkeypatching
  the module-level `date`/`datetime` name inside `service`/`api` (e.g.
  `monkeypatch.setattr(service, "date", _FixedDate)`) with a subclass
  overriding `today()`/`now()` — you can't patch the builtin type
  in-place, but you can swap what name a module resolves it through.
  The fixture HTML only has calendar rows for Jan 1–2, so "today" is
  frozen to `2026-01-01` wherever a test needs `today_prayer_times` to
  succeed.
- `tests/test_caldav_sync.py`'s `FakeCalendar`/`FakeEvent` stand in for
  `caldav.Calendar`/`caldav.CalendarObjectResource` without any real
  iCloud account or network — `FakeCalendar` deliberately has **no**
  `get_event_by_uid` method, so if production code ever regressed to
  calling it (the 412-inducing method — see the `caldav_sync.py` notes
  above), the test fails with `AttributeError` instead of silently
  passing.
- `tests/test_scheduler.py` never starts a real `BackgroundScheduler`
  thread (heavy/flaky for a unit test) — only the pure `"HH:MM"` →
  `CronTrigger` parsing and the `reschedule()` wiring are exercised,
  against a `MagicMock` in place of the real scheduler.
- `tests/test_service.py`'s `config_path` fixture calls
  `monkeypatch.chdir(tmp_path)` so `service.LAST_RUN_FILE` (a relative
  path) lands under the test's tmp dir instead of writing into the real
  repo's `state/` directory.

## `config.example.yaml` field reference

- `mosque.slug`: the last path segment of the mosque's Mawaqit page URL
  (`https://mawaqit.net/en/<slug>`).
- `mosque.timezone_override`: normally left `null` — the mosque's IANA
  timezone is read straight out of its own `confData` (`"timezone"`
  field). Only set this to override what the mosque page reports.
- `icloud.apple_id` / `icloud.app_specific_password`: an app-specific
  password generated at appleid.apple.com under Security → App-Specific
  Passwords — **never** the real Apple ID password.
- `icloud.calendar_name`: the dedicated calendar these events are
  written to. Created automatically if it doesn't exist yet (see the
  `caldav_sync.py` notes above for the manual fallback if auto-creation
  fails against iCloud).
- `prayers.<name>.enabled` / `.minutes_before`: per-prayer toggle and
  alarm lead time. Disabling a prayer removes/skips its event entirely,
  including deleting one that already existed from before it was
  disabled.
- `state_file`: where the fetcher writes today's computed prayer times,
  and the calendar sync reads them from. Relative paths resolve from the
  current working directory the command is run from.
- `schedule.time`: only read by `yaad serve` (the in-process scheduler);
  irrelevant to the bare `fetch`/`sync` CLI subcommands.
