"""Cron-triggered jobs (daily BP reminders).

Triggering options:
- Vercel Cron (vercel.json `crons`) — sends GET with
  `Authorization: Bearer ${CRON_SECRET}` automatically when the
  CRON_SECRET env var is set on the project.
- Any external scheduler (cron-job.org, UptimeRobot, server crontab)
  hitting the same URL with the same header. Useful on Vercel Hobby,
  where cron granularity is once per day.

Designed for a 15-minute cadence: a reminder fires when one of the
user's reminder_times falls inside the current 15-minute window in the
USER'S timezone.

On Vercel Hobby the only built-in cron is daily — vercel.json uses
`0 0 * * *` (00:00 UTC = 07:00 Asia/Bangkok), kept as a keep-alive
backstop while the real cadence comes from an external scheduler. That
backstop's 07:00 window overlaps the default 07:00 reminder, and a
jittery scheduler can fire twice in one window, so sends are
de-duplicated per (user, window) via Redis (best-effort, fails open:
a missed Redis beats a missed reminder).
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
# Dedup claim outlives the window + scheduler jitter. The key embeds the
# window's local datetime, so the same clock time tomorrow is a fresh key.
CLAIM_TTL_SECONDS = WINDOW_MINUTES * 60 * 2  # 30 min


def verify_cron_secret(authorization: str = Header(default="")):
    from ..config.settings import get_pwa_settings
    secret = get_pwa_settings().cron_secret
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


def _dedup_client():
    """Best-effort Redis client for reminder idempotency, or None when
    Redis isn't configured/reachable. Never raises — dedup is optional."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis
        return redis.from_url(
            redis_url, decode_responses=True,
            socket_connect_timeout=2.0, socket_timeout=2.0)
    except Exception as exc:
        logger.warning(f"Reminder dedup disabled (Redis init failed): {exc}")
        return None


def _claim_key(user_id: int, window_start: datetime) -> str:
    return f"reminder:sent:{user_id}:{window_start.isoformat()}"


def _claim_window(client, user_id: int, window_start: datetime) -> bool:
    """Atomically claim 'this user+window is handled'.
    True  → we won the claim, send now.
    False → another hit already covered this window, skip (duplicate).
    Fails OPEN: no client / Redis error → True (a rare duplicate beats a
    missed reminder)."""
    if client is None:
        return True
    try:
        return bool(client.set(
            _claim_key(user_id, window_start), "1",
            nx=True, ex=CLAIM_TTL_SECONDS))
    except Exception as exc:
        logger.warning(f"Reminder dedup claim failed, sending anyway: {exc}")
        return True


def _release_window(client, user_id: int, window_start: datetime) -> None:
    """Release a claim after a FAILED send so a later hit in the same
    window can retry. Best-effort."""
    if client is None:
        return
    try:
        client.delete(_claim_key(user_id, window_start))
    except Exception:
        pass


@router.get("/reminders", response_model=StandardResponse)
async def run_reminders(
    _: None = Depends(verify_cron_secret),
    db: Session = Depends(get_db)
):
    """Send BP measurement reminders due in the current 15-minute window."""
    request_id = str(uuid.uuid4())
    now_utc = datetime.now(pytz.UTC)

    # Keep-alive: ping Redis every cron run so Upstash never sees the
    # database as idle (free tier deletes inactive databases — this
    # already bit us once). Never blocks reminders. Import-guarded:
    # redis_health ships in the fix/redis-resilience branch.
    redis_status = "unknown"
    try:
        import asyncio as _asyncio
        from ..utils.redis_health import ping_redis
        redis_status = await _asyncio.to_thread(ping_redis)
    except ImportError:
        pass

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

    dedup = _dedup_client()
    checked = sent = failed = duplicate = 0
    try:
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
            window_start, window_end = bounds
            if not _due_in_window(prefs.reminder_times, window_start, window_end):
                continue

            # Idempotency: a backstop or jittery scheduler firing twice in
            # the SAME window must not double-send. First hit claims the
            # window; later hits skip. Released below on send failure so a
            # retry within the window can still get through.
            if not _claim_window(dedup, user.id, window_start):
                duplicate += 1
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
                    _release_window(dedup, user.id, window_start)
            except Exception as exc:
                failed += 1
                _release_window(dedup, user.id, window_start)
                logger.error(f"Reminder to user {user.id} raised: {exc}")
    finally:
        if dedup is not None:
            try:
                dedup.close()
            except Exception:
                pass

    logger.info(
        f"Reminder cron: due={checked} sent={sent} failed={failed} "
        f"duplicate_skipped={duplicate} redis={redis_status} "
        f"- Request ID: {request_id}")

    return StandardResponse(
        status="success",
        message="Reminder run complete",
        data={"due": checked, "sent": sent, "failed": failed,
              "duplicate_skipped": duplicate, "redis": redis_status},
        request_id=request_id,
    )
