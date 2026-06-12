"""Build a NotificationService from environment configuration."""

import logging
import os
from functools import lru_cache

from ...services.notification_service import NotificationService
from .base import NotificationChannel
from .telegram import TelegramChannel
from .web_push import WebPushChannel

logger = logging.getLogger(__name__)


def build_notification_service() -> NotificationService:
    channels: dict[str, NotificationChannel] = {}

    vapid_private = os.getenv("WEB_PUSH_VAPID_PRIVATE", "")
    vapid_subject = os.getenv("WEB_PUSH_VAPID_SUBJECT", "")
    if vapid_private and vapid_subject:
        channels["web_push"] = WebPushChannel(vapid_private, vapid_subject)
    else:
        logger.info("WebPushChannel disabled (VAPID env not configured)")

    if os.getenv("TELEGRAM_BOT_TOKEN", ""):
        channels["telegram"] = TelegramChannel()
    else:
        logger.info("TelegramChannel disabled (TELEGRAM_BOT_TOKEN not set)")

    return NotificationService(channels)


@lru_cache(maxsize=1)
def get_notification_service() -> NotificationService:
    """Process-wide singleton (env doesn't change at runtime)."""
    return build_notification_service()
