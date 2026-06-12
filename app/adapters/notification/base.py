"""Notification channel abstraction (PWA_SPEC §6.6).

Channels deliver a NotificationPayload to one user over one transport.
D4 privacy enforcement (generic vs detailed body) is NOT done here —
NotificationService owns that, channels just send what they are given.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ...models import User


@dataclass
class NotificationPayload:
    title: str
    body: str
    body_generic: str | None = None   # D4: used instead of body when not opted in
    url: str | None = None
    tag: str | None = None
    data: dict | None = None


@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None
    should_disable_target: bool = False   # 404/410 Gone → subscription deactivated


class NotificationChannel(ABC):
    channel_name: str

    @abstractmethod
    async def send(self, db: Session, user: User, payload: NotificationPayload) -> DeliveryResult:
        """Deliver payload to user. Must not raise — return a failed DeliveryResult."""
        ...
