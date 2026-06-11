"""Build a NotificationService from environment configuration."""

import logging
from functools import lru_cache

from ...config.settings import get_pwa_settings
from ...services.notification_service import NotificationService
from .base import NotificationChannel
from .telegram import TelegramChannel
from .web_push import WebPushChannel

logger = logging.getLogger(__name__)


def build_notification_service() -> NotificationService:
    settings = get_pwa_settings()
    channels: dict[str, NotificationChannel] = {}

    if settings.web_push_configured:
        channels["web_push"] = WebPushChannel(
            settings.vapid_private, settings.vapid_subject)
    else:
        logger.info("WebPushChannel disabled (VAPID env not configured)")

    if settings.telegram_configured:
        channels["telegram"] = TelegramChannel()
    else:
        logger.info("TelegramChannel disabled (TELEGRAM_BOT_TOKEN not set)")

    return NotificationService(channels)


@lru_cache(maxsize=1)
def get_notification_service() -> NotificationService:
    """Process-wide singleton (env doesn't change at runtime)."""
    return build_notification_service()
