# Prayer Reminder Sync

Syncs today's Iqama times from a mosque's Mawaqit page into a dedicated
iCloud Calendar, as real events with native `VALARM` alarms — so
reminders come through Apple's own Calendar app. See `docs/idea.md` for
the original design rationale and the plan files under
`~/.claude/plans/` for how the web UI on top of it was designed.

There are two ways to run this:

- **The web app** (recommended): a small FastAPI backend + Svelte UI.
  First run walks you through setup (iCloud, then mosque), then shows
  today's times, lets you tweak per-prayer alarms, and runs the daily
  sync itself on a schedule you set — no cron needed.
- **The bare CLI**, driven by cron — the original design, still fully
  supported for anyone who'd rather not keep a server running.

## Web app setup

1. **Backend — create a venv and install:**
   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -e .
   ```

2. **Frontend — build it once:**
   ```sh
   cd frontend
   npm install
   npm run build     # -> frontend/dist, served by the backend below
   cd ..
   ```

3. **Run the server:**
   ```sh
   .venv/bin/python -m prayer_sync serve
   ```
   Open **http://127.0.0.1:8000**. First run walks you through:
   1. Your iCloud Apple ID + an **app-specific password** (never your
      real Apple ID password — generate one at
      [appleid.apple.com](https://appleid.apple.com), under
      **Security → App-Specific Passwords**). This is validated against
      iCloud before anything is saved.
   2. Your mosque's Mawaqit slug — the last path segment of its page URL
      (`https://mawaqit.net/en/<slug>`). This is validated by actually
      fetching the page before anything is saved, and you'll see today's
      computed times right after.

   From there you land on the settings screen: today's times, a toggle +
   minutes-before stepper per prayer (autosaves), and cards to edit your
   mosque/iCloud/schedule settings or trigger a sync manually.

   The server binds to `127.0.0.1` only by default — it holds an iCloud
   app-specific password and isn't meant to be reachable off the machine
   it runs on. Pass `--host`/`--port` to `serve` to change that
   deliberately.

   If calendar creation fails against iCloud (their CalDAV server has a
   history of `MKCALENDAR` quirks — see `caldav_sync.get_or_create_calendar`),
   the error message will tell you: create a calendar with the exact
   name from your config once, by hand, in the Calendar app or at
   icloud.com/calendar. Everything after that just finds it by name.

4. **Daily sync**: as long as `python -m prayer_sync serve` is running,
   it fetches + syncs itself once a day at the time set in the
   Settings screen's "Daily sync time" card (default 03:00, editable
   without restarting). Keep the server running for this to actually
   happen unattended — see "Running persistently" below.

## Using the app

Once setup is done, opening the app takes you straight to the Settings
screen:

