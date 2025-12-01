"""Windows toast notification management."""

import logging
from datetime import datetime
from typing import Any

from winotify import Notification, audio

from .utils import format_relative_time

logger = logging.getLogger(__name__)

APP_ID = "Claude Usage Monitor"


def send_notification(
    title: str, message: str, urgent: bool = False, launch_url: str | None = None
) -> bool:
    """
    Send a Windows toast notification.

    Args:
        title: Notification title
        message: Notification body
        urgent: If True, play sound and use longer duration
        launch_url: Optional URL to open when notification clicked

    Returns:
        True if notification was sent successfully
    """
    try:
        toast = Notification(
            app_id=APP_ID,
            title=title,
            msg=message,
            duration="long" if urgent else "short",
        )

        if urgent:
            toast.set_audio(audio.Default, loop=False)

        if launch_url:
            toast.add_actions(label="Open Claude", launch=launch_url)

        toast.show()
        logger.info(f"Notification sent: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


class NotificationManager:
    """Manages usage threshold notifications."""

    def __init__(self, thresholds: list[int] | None = None):
        """
        Initialize notification manager.

        Args:
            thresholds: List of percentage thresholds to notify at (e.g., [50, 75, 90])
        """
        self.thresholds = sorted(thresholds or [50, 75, 90])
        # Track which thresholds have been notified for each period
        self._notified: dict[str, set[int]] = {
            "five_hour": set(),
            "seven_day": set(),
        }

    def check_and_notify(self, usage_data: dict[str, Any]) -> list[str]:
        """
        Check usage data and send notifications if thresholds crossed.

        Args:
            usage_data: API response containing usage information

        Returns:
            List of notification messages that were sent
        """
        notifications_sent = []

        for period in ["five_hour", "seven_day"]:
            data = usage_data.get(period)
            if not data:
                continue

            utilization = data.get("utilization", 0)
            resets_at = data.get("resets_at")

            # Check each threshold
            for threshold in self.thresholds:
                if (
                    utilization >= threshold
                    and threshold not in self._notified[period]
                ):
                    self._notified[period].add(threshold)
                    msg = self._send_threshold_notification(
                        period, utilization, threshold, resets_at
                    )
                    if msg:
                        notifications_sent.append(msg)

            # Reset notifications when usage drops below minimum threshold
            if utilization < min(self.thresholds):
                if self._notified[period]:
                    logger.info(f"Usage reset for {period}, clearing notifications")
                    self._notified[period].clear()

        return notifications_sent

    def _send_threshold_notification(
        self, period: str, usage: float, threshold: int, resets_at: str | None
    ) -> str | None:
        """Send notification for threshold being crossed."""
        period_name = "5-hour" if period == "five_hour" else "Weekly"

        if resets_at:
            reset_time = format_relative_time(resets_at)
            message = f"{period_name} limit at {int(usage)}%\nResets {reset_time}"
        else:
            message = f"{period_name} limit at {int(usage)}%"

        title = f"Claude Usage: {int(usage)}%"
        urgent = threshold >= 90

        success = send_notification(
            title=title,
            message=message,
            urgent=urgent,
            launch_url="https://claude.ai",
        )

        if success:
            logger.info(f"Threshold notification: {period} at {usage}% (threshold {threshold}%)")
            return f"{period_name}: {int(usage)}%"
        return None

    def send_auth_error_notification(self) -> None:
        """Send notification about authentication error."""
        send_notification(
            title="Claude Monitor: Auth Error",
            message="Session cookie expired. Please update your cookie in the config file.",
            urgent=True,
            launch_url="https://claude.ai",
        )

    def send_network_error_notification(self) -> None:
        """Send notification about network error."""
        send_notification(
            title="Claude Monitor: Connection Error",
            message="Unable to reach Claude.ai. Check your internet connection.",
            urgent=False,
        )

    def reset_notifications(self, period: str | None = None) -> None:
        """
        Reset notification tracking.

        Args:
            period: Specific period to reset, or None to reset all
        """
        if period:
            self._notified[period].clear()
        else:
            for p in self._notified:
                self._notified[p].clear()
        logger.info(f"Reset notifications for {period or 'all periods'}")

    def update_thresholds(self, thresholds: list[int]) -> None:
        """Update notification thresholds."""
        self.thresholds = sorted(thresholds)
        # Reset notifications when thresholds change
        self.reset_notifications()
        logger.info(f"Updated thresholds to {self.thresholds}")
