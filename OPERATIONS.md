# Air Alerts Notificator — Operations Reference

A personal bot monitoring Telegram channels for missile/drone threats, with
push alerts to iPhone. This page is a "what lives where and how to get in"
reference, not a development guide.

## Server

- **Provider**: Hetzner Cloud, CPX31 plan (4 vCPU / 8 GB / 80 GB), Ubuntu 24.04, EU region (Falkenstein/Nürnberg)
- **Public IP**: `<SERVER_IP>`
- **Shared** with another project on the same machine — the production backend for **VocaLoft**
  (youtube-audio-studio, `api.vocaloft.com`, Docker Compose + Caddy). This bot
  lives separately, in its own directory, under systemd, with no secrets shared with VocaLoft.
- **SSH**: `ssh deploy@<SERVER_IP>` (key-based auth, root/password login disabled,
  ufw: 22/80/443 open to everyone, everything else denied by default)

## Code and deployment

- **Git repository**: https://github.com/boychukmk/air-alerts-notificator (private)
- **Server directory**: `/home/deploy/alert-monitor/`
- Secrets (`TG_API_ID`, `TG_API_HASH`) — in `/home/deploy/alert-monitor/.env`
  (chmod 600, **not** in git, not in systemd unit files)
- App state (regions, channels, threat types, users, ntfy topics) — in SQLite
  at `/home/deploy/alert-monitor/settings.db` (**not** in git)
- Telegram session (the logged-in account) — `/home/deploy/alert-monitor/session.session`
  (**not** in git — effectively a password to the Telegram account)
- Deploy = `git pull` on the server + `sudo systemctl restart <service>`.
  After a dependency change, also run `venv/bin/pip install -r requirements.txt`
  on the server. No CI/CD pipeline deploys automatically — it's a manual step.

## Systemd services (on the server)

| Service | What it does | Commands |
|---|---|---|
| `alert-monitor.service` | Telethon userbot: listens to channels, filters, sends alerts to ntfy | `sudo systemctl status/restart alert-monitor.service`, logs: `sudo journalctl -u alert-monitor.service -f` |
| `alert-monitor-web.service` | FastAPI control panel (uvicorn, port 8081) | `sudo systemctl status/restart alert-monitor-web.service` |

Both are `Restart=always`, surviving server reboots and process crashes.

## Telegram account (the monitoring userbot)

- A separate Telegram account, **not the author's main personal one**
- api_id/api_hash obtained at my.telegram.org under that account
- Joined (as a regular member) to source channels — managed via the web panel
  or directly through `scripts/join_invite.py`

## Web control panel

- **URL**: http://<TAILSCALE_IP>:8081 (reachable **only** over Tailscale VPN,
  not from the open internet — port 8081 is closed in ufw for the public interface)
- Login is by phone number; exactly 2 users are registered, and no new ones
  can be added through the app (there's no registration feature — only manual
  insertion via `scripts/seed_settings.py` on the server)
- Features: enable/disable a city (several can be active at once, each with
  its own ntfy topic), enable/disable a threat type, view and add trigger
  keywords, add a new source channel by link or handle

## VPN (Tailscale)

- Private network, free plan, account tied to the owner's Google login
- The server has a static tailnet address `<TAILSCALE_IP>`
- To get access from a new device — install the Tailscale app
  (App Store / tailscale.com), sign in with the same account
- Port 8081 in ufw is open exclusively `on tailscale0` — without joining this
  network the panel is physically unreachable from outside

## Alert delivery (ntfy)

- Service: https://ntfy.sh (public, free, no registration required)
- **Each city has its own topic** (generated automatically when a region is
  enabled in the panel, shown right next to its toggle)
- On iPhone: the **ntfy** app from the App Store, subscribed to the specific
  topic for one's city
- Required one-time iPhone setup: **Settings → Focus → [mode] →
  Allowed Notifications → ntfy → Time Sensitive Notifications** — without this,
  notifications can get muted under Do Not Disturb / a nighttime Focus mode
- On trigger — a burst of 5 notifications spaced ~1s apart (not just one),
  to reliably grab attention; a global 2-minute cooldown **per city** —
  several channels confirming the same event don't spam separate bursts

## Known limitations

- Without an Apple Developer account there's no custom notification sound —
  only ntfy's built-in tones; a full Notification Service Extension (custom
  sound, critical alerts) requires a paid Apple account ($99/year)
- The web panel is plain HTTP (no TLS) — security relies on being closed
  inside the Tailscale network, not on traffic encryption
