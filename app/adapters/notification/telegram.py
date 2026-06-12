"""Telegram delivery — thin wrapper around the existing raw-HTTP sender.

Reuses app.utils.notification.send_telegram_message (the same transport
send_telegram_otp has always used) so this works in FastAPI/cron context
without the python-telegram-bot runtime.
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from ...models import User
from ...utils.notification import send_telegram_message
from .base import DeliveryResult, NotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    channel_name = "telegram"

    async def send(self, db: Session, user: User, payload: NotificationPayload) -> DeliveryResult:
        telegram_id = user.telegram_id  # decrypts via model property
        if not telegram_id:
            return DeliveryResult(False, self.channel_name, "not_paired")

        text = f"*{payload.title}*\n\n{payload.body}" if payload.title else payload.body
        if payload.url:
            text += f"\n\n{payload.url}"

        ok = await asyncio.to_thread(send_telegram_message, telegram_id, text)
        return DeliveryResult(
            success=ok,
            channel=self.channel_name,
            error=None if ok else "telegram_send_failed",
        )
