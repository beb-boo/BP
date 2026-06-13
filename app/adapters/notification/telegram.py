"""Telegram delivery — thin wrapper around the existing raw-HTTP sender.

Reuses app.utils.notification.send_telegram_message (the same transport
send_telegram_otp has always used) so this works in FastAPI/cron context
without the python-telegram-bot runtime.
"""

import asyncio
import logging
import os

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
        link = self._resolve_url(payload.url)
        if link:
            text += f"\n\n{link}"

        ok = await asyncio.to_thread(send_telegram_message, telegram_id, text)
        return DeliveryResult(
            success=ok,
            channel=self.channel_name,
            error=None if ok else "telegram_send_failed",
        )

    @staticmethod
    def _resolve_url(url: str | None) -> str | None:
        """Payload URLs are web-app paths (e.g. "/dashboard") meant for the
        service worker's notificationclick. In a Telegram message a bare
        path renders like a bot command — useless. Resolve it against
        WEB_DASHBOARD_URL when configured, otherwise drop it.

        WEB_DASHBOARD_URL is a FULL page URL elsewhere in the repo (the
        /stats button links to it directly), e.g.
        https://frontend.example/dashboard — so only its origin is used
        here, never its path, to avoid .../dashboard/dashboard."""
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        from urllib.parse import urlparse
        parsed = urlparse(os.getenv("WEB_DASHBOARD_URL", ""))
        if not (parsed.scheme and parsed.netloc):
            return None
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}{url}" if url.startswith("/") else f"{origin}/{url}"
