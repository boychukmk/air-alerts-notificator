# Air Alerts Notificator

A personal notification bot for Ukraine. Since Russia's full-scale invasion,
Ukrainian cities face regular missile and drone strikes, and dozens of
Telegram channels report real-time sightings of launches, headings and
targets faster than official air-raid sirens. This bot listens to a curated
set of those channels, decides whether a message describes an actual,
in-progress threat to a specific city (as opposed to an all-clear, a forecast,
or unrelated chatter), and pushes an iPhone notification via
[ntfy](https://ntfy.sh) — loud enough to wake someone up, but only when it's
real.

## How it works

```
Telegram channels ──> alertbot/monitor.py (Telethon userbot)
                       │
                       ├─ filters.py     — classification: threat + location
                       │                   keyword co-occurrence, filtering
                       │                   out negations/hypotheticals
                       ├─ dedup.py       — dedup by normalized message text
                       ├─ storage.py     — audit log of every decision (events.db)
                       └─ notifier.py    — push burst via ntfy.sh

settings.db (SQLite) — regions, threat types, channels, users, sessions
                       │
                       └─ webapp/app.py — FastAPI control panel (LAN/VPN only)
```

Two independent long-running processes share one `settings.db`:
- **`alertbot/monitor.py`** — listens to the channels and fires alerts.
- **`webapp/app.py`** — a small control panel to toggle cities, threat types,
  and source channels (`monitor.py` reloads settings every 5s, no restart
  needed).

`settings.db`/`session.session`/`events.db` default to the repo root
(next to the `alertbot/` package); override the location with the
`ALERTBOT_DATA_DIR` environment variable — see `alertbot/paths.py`.

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + pytest + ruff
pip install -e .                      # installs this repo as a package (alertbot/, webapp/, scripts/)

cp .env.example .env   # fill in TG_API_ID / TG_API_HASH (my.telegram.org)

python scripts/seed_settings.py             # initialize settings.db + panel users
python scripts/login.py request +380...    # one-time Telegram account login
python scripts/login.py confirm +380... <code> <phone_code_hash>

python -m alertbot.monitor                  # monitoring + alerts
uvicorn webapp.app:app --reload --port 8081 # control panel, separate terminal
```

## Tests & lint

```bash
pytest        # 68 tests: filters/dedup/auth/channel_input/links/settings_store/webapp
ruff check .  # linter, config in pyproject.toml
```

The most important coverage is `tests/test_filters.py`: regression cases
pulled from real messages in `events.db` — both genuine alerts that must keep
firing, and past false positives that must stay blocked. Any change to
`filters.py` should be run against this suite before deploying.

CI (`.github/workflows/tests.yml`) runs `ruff` + `pytest` on every push/PR.

## Repository structure

```
alertbot/            # core logic, installable package
  monitor.py            — main process: listens to Telegram, classifies, alerts
  filters.py            — threat+location classification, noise filtering
  notifier.py           — push delivery via ntfy.sh
  dedup.py              — in-memory message deduplication
  storage.py            — audit log (SQLite)
  settings_store.py     — app state: regions/channels/threat types/users/sessions
  telegram_client.py    — shared Telethon client factory (single session)
  auth.py               — password hashing (PBKDF2), session tokens
  channel_input.py, links.py — channel input parsing, message links
  paths.py              — where settings.db/session.session/events.db live

webapp/              # FastAPI control panel
  app.py                — routes
  templates/            — HTML (Jinja2, no interpolation — just structure)
  static/               — dashboard/login CSS & JS

scripts/             # one-off admin scripts (not run as services)
  seed_settings.py, add_regions.py, set_password.py — settings.db administration
  login.py, qrlogin.py, resend.py, join_invite.py, list_dialogs.py — Telegram account

tests/               # pytest suite
deploy/              # systemd unit files
OPERATIONS.md        # deploy/infra reference (server, systemd, VPN) — in Ukrainian,
                      # written for the author's own ops use, not a dev-facing doc
```

## Production

Deployment, systemd services, VPN and ntfy setup are documented in
[OPERATIONS.md](OPERATIONS.md).
