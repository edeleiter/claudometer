"""Claudometer Sense HAT entry point.

Wires config -> data source -> display, then runs a background poll thread (with
the same backoff policy as the Windows tray app) and a foreground render/joystick
loop. Run with ``python -m sensehat.app`` (see ``--help``).
"""

import argparse
import logging
import signal
import sys
import threading
import time

from .data_source import (
    STATE_AUTH,
    STATE_LOADING,
    STATE_OK,
    STATE_RATE_LIMITED,
    DemoDataSource,
    LiveDataSource,
    Usage,
)
from .display import MODE_NAMES, MODES, SenseHatDisplay
from .sense_compat import get_sense

logger = logging.getLogger("claudometer.sensehat")

# Poll backoff per feed state, mirroring src/main.py._poll_loop.
AUTH_BACKOFF = 3600  # 1 hour - don't spam on an expired cookie
RATE_LIMIT_BACKOFF = 120  # 2 minutes
MAX_BACKOFF = 1800  # 30 minutes cap for network/other errors


class ClaudometerApp:
    """Owns shared state and the two loops (poll + render)."""

    def __init__(self, display: SenseHatDisplay, source, base_interval: float):
        self.display = display
        self.source = source
        self.base_interval = base_interval

        self._lock = threading.Lock()
        self._usage = Usage(state=STATE_LOADING)
        self._mode_idx = 0
        self._running = False
        self._refresh = threading.Event()
        self._poll_thread: threading.Thread | None = None

    # -- shared state -------------------------------------------------------

    @property
    def usage(self) -> Usage:
        with self._lock:
            return self._usage

    @usage.setter
    def usage(self, value: Usage) -> None:
        with self._lock:
            self._usage = value

    @property
    def mode(self) -> int:
        return MODES[self._mode_idx]

    def cycle_mode(self, step: int) -> None:
        self._mode_idx = (self._mode_idx + step) % len(MODES)
        logger.info(f"Mode -> {MODE_NAMES[self.mode]}")

    # -- poll thread --------------------------------------------------------

    def _poll_once(self) -> Usage:
        usage = self.source.get_usage()
        self.usage = usage
        if usage.state == STATE_OK:
            logger.info(
                f"Usage: 5h={usage.five_hour:.0f}%  7d={usage.seven_day:.0f}%  "
                f"(worst {usage.worst:.0f}%)"
            )
        else:
            logger.info(f"Usage state: {usage.state}")
        return usage

    def _sleep_for_state(self, state: str) -> None:
        """Interruptible sleep whose duration depends on the last feed state."""
        if state == STATE_AUTH:
            duration = AUTH_BACKOFF
        elif state == STATE_RATE_LIMITED:
            duration = RATE_LIMIT_BACKOFF
        elif state in (STATE_OK, STATE_LOADING):
            duration = self.base_interval
            self._backoff_mult = 1
        else:  # network / other error -> exponential backoff
            duration = min(self.base_interval * self._backoff_mult, MAX_BACKOFF)
            self._backoff_mult = min(self._backoff_mult * 2, 6)

        # Wake early on shutdown or a manual refresh request.
        deadline = duration
        slice_s = 0.1
        waited = 0.0
        while self._running and waited < deadline:
            if self._refresh.wait(timeout=slice_s):
                self._refresh.clear()
                return
            waited += slice_s

    def _poll_loop(self) -> None:
        self._backoff_mult = 1
        usage = self._poll_once()
        while self._running:
            self._sleep_for_state(usage.state)
            if not self._running:
                break
            usage = self._poll_once()

    def request_refresh(self) -> None:
        logger.info("Manual refresh requested")
        self._refresh.set()

    # -- joystick -----------------------------------------------------------

    def _handle_events(self) -> None:
        try:
            events = self.display.sense.stick.get_events()
        except Exception as e:
            logger.debug(f"stick.get_events failed: {e}")
            return
        for event in events:
            if getattr(event, "action", None) != "pressed":
                continue
            direction = getattr(event, "direction", None)
            if direction == "right":
                self.cycle_mode(1)
            elif direction == "left":
                self.cycle_mode(-1)
            elif direction == "middle":
                self.request_refresh()
            elif direction == "up":
                self.display.set_low_light(False)
                logger.info("Brightness -> full")
            elif direction == "down":
                self.display.set_low_light(True)
                logger.info("Brightness -> low")

    # -- lifecycle ----------------------------------------------------------

    def run(self) -> int:
        self._running = True
        self._install_signal_handlers()

        self._poll_thread = threading.Thread(
            target=self._poll_loop, name="poll", daemon=True
        )
        self._poll_thread.start()

        tick = 0
        try:
            while self._running:
                self._handle_events()
                did_scroll = self.display.show_usage(self.usage, self.mode, tick)
                tick += 1
                if not did_scroll:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt")
        finally:
            self._running = False
            if self._poll_thread:
                self._poll_thread.join(timeout=2)
            self.display.clear()
            logger.info("Claudometer Sense HAT stopped")
        return 0

    def stop(self, *_args) -> None:
        logger.info("Shutdown signal received")
        self._running = False

    def _install_signal_handlers(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self.stop)
            except (ValueError, OSError):
                pass  # not on the main thread / unsupported platform

    def render_once(self) -> int:
        """Render a single frame (one poll) and exit - for smoke tests."""
        usage = self._poll_once()
        self.display.show_usage(usage, self.mode, 0)
        logger.info(
            f"Rendered one frame: state={usage.state} "
            f"5h={usage.five_hour:.0f} 7d={usage.seven_day:.0f} "
            f"mode={MODE_NAMES[self.mode]}"
        )
        return 0


