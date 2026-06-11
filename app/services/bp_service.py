"""BPRecordService — shared BP business logic for web API + bot (PWA_SPEC §8).

The create/duplicate/idempotency logic here was moved verbatim from
app/routers/bp_records.py and app/bot/services.py (they had drifted
copies of the same duplicate check). Channel-specific concerns stay in
the callers: HTTP status mapping in the router, date-string parsing and
session management in BotService.
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import BloodPressureRecord, User
from ..utils.timezone import now_tz

logger = logging.getLogger(__name__)


class BPRecordService:

    def create_record(
        self,
        db: Session,
        user_id: int,
        *,
        systolic: int,
        diastolic: int,
        pulse: int,
        measurement_date: datetime,
        measurement_time: str | None,
        notes: str | None = None,
        source: str = "api",
        client_record_id: str | None = None,
    ) -> tuple[BloodPressureRecord, bool]:
        """Create a BP record. Returns (record, created).

        created=False means an existing record was returned instead:
        either an idempotent replay (client_record_id match) or the
        legacy same-day/same-values duplicate.
        """
        # 1. Idempotency (PWA_SPEC §7.3): same client_record_id → replay.
        if client_record_id:
            existing = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.client_record_id == client_record_id,
                BloodPressureRecord.user_id == user_id
            ).first()
            if existing:
                return existing, False

        # 2. Legacy duplicate check (moved verbatim — date part + time +
        #    all three values must match).
        expected_date = measurement_date.date() if measurement_date else now_tz().date()
        existing = db.query(BloodPressureRecord).filter(
            BloodPressureRecord.user_id == user_id,
            func.date(BloodPressureRecord.measurement_date) == expected_date,
            BloodPressureRecord.measurement_time == measurement_time,
            BloodPressureRecord.systolic == systolic,
            BloodPressureRecord.diastolic == diastolic,
            BloodPressureRecord.pulse == pulse
        ).first()
        if existing:
            return existing, False

        # 3. Insert.
        record = BloodPressureRecord(
            user_id=user_id,
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            measurement_date=measurement_date,
            measurement_time=measurement_time,
            notes=notes,
            client_record_id=client_record_id,
            created_at=now_tz()
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            # Race on the client_record_id unique index — row exists now.
            db.rollback()
            if client_record_id:
                existing = db.query(BloodPressureRecord).filter(
                    BloodPressureRecord.client_record_id == client_record_id,
                    BloodPressureRecord.user_id == user_id
                ).first()
                if existing:
                    return existing, False
            raise
        db.refresh(record)
        return record, True

    # ------------------------------------------------------------------
    # Abnormal alert (new in Sprint 4 — goes through NotificationService)
    # ------------------------------------------------------------------

    @staticmethod
    def is_crisis(systolic: int, diastolic: int) -> bool:
        """AHA/ACC 2017 hypertensive crisis threshold."""
        return systolic > 180 or diastolic > 120

    def _maybe_alert_abnormal(self, db: Session, record: BloodPressureRecord,
                              *, source: str) -> None:
        """Fire-and-forget crisis alert. Never blocks or fails the save."""
        if not self.is_crisis(record.systolic, record.diastolic):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.info(
                f"Abnormal BP for user {record.user_id} (no event loop, "
                "alert skipped)")
            return

        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            return
        values = (record.systolic, record.diastolic, record.pulse)
        loop.create_task(self._send_abnormal_alert(user.id, values, user.language or "th"))

    @staticmethod
    async def _send_abnormal_alert(user_id: int, values: tuple[int, int, int],
                                   lang: str) -> None:
        # Local imports avoid circulars (notification_service ← bot.locales).
        from ..adapters.notification import NotificationPayload, get_notification_service
        from ..bot.locales import get_text
        from ..database import SessionLocal

        try:
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return
                payload = NotificationPayload(
                    title=get_text("alert_abnormal_title", lang),
                    body=get_text("alert_abnormal_body", lang,
                                  sys=values[0], dia=values[1], pulse=values[2]),
                    body_generic=get_text("alert_abnormal_generic", lang),
                    url="/dashboard",
                    tag="bp-abnormal",
                )
                await get_notification_service().notify(db, user, payload)
        except Exception as exc:
            logger.error(f"Abnormal alert for user {user_id} failed: {exc}")

    # ------------------------------------------------------------------
    # OCR (moved from app/routers/ocr.py — ephemeral, image never stored)
    # ------------------------------------------------------------------

    async def process_ocr(self, image_bytes: bytes, *, upload_time=None):
        """Run Gemini OCR on raw image bytes via a temp file (deleted in
        finally). Returns the OCRResult from ocr_helper unchanged."""
        from ..utils.ocr_helper import read_blood_pressure_with_gemini

        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_bytes)
                temp_file_path = temp_file.name

            # Sync Gemini call off the event loop (behavior preserved).
            return await asyncio.to_thread(
                read_blood_pressure_with_gemini, temp_file_path,
                upload_time=upload_time
            )
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


bp_record_service = BPRecordService()