- **The ring at the top** shows time remaining until the next enabled
  prayer's Iqama, with "Next: {Prayer} at {time}" underneath. If you're
  before the day's first enabled prayer, or after the last one, it shows
  a resting state instead of a countdown (it doesn't look ahead to
  tomorrow's times).
- **Prayers card**: each row shows today's actual Adhan/Iqama time for
  that prayer (read-only, computed live from Mawaqit), a stepper for how
  many minutes before Iqama the alarm should fire, and a toggle to
  enable/disable that prayer entirely. Both **autosave** a moment after
  you change them — watch for the small "Saving…" / "Saved" label.
  Disabling a prayer here doesn't just stop future syncing of it — the
  next sync actively **removes** its event from the calendar if one was
  already there.
- **Sync card**: shows when the daily job last ran and whether it
  succeeded (with the error message if not). **Sync Now** triggers a
  fetch + sync immediately, outside the daily schedule — useful right
  after changing something and wanting to see it land in the calendar
  without waiting.
- **Mosque / iCloud / Schedule cards**: each needs an explicit **Save**
  (unlike the Prayers card) because saving re-validates against Mawaqit
  or iCloud first. On the iCloud card, leave the password field blank to
  keep the one already on file — only fill it in when you're actually
  rotating it.

### Running persistently

`serve` needs to keep running for the daily schedule to fire. A simple
systemd user service:

```ini
# ~/.config/systemd/user/prayer-sync.service
[Unit]
Description=Prayer Reminder Sync

[Service]
WorkingDirectory=/path/to/prayer-time-sync
ExecStart=/path/to/prayer-time-sync/.venv/bin/python -m prayer_sync serve
Restart=on-failure

[Install]
WantedBy=default.target
```

```sh
systemctl --user daemon-reload
systemctl --user enable --now prayer-sync
journalctl --user -u prayer-sync -f   # logs, including each daily run's outcome
```

(Drop `--user` and adjust paths for a system-wide service instead, if
you'd rather it start without a login session.)

### Frontend development

```sh
cd frontend && npm run dev     # Vite dev server on :5173, proxies /api -> :8000
.venv/bin/python -m prayer_sync serve   # backend on :8000, in another terminal
```

## Bare CLI + cron (no server to keep running)

Skip `npm`/`serve` entirely and drive it by hand or via cron instead:

1. Follow backend step 1 above (venv + `pip install -e .`).
2. Get your mosque slug and iCloud app-specific password as described
   above.
3. Create your config:
   ```sh
   cp config.example.yaml config.yaml
   chmod 600 config.yaml
   ```
   Edit it directly — mosque slug, iCloud credentials/calendar name,
   per-prayer `enabled`/`minutes_before`. (The `schedule` section is
   irrelevant here; it only matters to `serve`.)
4. Run it once to confirm it works end-to-end:
   ```sh
   .venv/bin/python -m prayer_sync fetch
   .venv/bin/python -m prayer_sync sync
   ```
   Check your iCloud calendar (the app or icloud.com) for the new events.
5. Add to crontab (`crontab -e`), early enough to be well before Fajr in
   your mosque's timezone:
   ```cron
   15 3 * * * cd /path/to/prayer-time-sync && \
     .venv/bin/python -m prayer_sync fetch >> logs/fetch.log 2>&1 && \
     .venv/bin/python -m prayer_sync sync  >> logs/sync.log  2>&1
   ```
   The `&&` matters: `sync` only runs if `fetch` succeeded, so a fetch
   failure never gets papered over by a sync that reuses stale state.
   Cron mails stderr on failure by default; the log redirects
   additionally give you a persistent log to check.

## Running the tests

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Tests run fully offline: mosque-page parsing is tested against a fixture
in `tests/fixtures/`, the CalDAV upsert/delete logic against an in-memory
fake calendar, and the FastAPI routes via `TestClient` with the
mawaqit/CalDAV calls monkeypatched — no live iCloud account or network
needed to run the suite. There's no automated frontend test suite (a
personal 2-screen UI is fastest to verify by actually looking at it);
`docs/idea.md` §6's acceptance criteria are meant to be walked manually,
once, against your real account.

## Project layout

```
src/prayer_sync/
├── config.py        # load_config() -- re-read fresh every run; onboarding's partial-write helpers
├── mawaqit.py        # fetch mosque page, extract confData, compute today's adhan/iqama
├── state.py          # local JSON state: today's computed times (atomic write)
├── caldav_sync.py     # iCloud CalDAV: find/create calendar, upsert/delete events
├── service.py        # fetch/sync business logic shared by the CLI, API, and scheduler
├── scheduler.py       # in-process daily scheduler (APScheduler) started by `serve`
├── api.py            # FastAPI app: onboarding, settings, live prayer times, sync status/trigger
└── cli.py            # `fetch` / `sync` / `serve` subcommands

frontend/
├── src/App.svelte                 # routes to Onboarding or Settings based on /api/setup/status
└── src/lib/
    ├── api.js                     # fetch wrappers for the backend
    ├── theme.css                  # design tokens (true-black canvas, Move-pink accent, SF Pro/Inter)
    ├── components/                # Card, Button, Toggle, Stepper, TextField, Toast, NextPrayerRing
    ├── onboarding/                 # 2-step wizard: iCloud, then mosque
    └── settings/                  # ring hero + per-prayer, mosque, iCloud, schedule, sync cards
```
