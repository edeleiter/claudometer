"""System tray icon management."""

import logging
from typing import Any, Callable

import pystray
from PIL import Image

from .icon_generator import IconGenerator
from .utils import format_relative_time, open_file_in_editor, open_url

logger = logging.getLogger(__name__)


class TrayIconManager:
    """Manages the system tray icon and menu."""

    def __init__(
        self,
        on_refresh: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        config_path: str | None = None,
    ):
        """
        Initialize tray icon manager.

        Args:
            on_refresh: Callback for refresh menu item
            on_exit: Callback for exit menu item
            config_path: Path to config file for "Open Config" menu item
        """
        self.on_refresh = on_refresh
        self.on_exit = on_exit
        self.config_path = config_path

        self.icon_generator = IconGenerator()
        self.icon: pystray.Icon | None = None
        self.current_usage: dict[str, Any] | None = None
        self.error_state: str | None = None

    def _create_menu(self) -> pystray.Menu:
        """Create the context menu for the tray icon."""
        return pystray.Menu(
            pystray.MenuItem("Refresh Now", self._handle_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open claude.ai", self._handle_open_claude),
            pystray.MenuItem("Open Config", self._handle_open_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._handle_exit),
        )

    def _handle_refresh(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle refresh menu click."""
        logger.info("Manual refresh requested")
        if self.on_refresh:
            self.on_refresh()

    def _handle_open_claude(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle open claude.ai menu click."""
        open_url("https://claude.ai")

    def _handle_open_config(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle open config menu click."""
        if self.config_path:
            from pathlib import Path
            open_file_in_editor(Path(self.config_path))
        else:
            logger.warning("Config path not set")

    def _handle_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle exit menu click."""
        logger.info("Exit requested from tray menu")
        if self.on_exit:
            self.on_exit()
        self.stop()

    def _build_tooltip(self) -> str:
        """Build tooltip text showing current usage."""
        if self.error_state:
            return self._build_error_tooltip()

        if not self.current_usage:
            return "Claude Monitor\nLoading..."

        lines = ["Claude Usage Monitor", ""]

        five = self.current_usage.get("five_hour")
        if five:
            pct = five.get("utilization", 0)
            reset = format_relative_time(five.get("resets_at"))
            status = "OK" if pct < 75 else ("HIGH" if pct < 90 else "CRITICAL")
            lines.append(f"5-hour:  {pct:.0f}% [{status}]")
            lines.append(f"  Resets {reset}")

        seven = self.current_usage.get("seven_day")
        if seven:
            pct = seven.get("utilization", 0)
            reset = format_relative_time(seven.get("resets_at"))
            status = "OK" if pct < 75 else ("HIGH" if pct < 90 else "CRITICAL")
            lines.append(f"Weekly:  {pct:.0f}% [{status}]")
            lines.append(f"  Resets {reset}")

        return "\n".join(lines)

    def _build_error_tooltip(self) -> str:
        """Build tooltip for error state."""
        if self.error_state == "auth_expired":
            return "Claude Monitor\n\nAuth Error: Cookie expired\nUpdate config and restart"
        elif self.error_state == "network_error":
            return "Claude Monitor\n\nConnection Error\nCheck internet connection"
        elif self.error_state == "rate_limited":
            return "Claude Monitor\n\nRate Limited\nWaiting to retry..."
        else:
            return "Claude Monitor\n\nError occurred"

    def _get_current_icon(self) -> Image.Image:
        """Get the appropriate icon for current state."""
        if self.error_state:
            return self.icon_generator.create_error_icon(self.error_state)

        if not self.current_usage:
            return self.icon_generator.create_loading_icon()

        five_hour = self.current_usage.get("five_hour", {}).get("utilization", 0)
        seven_day = self.current_usage.get("seven_day", {}).get("utilization", 0)

        return self.icon_generator.create_usage_icon(five_hour, seven_day)

    def update_usage(self, usage_data: dict[str, Any]) -> None:
        """
        Update the icon with new usage data.

        Args:
            usage_data: API response containing usage information
        """
        self.current_usage = usage_data
        self.error_state = None
        self._update_icon()

    def set_error_state(self, error_type: str) -> None:
        """
        Set error state for the icon.

        Args:
            error_type: Type of error ('auth_expired', 'network_error', 'rate_limited')
        """
        self.error_state = error_type
        self._update_icon()

    def clear_error_state(self) -> None:
        """Clear error state."""
        self.error_state = None
        self._update_icon()

    def _update_icon(self) -> None:
        """Update the tray icon and tooltip."""
        if not self.icon:
            return

        try:
            self.icon.icon = self._get_current_icon()
            self.icon.title = self._build_tooltip()
        except Exception as e:
            logger.error(f"Failed to update icon: {e}")

    def start(self) -> None:
        """Start the tray icon (blocks the main thread)."""
        initial_icon = self.icon_generator.create_loading_icon()

        self.icon = pystray.Icon(
            "claude_monitor",
            initial_icon,
            "Claude Monitor\nLoading...",
            self._create_menu(),
        )

        logger.info("Starting tray icon")
        self.icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self.icon:
            logger.info("Stopping tray icon")
            self.icon.stop()
            self.icon = None

    def is_running(self) -> bool:
        """Check if tray icon is running."""
        return self.icon is not None and self.icon.visible
