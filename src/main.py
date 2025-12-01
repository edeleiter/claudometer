"""Main application entry point for Claude Usage Monitor."""

import logging
import sys
import threading
import time
from pathlib import Path

from .api_client import (
    AuthenticationError,
    ClaudeAPIClient,
    ClaudeAPIError,
    NetworkError,
    RateLimitError,
)
from .config import ConfigManager, get_config_path, get_log_dir
from .notifications import NotificationManager
from .tray_icon import TrayIconManager
from .utils import setup_logging

logger = logging.getLogger(__name__)


class ClaudeUsageMonitor:
    """Main application class coordinating all components."""

    def __init__(self):
        """Initialize the monitor application."""
        self.config = ConfigManager()
        self.running = False
        self.poll_thread: threading.Thread | None = None

        # Setup logging
        setup_logging(get_log_dir(), self.config.get("debug_mode", False))
        logger.info("Claude Usage Monitor starting...")

        # Initialize components (will be set up after config check)
        self.api: ClaudeAPIClient | None = None
        self.notifications: NotificationManager | None = None
        self.tray: TrayIconManager | None = None

    def _check_first_run(self) -> bool:
        """
        Check if this is first run and handle setup.

        Returns:
            True if configured and ready to run, False if setup needed
        """
        if self.config.is_configured():
            return True

        # First run - create example config and show instructions
        self._show_first_run_setup()
        return False

    def _show_first_run_setup(self) -> None:
        """Show first-run setup instructions."""
        config_path = get_config_path()

        # Create config with empty values
        self.config.save()

        print("=" * 60)
        print("Claude Usage Monitor - First Time Setup")
        print("=" * 60)
        print()
        print("A config file has been created at:")
        print(f"  {config_path}")
        print()
        print("Please edit the config file and add your credentials:")
        print()
        print("1. Organization ID:")
        print("   - Go to https://claude.ai/settings/usage")
        print("   - Copy the UUID from the URL:")
        print("     https://claude.ai/settings/organizations/YOUR-ORG-ID/usage")
        print()
        print("2. Session Cookie:")
        print("   - Open https://claude.ai in Chrome/Edge")
        print("   - Press F12 -> Application tab -> Cookies -> https://claude.ai")
        print("   - Find 'sessionKey' and copy its value")
        print()
        print("After editing the config, run the application again.")
        print("=" * 60)

        # Open the config file for editing
        try:
            import os
            os.startfile(str(config_path))
        except Exception:
            pass

    def _setup_components(self) -> None:
        """Initialize all components after config is verified."""
        self.api = ClaudeAPIClient(
            self.config["organization_id"],
            self.config["session_cookie"],
        )

        self.notifications = NotificationManager(
            self.config.get("notification_thresholds", [50, 75, 90])
        )

        self.tray = TrayIconManager(
            on_refresh=self._manual_refresh,
            on_exit=self._shutdown,
            config_path=str(get_config_path()),
        )

    def _manual_refresh(self) -> None:
        """Handle manual refresh request from tray menu."""
        logger.info("Manual refresh triggered")
        # Run poll in a separate thread to not block
        threading.Thread(target=self._poll_once, daemon=True).start()

    def _poll_once(self) -> None:
        """Perform a single poll of the API."""
        if not self.api or not self.tray or not self.notifications:
            return

        try:
            usage = self.api.get_usage()
            self.tray.update_usage(usage)
            self.notifications.check_and_notify(usage)
            logger.debug("Poll successful")

        except AuthenticationError:
            logger.error("Authentication failed - cookie expired")
            self.tray.set_error_state("auth_expired")
            self.notifications.send_auth_error_notification()

        except RateLimitError as e:
            logger.warning(f"Rate limited, retry after {e.retry_after}s")
            self.tray.set_error_state("rate_limited")

        except NetworkError as e:
            logger.warning(f"Network error: {e}")
            self.tray.set_error_state("network_error")

        except ClaudeAPIError as e:
            logger.error(f"API error: {e}")
            self.tray.set_error_state("error")

    def _poll_loop(self) -> None:
        """Background polling loop."""
        base_interval = self.config.get("poll_interval_seconds", 300)
        backoff_multiplier = 1

        # Initial poll
        self._poll_once()

        while self.running:
            # Calculate sleep time with backoff
            if self.tray and self.tray.error_state:
                if self.tray.error_state == "auth_expired":
                    # Don't spam on auth errors - check less frequently
                    sleep_time = 3600  # 1 hour
                elif self.tray.error_state == "rate_limited":
                    sleep_time = 120  # 2 minutes
                else:
                    # Exponential backoff for other errors
                    sleep_time = min(base_interval * backoff_multiplier, 1800)
                    backoff_multiplier = min(backoff_multiplier * 2, 6)
            else:
                sleep_time = base_interval
                backoff_multiplier = 1

            # Sleep in small intervals to allow for shutdown
            for _ in range(int(sleep_time)):
                if not self.running:
                    return
                time.sleep(1)

            if self.running:
                self._poll_once()

    def _shutdown(self) -> None:
        """Handle application shutdown."""
        logger.info("Shutting down...")
        self.running = False

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Check first run
        if not self._check_first_run():
            return 1

        # Setup components
        self._setup_components()

        if not self.tray:
            logger.error("Failed to setup tray icon")
            return 1

        self.running = True

        # Start polling thread
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()

        # Run tray icon (blocks main thread)
        try:
            self.tray.start()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.running = False

        # Wait for poll thread to finish
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=2)

        logger.info("Claude Usage Monitor stopped")
        return 0


def main() -> int:
    """Main entry point."""
    try:
        monitor = ClaudeUsageMonitor()
        return monitor.run()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
