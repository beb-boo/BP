"""Cron-triggered jobs (daily BP reminders).

Triggering options:
- Vercel Cron (vercel.json `crons`) — sends GET with
  `Authorization: Bearer ${CRON_SECRET}` automatically when the
  CRON_SECRET env var is set on the project.
- Any external scheduler (cron-job.org, UptimeRobot, server crontab)
  hitting the same URL with the same header. Useful on Vercel Hobby,
  where cron granularity is once per day.

Schedule every 15 minutes. A reminder fires when one of the user's
reminder_times falls inside the current 15-minute window in the USER'S
timezone, so each run covers exactly one window and never double-sends
(as long as the scheduler fires once per window).
"""

import logging
import os
import uuid
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..adapters.notification import NotificationPayload, get_notification_service
from ..bot.locales import get_text
from ..database import get_db
from ..models import PushSubscription, User
from ..services.notification_service import parse_preferences
from ..schemas import StandardResponse

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])
logger = logging.getLogger(__name__)

WINDOW_MINUTES = 15


def verify_cron_secret(authorization: str = Header(default="")):
    secret = os.getenv("CRON_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=503, detail="CRON_SECRET is not configured")
    if authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Invalid cron credentials")


def _window_bounds(now_utc: datetime, tz_name: str) -> tuple[datetime, datetime] | None:
    """Current 15-minute window [start, end) as naive local time, or None for bad tz."""
    try:
        tz = pytz.timezone(tz_name or "Asia/Bangkok")
    except pytz.exceptions.UnknownTimeZoneError:
        return None
    local = now_utc.astimezone(tz).replace(tzinfo=None)
    start = local.replace(minute=(local.minute // WINDOW_MINUTES) * WINDOW_MINUTES,
                          second=0, microsecond=0)
    return start, start + timedelta(minutes=WINDOW_MINUTES)


def _due_in_window(reminder_times: list[str], start: datetime, end: datetime) -> bool:
    for hhmm in reminder_times:
        try:
            h, m = hhmm.split(":")
            candidate = start.replace(hour=int(h), minute=int(m))
        except (ValueError, AttributeError):
            continue
        if start <= candidate < end:
            return True
    return False


@router.get("/reminders", response_model=StandardResponse)
async def run_reminders(
    _: None = Depends(verify_cron_secret),
    db: Session = Depends(get_db)
):
    """Send BP measurement reminders due in the current 15-minute window."""
    request_id = str(uuid.uuid4())
    now_utc = datetime.now(pytz.UTC)
    service = get_notification_service()

    if not service.channels:
        raise HTTPException(
            status_code=503, detail="No notification channels configured")

    # Only users who can actually receive something: telegram paired or
    # at least one active push subscription.
    push_user_ids = {
        row[0] for row in db.query(PushSubscription.user_id).filter(
            PushSubscription.is_active == True  # noqa: E712
        ).distinct().all()
    }

    candidates = db.query(User).filter(User.is_active == True).all()  # noqa: E712

    checked = sent = failed = 0
    for user in candidates:
        reachable = bool(user.telegram_id_hash) or user.id in push_user_ids
        if not reachable:
            continue

        prefs = parse_preferences(user.notification_preferences)
        if not prefs.reminder_enabled or not prefs.reminder_times:
            continue

        bounds = _window_bounds(now_utc, user.timezone)
        if bounds is None:
            continue
        if not _due_in_window(prefs.reminder_times, *bounds):
            continue

        checked += 1
        lang = user.language or "th"
        payload = NotificationPayload(
            title=get_text("reminder_title", lang),
            body=get_text("reminder_body", lang),
            body_generic=get_text("reminder_body", lang),  # reminder is inherently generic
            url="/dashboard",
            tag="bp-reminder",
        )
        try:
            results = await service.notify(db, user, payload)
            if any(r.success for r in results):
                sent += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            logger.error(f"Reminder to user {user.id} raised: {exc}")

    logger.info(
        f"Reminder cron: due={checked} sent={sent} failed={failed} "
        f"- Request ID: {request_id}")

    return StandardResponse(
        status="success",
        message="Reminder run complete",
        data={"due": checked, "sent": sent, "failed": failed},
        request_id=request_id,
    )