# Accepted env var names (first match wins) for each credential.
ENV_ORG = ("CLAUDOMETER_ORG_ID", "CLAUDOMETER_ORGANIZATION_ID")
ENV_COOKIE = ("CLAUDOMETER_SESSION_COOKIE", "CLAUDOMETER_SESSION_KEY")
ENV_DEVICE = ("CLAUDOMETER_DEVICE_ID",)
ENV_INTERVAL = ("CLAUDOMETER_POLL_INTERVAL",)


def _first_env(names):
    """Return the first non-empty value among the given env var names."""
    import os

    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _resolve_device_id() -> str:
    """A stable device id for .env-only setups, persisted next to the app data.

    Kept independent of config.json so that supplying credentials via .env does
    NOT pull in (or create) a config.json. The value is just an identifier sent
    in a request header; it only needs to stay stable across runs.
    """
    import uuid

    from src.config import get_app_data_dir

    path = get_app_data_dir() / "sensehat_device_id"
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8").strip()
            if existing:
                return existing
    except OSError:
        pass
    device_id = str(uuid.uuid4())
    try:
        path.write_text(device_id, encoding="utf-8")
    except OSError:
        pass
    return device_id


def _interval_from_env_or_args(args):
    """Resolve poll interval from --interval then the env var, else None."""
    if args.interval is not None:
        return args.interval
    env_interval = _first_env(ENV_INTERVAL)
    return float(env_interval) if env_interval else None


def _build_source(args):
    """Construct the data source, resolving credentials for live mode.

    Credentials come from ONE source, chosen by precedence:
      1. environment / .env  (real env vars, then .env files)
      2. config.json         (the Windows tray app's file) -- fallback only

    config.json is loaded lazily, so an .env that supplies org + cookie means we
    never touch (or create) config.json at all.
    """
    if args.demo:
        logger.info("Demo data source (synthetic sweep)")
        return DemoDataSource(), (args.interval if args.interval is not None else 0.7)

    from pathlib import Path

    from .env_loader import load_dotenv

    # Default .env search: repo root, then sensehat/. An explicit --env wins.
    repo_root = Path(__file__).resolve().parent.parent
    env_paths = [args.env] if args.env else [
        repo_root / ".env", repo_root / "sensehat" / ".env"
    ]
    load_dotenv(env_paths)

    org_id = _first_env(ENV_ORG)
    session_cookie = _first_env(ENV_COOKIE)
    interval = _interval_from_env_or_args(args)

    # Path 1: .env / environment fully provides credentials -> config.json untouched.
    if org_id and session_cookie:
        logger.info("Credentials loaded from environment/.env")
        device_id = _first_env(ENV_DEVICE) or _resolve_device_id()
        return LiveDataSource(org_id, session_cookie, device_id), (interval or 300.0)

    # Path 2: fall back to the tray app's config.json for whatever is missing.
    from src.config import ConfigManager, get_config_path

    config = ConfigManager()
    org_id = org_id or config.get("organization_id")
    session_cookie = session_cookie or config.get("session_cookie")

    if not org_id or not session_cookie:
        config.save()  # write a template with empty fields
        print("=" * 60)
        print("Claudometer Sense HAT - credentials needed")
        print("=" * 60)
        print("\nProvide credentials in EITHER of these ways:\n")
        print("  1. A .env file (handy for emulator testing). Copy the template:")
        print("       cp sensehat/env.example .env   # then edit it")
        print("     Keys: CLAUDOMETER_ORG_ID, CLAUDOMETER_SESSION_COOKIE\n")
        print(f"  2. The config file at:\n       {get_config_path()}\n")
        print("  organization_id : the UUID from https://claude.ai/settings/usage")
        print("  session_cookie  : the 'sessionKey' cookie from claude.ai (F12)")
        print("\nThen run again. Or try the visuals now with:  --demo\n")
        sys.exit(1)

    logger.info("Credentials loaded from config.json (no .env override found)")
    device_id = (
        _first_env(ENV_DEVICE) or config.get("device_id") or config.ensure_device_id()
    )
    if interval is None:
        interval = float(config.get("poll_interval_seconds", 300))
    return LiveDataSource(org_id, session_cookie, device_id), interval


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="claudometer-sensehat",
        description="Display Claude.ai usage on a Raspberry Pi Sense HAT.",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Use synthetic data (no credentials/network needed).",
    )
    parser.add_argument(
        "--emulator", action="store_true",
        help="Force the sense_emu emulator backend.",
    )
    parser.add_argument(
        "--backend", choices=["auto", "hardware", "emulator", "stub"],
        help="Select display backend explicitly ('stub' prints ASCII).",
    )
    parser.add_argument(
        "--env", default=None,
        help="Path to a .env file with credentials (default: ./.env, sensehat/.env).",
    )
    parser.add_argument(
        "--interval", type=float, default=None,
        help="Seconds between polls (default: config value, or 0.7 in --demo).",
    )
    parser.add_argument(
        "--rotation", type=int, default=0, choices=[0, 90, 180, 270],
        help="Matrix rotation to match Pi orientation.",
    )
    parser.add_argument(
        "--brightness", choices=["low", "full"], default="low",
        help="LED brightness (default: low).",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Render a single frame and exit (smoke test).",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        sense, backend = get_sense(force_emulator=args.emulator, backend=args.backend)
    except RuntimeError as e:
        logger.error(str(e))
        return 1
    logger.info(f"Display backend: {backend}")

    display = SenseHatDisplay(
        sense, rotation=args.rotation, low_light=(args.brightness == "low")
    )

    try:
        source, base_interval = _build_source(args)
    except Exception as e:
        logger.exception(f"Failed to initialize data source: {e}")
        display.clear()
        return 1

    app = ClaudometerApp(display, source, base_interval)
    return app.render_once() if args.once else app.run()


if __name__ == "__main__":
    sys.exit(main())
