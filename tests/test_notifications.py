"""Tests for notifications module."""

from unittest.mock import patch

import pytest

from src.notifications import NotificationManager


class TestNotificationManager:
    """Tests for NotificationManager class."""

    def test_init_default_thresholds(self):
        """Test default thresholds are set."""
        manager = NotificationManager()

        assert manager.thresholds == [50, 75, 90]

    def test_init_custom_thresholds(self):
        """Test custom thresholds are sorted."""
        manager = NotificationManager([90, 50, 75])

        assert manager.thresholds == [50, 75, 90]

    @patch("src.notifications.send_notification")
    def test_notify_at_threshold(self, mock_notify, sample_usage_response):
        """Test notification fires when threshold crossed."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Set usage to 51% (above 50 threshold)
        sample_usage_response["five_hour"]["utilization"] = 51.0

        notifications = manager.check_and_notify(sample_usage_response)

        assert len(notifications) == 1
        mock_notify.assert_called_once()

    @patch("src.notifications.send_notification")
    def test_no_notification_below_threshold(self, mock_notify, sample_usage_response):
        """Test no notification when below all thresholds."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Set usage below 50%
        sample_usage_response["five_hour"]["utilization"] = 30.0
        sample_usage_response["seven_day"]["utilization"] = 20.0

        notifications = manager.check_and_notify(sample_usage_response)

        assert len(notifications) == 0
        mock_notify.assert_not_called()

    @patch("src.notifications.send_notification")
    def test_no_repeat_notification(self, mock_notify, sample_usage_response):
        """Test notification doesn't repeat for same threshold."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        sample_usage_response["five_hour"]["utilization"] = 51.0

        # First check - should notify
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 1

        # Second check at same level - should NOT notify again
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 1

    @patch("src.notifications.send_notification")
    def test_notify_next_threshold(self, mock_notify, sample_usage_response):
        """Test notification fires for next threshold."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Cross 50%
        sample_usage_response["five_hour"]["utilization"] = 51.0
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 1

        # Cross 75%
        sample_usage_response["five_hour"]["utilization"] = 76.0
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 2

        # Cross 90%
        sample_usage_response["five_hour"]["utilization"] = 91.0
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 3

    @patch("src.notifications.send_notification")
    def test_reset_clears_notifications(self, mock_notify, sample_usage_response):
        """Test notifications reset when usage drops below minimum threshold."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Cross 75%
        sample_usage_response["five_hour"]["utilization"] = 76.0
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 2  # 50% and 75%

        # Usage resets to low value
        sample_usage_response["five_hour"]["utilization"] = 5.0
        manager.check_and_notify(sample_usage_response)

        # Cross 50% again - should notify
        sample_usage_response["five_hour"]["utilization"] = 51.0
        manager.check_and_notify(sample_usage_response)
        assert mock_notify.call_count == 3  # One more notification

    @patch("src.notifications.send_notification")
    def test_both_periods_notified(self, mock_notify, sample_usage_response):
        """Test both 5-hour and 7-day periods trigger notifications."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Both periods above 75%
        sample_usage_response["five_hour"]["utilization"] = 76.0
        sample_usage_response["seven_day"]["utilization"] = 80.0

        manager.check_and_notify(sample_usage_response)

        # Should have notifications for both periods at 50% and 75%
        assert mock_notify.call_count == 4

    def test_reset_notifications_specific_period(self):
        """Test resetting notifications for specific period."""
        manager = NotificationManager([50, 75, 90])
        manager._notified["five_hour"] = {50, 75}
        manager._notified["seven_day"] = {50}

        manager.reset_notifications("five_hour")

        assert manager._notified["five_hour"] == set()
        assert manager._notified["seven_day"] == {50}

    def test_reset_notifications_all(self):
        """Test resetting all notifications."""
        manager = NotificationManager([50, 75, 90])
        manager._notified["five_hour"] = {50, 75}
        manager._notified["seven_day"] = {50}

        manager.reset_notifications()

        assert manager._notified["five_hour"] == set()
        assert manager._notified["seven_day"] == set()

    def test_update_thresholds(self):
        """Test updating thresholds clears notifications."""
        manager = NotificationManager([50, 75, 90])
        manager._notified["five_hour"] = {50, 75}

        manager.update_thresholds([60, 80, 95])

        assert manager.thresholds == [60, 80, 95]
        assert manager._notified["five_hour"] == set()

    @patch("src.notifications.send_notification")
    def test_handles_missing_period_data(self, mock_notify):
        """Test gracefully handles missing period data."""
        mock_notify.return_value = True
        manager = NotificationManager([50, 75, 90])

        # Response with missing seven_day
        usage_data = {
            "five_hour": {"utilization": 60.0, "resets_at": None},
            "seven_day": None,
        }

        notifications = manager.check_and_notify(usage_data)

        # Should only notify for five_hour
        assert len(notifications) == 1
