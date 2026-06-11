"""NotificationService: D4 enforcement, channel fallback, 410 deactivation."""

import asyncio
from unittest.mock import MagicMock, patch

from app.adapters.notification.base import (
    DeliveryResult,
    NotificationChannel,
    NotificationPayload,
)
from app.adapters.notification.web_push import WebPushChannel
from app.models import PushSubscription, User
from app.services.notification_service import (
    NotificationService,
    parse_preferences,
)


class FakeChannel(NotificationChannel):
    def __init__(self, name: str, ok: bool):
        self.channel_name = name
        self.ok = ok
        self.sent: list[NotificationPayload] = []

    async def send(self, db, user, payload):
        self.sent.append(payload)
        return DeliveryResult(self.ok, self.channel_name,
                              None if self.ok else "boom")


def _user(prefs):
    user = MagicMock(spec=User)
    user.id = 1
    user.language = "th"
    user.telegram_id_hash = "h"
    user.notification_preferences = prefs
    return user


PAYLOAD = NotificationPayload(title="BP", body="SBP 185 — detail!",
                              body_generic=None)


class TestD4Enforcement:
    def test_web_push_gets_generic_body_by_default(self):
        ch = FakeChannel("web_push", True)
        svc = NotificationService({"web_push": ch})
        user = _user({"channels": ["web_push"]})
        asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert ch.sent[0].body == "ถึงเวลาวัดความดันโลหิต"

    def test_opt_in_keeps_detail(self):
        ch = FakeChannel("web_push", True)
        svc = NotificationService({"web_push": ch})
        user = _user({"channels": ["web_push"], "show_details_in_push": True})
        asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert ch.sent[0].body == "SBP 185 — detail!"

    def test_caller_generic_wins_over_default(self):
        ch = FakeChannel("web_push", True)
        svc = NotificationService({"web_push": ch})
        user = _user({"channels": ["web_push"]})
        payload = NotificationPayload(title="BP", body="detail",
                                      body_generic="มีข้อมูลใหม่ในระบบ")
        asyncio.run(svc.notify(MagicMock(), user, payload))
        assert ch.sent[0].body == "มีข้อมูลใหม่ในระบบ"

    def test_telegram_keeps_detail_without_opt_in(self):
        ch = FakeChannel("telegram", True)
        svc = NotificationService({"telegram": ch})
        user = _user({"channels": ["telegram"]})
        asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert ch.sent[0].body == "SBP 185 — detail!"


class TestFallback:
    def test_first_success_stops(self):
        a = FakeChannel("web_push", True)
        b = FakeChannel("telegram", True)
        svc = NotificationService({"web_push": a, "telegram": b})
        user = _user({"channels": ["web_push", "telegram"]})
        results = asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert len(results) == 1 and results[0].channel == "web_push"
        assert b.sent == []

    def test_falls_through_to_next_channel(self):
        a = FakeChannel("web_push", False)
        b = FakeChannel("telegram", True)
        svc = NotificationService({"web_push": a, "telegram": b})
        user = _user({"channels": ["web_push", "telegram"]})
        results = asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert [r.success for r in results] == [False, True]

    def test_unknown_channel_skipped(self):
        b = FakeChannel("telegram", True)
        svc = NotificationService({"telegram": b})
        user = _user({"channels": ["line", "telegram"]})
        results = asyncio.run(svc.notify(MagicMock(), user, PAYLOAD))
        assert len(results) == 1 and results[0].channel == "telegram"


class TestPreferenceParsing:
    def test_empty_gives_defaults(self):
        p = parse_preferences({})
        assert p.show_details_in_push is False
        assert p.reminder_enabled is True
        assert p.reminder_times == ["07:00", "19:00"]

    def test_junk_tolerated(self):
        p = parse_preferences({"channels": "not-a-list", "bogus": 1})
        assert p.channels is None

    def test_non_dict_tolerated(self):
        assert parse_preferences("garbage").channels is None
        assert parse_preferences(None).reminder_enabled is True


class _FakeWebPushException(Exception):
    def __init__(self, status):
        self.response = MagicMock(status_code=status)


class TestWebPush410Deactivation:
    def _sub(self, db_session, user_id, endpoint):
        sub = PushSubscription(
            user_id=user_id, endpoint=endpoint, p256dh="k", auth="a",
            is_active=True)
        db_session.add(sub)
        db_session.commit()
        return sub

    def _make_user(self, db_session):
        user = User(email=f"wp{id(self)}@test.com", password_hash="x",
                    role="patient")
        db_session.add(user)
        db_session.commit()
        return user

    def test_410_deactivates_subscription(self, db_session):
        user = self._make_user(db_session)
        sub = self._sub(db_session, user.id, f"https://push.example/{user.id}/a")
        channel = WebPushChannel("priv", "mailto:t@t.t")

        with patch.object(channel, "_push_one",
                          side_effect=_FakeWebPushException(410)):
            result = asyncio.run(channel.send(db_session, user, PAYLOAD))

        db_session.refresh(sub)
        assert sub.is_active is False
        assert result.success is False
        assert result.should_disable_target is True

    def test_partial_success_counts_as_success(self, db_session):
        user = self._make_user(db_session)
        ok_sub = self._sub(db_session, user.id, f"https://push.example/{user.id}/ok")
        dead = self._sub(db_session, user.id, f"https://push.example/{user.id}/dead")
        channel = WebPushChannel("priv", "mailto:t@t.t")

        def push(endpoint, p256dh, auth, message):
            if endpoint.endswith("/dead"):
                raise _FakeWebPushException(404)

        with patch.object(channel, "_push_one", side_effect=push):
            result = asyncio.run(channel.send(db_session, user, PAYLOAD))

        db_session.refresh(ok_sub)
        db_session.refresh(dead)
        assert result.success is True
        assert dead.is_active is False
        assert ok_sub.is_active is True
        assert ok_sub.last_used_at is not None

    def test_no_subscriptions(self, db_session):
        user = self._make_user(db_session)
        channel = WebPushChannel("priv", "mailto:t@t.t")
        result = asyncio.run(channel.send(db_session, user, PAYLOAD))
        assert result.success is False
        assert result.error == "no_active_subscriptions"
