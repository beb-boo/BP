"""BPRecordService: create, idempotency, duplicates, abnormal alert."""

import asyncio
import uuid
from datetime import datetime

from app.adapters.notification.base import (
    DeliveryResult,
    NotificationChannel,
)
from app.adapters.notification.factory import get_notification_service
from app.models import BloodPressureRecord, User
from app.services.bp_service import BPRecordService, bp_record_service


def _make_user(db_session, email):
    user = User(email=email, password_hash="x", role="patient", language="th")
    db_session.add(user)
    db_session.commit()
    return user


DATE = datetime(2026, 6, 11, 8, 0)


class TestCreateRecord:
    def test_create_and_duplicate(self, db_session):
        user = _make_user(db_session, "bps1@test.com")
        rec, created = bp_record_service.create_record(
            db_session, user.id, systolic=120, diastolic=80, pulse=70,
            measurement_date=DATE, measurement_time="08:00", source="test")
        assert created is True

        rec2, created2 = bp_record_service.create_record(
            db_session, user.id, systolic=120, diastolic=80, pulse=70,
            measurement_date=DATE, measurement_time="08:00", source="test")
        assert created2 is False
        assert rec2.id == rec.id

    def test_idempotent_replay(self, db_session):
        user = _make_user(db_session, "bps2@test.com")
        cid = str(uuid.uuid4())
        rec, created = bp_record_service.create_record(
            db_session, user.id, systolic=118, diastolic=78, pulse=66,
            measurement_date=DATE, measurement_time="09:00",
            source="test", client_record_id=cid)
        assert created is True

        # Replay with DIFFERENT values still returns the original.
        rec2, created2 = bp_record_service.create_record(
            db_session, user.id, systolic=140, diastolic=90, pulse=80,
            measurement_date=DATE, measurement_time="10:00",
            source="test", client_record_id=cid)
        assert created2 is False
        assert rec2.id == rec.id
        assert rec2.systolic == 118

    def test_records_isolated_per_user(self, db_session):
        u1 = _make_user(db_session, "bps3@test.com")
        u2 = _make_user(db_session, "bps4@test.com")
        bp_record_service.create_record(
            db_session, u1.id, systolic=121, diastolic=81, pulse=71,
            measurement_date=DATE, measurement_time="11:00", source="test")
        # Same values for another user must create a new row.
        _, created = bp_record_service.create_record(
            db_session, u2.id, systolic=121, diastolic=81, pulse=71,
            measurement_date=DATE, measurement_time="11:00", source="test")
        assert created is True


class TestCrisisThreshold:
    def test_boundaries(self):
        assert BPRecordService.is_crisis(181, 80)
        assert BPRecordService.is_crisis(120, 121)
        assert not BPRecordService.is_crisis(180, 120)
        assert not BPRecordService.is_crisis(120, 80)


class _CaptureChannel(NotificationChannel):
    channel_name = "telegram"

    def __init__(self):
        self.sent = []

    async def send(self, db, user, payload):
        self.sent.append(payload)
        return DeliveryResult(True, self.channel_name)


class TestAbnormalAlert:
    def test_crisis_triggers_alert(self, db_session, test_engine):
        capture = _CaptureChannel()
        svc = get_notification_service()
        original = dict(svc.channels)
        svc.channels.clear()
        svc.channels["telegram"] = capture
        try:
            user = _make_user(db_session, "abn1@test.com")
            user.telegram_id = 4242
            db_session.commit()

            async def run():
                bp_record_service.create_record(
                    db_session, user.id, systolic=190, diastolic=95, pulse=90,
                    measurement_date=DATE, measurement_time="12:00",
                    source="test")
                await asyncio.sleep(0.3)  # let the fire-and-forget task run

            asyncio.run(run())
            assert len(capture.sent) == 1
            payload = capture.sent[0]
            assert "190" in payload.body
            assert payload.body_generic  # D4-safe generic available
            assert payload.tag == "bp-abnormal"
        finally:
            svc.channels.clear()
            svc.channels.update(original)

    def test_normal_value_no_alert(self, db_session):
        capture = _CaptureChannel()
        svc = get_notification_service()
        original = dict(svc.channels)
        svc.channels.clear()
        svc.channels["telegram"] = capture
        try:
            user = _make_user(db_session, "abn2@test.com")

            async def run():
                bp_record_service.create_record(
                    db_session, user.id, systolic=125, diastolic=82, pulse=70,
                    measurement_date=DATE, measurement_time="13:00",
                    source="test")
                await asyncio.sleep(0.2)

            asyncio.run(run())
            assert capture.sent == []
        finally:
            svc.channels.clear()
            svc.channels.update(original)

    def test_no_event_loop_does_not_crash(self, db_session):
        user = _make_user(db_session, "abn3@test.com")
        # Direct sync call (no loop): save must still succeed.
        rec, created = bp_record_service.create_record(
            db_session, user.id, systolic=200, diastolic=130, pulse=99,
            measurement_date=DATE, measurement_time="14:00", source="test")
        assert created is True
        assert db_session.query(BloodPressureRecord).filter_by(
            id=rec.id).first() is not None
