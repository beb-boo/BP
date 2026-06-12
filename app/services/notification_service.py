"""NotificationService — preference-aware notification orchestrator.

PWA_SPEC §6.5/§6.6:
- Reads user.notification_preferences (validated by Pydantic, defaults
  inferred from what the user has when '{}').
- D4 privacy is enforced HERE, once, per channel: web_push gets the
  generic body unless show_details_in_push is true; telegram keeps
  details (user accepted that channel's behavior by pairing).
- First-success channel order; every attempt is logged.
"""

import logging
from dataclasses import replace

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from ..adapters.notification.base import (
    DeliveryResult,
    NotificationChannel,
    NotificationPayload,
)
from ..bot.locales import get_text
from ..models import PushSubscription, User

logger = logging.getLogger(__name__)

KNOWN_CHANNELS = ("web_push", "telegram")


class NotificationPreferences(BaseModel):
    """Shape v1 of users.notification_preferences (PWA_SPEC §6.4)."""
    channels: list[str] | None = None        # order = priority; None → infer
    show_details_in_push: bool = False        # D4 opt-in
    reminder_enabled: bool = True
    reminder_times: list[str] = Field(default_factory=lambda: ["07:00", "19:00"])


def parse_preferences(raw) -> NotificationPreferences:
    """Validate stored JSON; tolerate junk by falling back to defaults."""
    if not raw or not isinstance(raw, dict):
        return NotificationPreferences()
    try:
        return NotificationPreferences(**{
            k: v for k, v in raw.items()
            if k in NotificationPreferences.model_fields
        })
    except ValidationError as exc:
        logger.warning(f"Invalid notification_preferences, using defaults: {exc}")
        return NotificationPreferences()


class NotificationService:
    def __init__(self, channels: dict[str, NotificationChannel]):
        self.channels = channels

    def _infer_channels(self, db: Session, user: User) -> list[str]:
        """Default channel order when preferences don't specify one."""
        inferred: list[str] = []
        if "web_push" in self.channels:
            has_sub = db.query(PushSubscription).filter(
                PushSubscription.user_id == user.id,
                PushSubscription.is_active == True  # noqa: E712
            ).first() is not None
            if has_sub:
                inferred.append("web_push")
        if "telegram" in self.channels and user.telegram_id_hash:
            inferred.append("telegram")
        return inferred

    async def notify(self, db: Session, user: User,
                     payload: NotificationPayload) -> list[DeliveryResult]:
        """Send through the first channel that succeeds. Returns all attempts."""
        prefs = parse_preferences(user.notification_preferences)
        channel_order = prefs.channels or self._infer_channels(db, user)

        results: list[DeliveryResult] = []
        for name in channel_order:
            channel = self.channels.get(name)
            if channel is None:
                continue

            send_payload = payload
            if name == "web_push" and not prefs.show_details_in_push:
                # D4: lock-screen content stays generic unless opted in.
                generic = payload.body_generic or get_text(
                    "push_generic_body", user.language or "th")
                send_payload = replace(payload, body=generic)

            result = await channel.send(db, user, send_payload)
            results.append(result)
            logger.info(
                f"Notification to user {user.id} via {name}: "
                f"{'ok' if result.success else f'failed ({result.error})'}"
            )
            if result.success:
                break

        if not results:
            logger.info(
                f"Notification to user {user.id} skipped — no usable channel")
        return results
