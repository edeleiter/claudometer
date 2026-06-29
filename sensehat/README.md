# Claudometer on the Sense HAT

Display your Claude.ai usage on a Raspberry Pi **Sense HAT** 8×8 LED matrix —
an always-on ambient appliance. It reuses the same Claude.ai API client and
config as the Windows tray app (`../src/`); only the display layer is new.

The project uses [**uv**](https://docs.astral.sh/uv/) to run Python. The commands
below all go through `uv run`, which resolves `requests` from `../pyproject.toml`
automatically. `--no-project` keeps the env light by skipping the Windows-only
tray deps (`pystray`/`winotify`).

The same code runs on three backends:

| Backend    | Where            | How to select                      |
|------------|------------------|------------------------------------|
| `hardware` | Raspberry Pi     | default (auto-detected)            |
| `emulator` | desktop/dev      | `--emulator` (provide `sense-emu`) |
| `stub`     | headless / CI    | `--backend stub` (prints ASCII)    |

## Display modes (cycle with the joystick)

| Mode | Name      | Shows                                                        |
|------|-----------|-------------------------------------------------------------|
| 0    | dual-bars | Left bar = 5-hour window, right bar = 7-day window (default) |
| 1    | meter     | One full-width bar of the *worse* of the two windows        |
| 2    | scroll    | Scrolls the exact numbers, e.g. `5h 47 7d 25`               |

Bars fill bottom-up and are colored by usage tier (matching the tray icon):
**green** <50%, **yellow** 50–74%, **orange** 75–89%, **red** ≥90%.

Non-data states replace the bars with a glyph: blue **!** = session cookie
expired, gray **?** = network error, gray **X** = other API error, a dim walking
pixel = loading.

## Joystick controls

| Direction     | Action                          |
|---------------|---------------------------------|
| left / right  | previous / next display mode    |
| middle (push) | force an immediate refresh      |
| up / down     | brightness full / low           |

## Develop on the emulator (do this first)

On your dev machine (the emulator GUI needs an X display — WSLg provides one on
Windows 11). `uv` pulls in `sense-emu` on the fly with `--with`, so there's
nothing to install up front:

```bash
# on-screen LED matrix + virtual joystick:
uv run --no-project --with sense-emu sense_emu_gui &

# Synthetic sweep — no credentials needed, great for tuning the visuals:
uv run --no-project --with requests --with sense-emu python -m sensehat.app --demo --emulator

# Live data on the emulator (fill in credentials first, see below):
uv run --no-project --with requests --with sense-emu python -m sensehat.app --emulator
```

No GUI handy? Preview the rendering as ASCII in the terminal (requests only):

```bash
uv run --no-project --with requests python -m sensehat.app --demo --backend stub          # animated sweep
uv run --no-project --with requests python -m sensehat.app --demo --backend stub --once    # single frame
```

## Credentials

Credentials come from a single source, chosen by precedence:
**environment / `.env` → `config.json`** (the tray app's file, used only as a
fallback). If your `.env` supplies the org + cookie, `config.json` is never read.

### Option A — `.env` (easiest for emulator testing)

```bash
cp sensehat/env.example .env         # at the repo root
# edit .env and fill in:
#   CLAUDOMETER_ORG_ID=...
#   CLAUDOMETER_SESSION_COOKIE=...

# picks up ./.env automatically:
uv run --no-project --with requests --with sense-emu python -m sensehat.app --emulator
```

`.env` is searched at the repo root and `sensehat/.env`, or point at one with
`--env path/to/.env`. It's git-ignored, so your secrets stay local.

### Option B — `config.json`

Live mode also reuses `ConfigManager` from `../src/config.py`. On first run it
writes a template and tells you where; on Linux that's
`~/.claude-monitor/config.json` (or set `CLAUDE_MONITOR_DATA` to choose the
directory):

```json
{
  "organization_id": "<UUID from https://claude.ai/settings/usage>",
  "session_cookie": "<the 'sessionKey' cookie from claude.ai (F12 → Application → Cookies)>",
  "poll_interval_seconds": 300
}
```

Either way, `device_id` is generated automatically. These are the same values
the Windows app uses, so you can copy them straight from its `config.json`.

## Deploy on the Raspberry Pi

```bash
sudo apt update && sudo apt install -y sense-hat        # the 'sense_hat' module
sudo usermod -aG input "$USER"                          # joystick access (re-login after)

# Install uv if you don't have it:
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone <your-repo> ~/claudometer && cd ~/claudometer
# Put your credentials in a .env file or ~/.claude-monitor/config.json (see above)

# Build a venv that can still see apt's sense_hat, then install requests into it.
# run.sh prefers this .venv, which is what the service uses.
uv venv --system-site-packages
uv pip install requests

chmod +x sensehat/run.sh
./sensehat/run.sh                                       # manual test on the matrix
```

The `--system-site-packages` flag is what lets the uv venv import the
apt-installed `sense_hat` (which isn't on PyPI in a Pi-friendly form).

### Run as a service (always-on, starts at boot)

```bash
sudo cp sensehat/claudometer-sensehat.service /etc/systemd/system/
# Edit User / WorkingDirectory / ExecStart paths in the unit if not /home/pi/claudometer
sudo systemctl daemon-reload
sudo systemctl enable --now claudometer-sensehat
journalctl -u claudometer-sensehat -f                   # follow logs
```

`Restart=on-failure` brings it back if it crashes, and `enable` starts it on
every boot.

## CLI reference

```
--demo                 synthetic data (no creds/network)
--emulator             force the sense_emu backend
--env PATH             load credentials from a specific .env file
--backend {auto,hardware,emulator,stub}
--interval SECONDS     poll interval (default: config, or 0.7 in --demo)
--rotation {0,90,180,270}   match your Pi's orientation
--brightness {low,full}     default low
--once                 render one frame and exit (smoke test)
--log-level LEVEL      DEBUG / INFO / WARNING ...
```
