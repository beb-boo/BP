"""Web Push delivery via pywebpush (VAPID)."""

import asyncio
import json
import logging

from sqlalchemy.orm import Session

from ...models import PushSubscription, User
from ...utils.timezone import now_tz
from .base import DeliveryResult, NotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)


class WebPushChannel(NotificationChannel):
    channel_name = "web_push"

    def __init__(self, vapid_private_key: str, vapid_subject: str):
        self._vapid_private_key = vapid_private_key
        self._vapid_subject = vapid_subject

    async def send(self, db: Session, user: User, payload: NotificationPayload) -> DeliveryResult:
        subscriptions = db.query(PushSubscription).filter(
            PushSubscription.user_id == user.id,
            PushSubscription.is_active == True  # noqa: E712
        ).all()

        if not subscriptions:
            return DeliveryResult(False, self.channel_name, "no_active_subscriptions")

        message = json.dumps({
            "title": payload.title,
            "body": payload.body,
            "tag": payload.tag,
            "url": payload.url or "/",
            "data": payload.data or {},
        })

        delivered = 0
        deactivated = 0
        last_error: str | None = None

        for sub in subscriptions:
            try:
                # pywebpush is sync (requests) — keep the event loop free.
                await asyncio.to_thread(
                    self._push_one,
                    sub.endpoint, sub.p256dh, sub.auth, message,
                )
                sub.last_used_at = now_tz()
                delivered += 1
            except Exception as exc:  # WebPushException or network errors
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):
                    # Endpoint gone — subscription is dead, stop retrying it.
                    sub.is_active = False
                    deactivated += 1
                    logger.info(
                        f"Web push subscription {sub.id} for user {user.id} "
                        f"gone (HTTP {status}) — deactivated"
                    )
                else:
                    last_error = f"{type(exc).__name__}: {exc}"
                    # Don't log full endpoint URLs (treated as sensitive).
                    logger.warning(
                        f"Web push to subscription {sub.id} (user {user.id}) "
                        f"failed: {last_error[:200]}"
                    )

        db.commit()

        return DeliveryResult(
            success=delivered > 0,
            channel=self.channel_name,
            error=None if delivered > 0 else (last_error or "all_subscriptions_gone"),
            should_disable_target=deactivated > 0,
        )

    def _push_one(self, endpoint: str, p256dh: str, auth: str, message: str) -> None:
        from pywebpush import webpush

        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=message,
            vapid_private_key=self._vapid_private_key,
            vapid_claims={"sub": self._vapid_subject},
        )
