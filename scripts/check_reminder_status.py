"""Diagnose why a user does (or does not) receive BP reminders.

Read-only. Mirrors the EXACT gates the reminder cron applies, by reusing
the cron's own helpers (`_window_bounds`, `_due_in_window`) and the
NotificationService's `parse_preferences`, so the verdict can't drift
from real behaviour.

Usage:
    python3 -m scripts.check_reminder_status --phone 0812345678
    python3 -m scripts.check_reminder_status --email user@example.com
    python3 -m scripts.check_reminder_status --telegram 123456789
    python3 -m scripts.check_reminder_status --id 42
    python3 -m scripts.check_reminder_status --list      # everyone with reminders enabled

What it answers:
    - Is Telegram actually paired? (telegram_id_hash set AND decryptable)
    - Active web-push subscriptions?
    - Is the user REACHABLE by the cron at all? (the silent-skip gate)
    - reminder_enabled / reminder_times / timezone / is_active
    - Given the server's current time, would a reminder be due right now?
    - The FIRST blocking gate, if any.
"""

import argparse
import os
import sys

import pytz
from dotenv import load_dotenv

# Repo root on path so `app` imports resolve when run as a module or script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from datetime import datetime  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import PushSubscription, User  # noqa: E402
from app.routers.cron import _due_in_window, _window_bounds  # noqa: E402
from app.services.notification_service import parse_preferences  # noqa: E402
from app.utils.encryption import hash_value  # noqa: E402


def _lookup(db, args) -> User | None:
    if args.id:
        return db.query(User).filter(User.id == int(args.id)).first()
    if args.phone:
        return db.query(User).filter(
            User.phone_number_hash == hash_value(args.phone)).first()
    if args.email:
        return db.query(User).filter(
            User.email_hash == hash_value(args.email)).first()
    if args.telegram:
        return db.query(User).filter(
            User.telegram_id_hash == hash_value(str(args.telegram))).first()
    return None


def _diagnose(db, user: User, now_utc: datetime) -> None:
    prefs = parse_preferences(user.notification_preferences)

    paired_hash = bool(user.telegram_id_hash)
    tg_id = user.telegram_id  # decrypts; None if missing OR key mismatch
    decrypt_ok = tg_id is not None
    push_active = db.query(PushSubscription).filter(
        PushSubscription.user_id == user.id,
        PushSubscription.is_active == True,  # noqa: E712
    ).count()

    reachable = paired_hash or push_active > 0

    bounds = _window_bounds(now_utc, user.timezone)
    tz_valid = bounds is not None
    due_now = bool(bounds) and _due_in_window(prefs.reminder_times, *bounds)

    print(f"\nUser #{user.id}  (role={user.role})")
    print(f"  is_active:            {user.is_active}")
    print(f"  timezone:            {user.timezone!r}  (valid={tz_valid})")
    print(f"  language:            {user.language!r}")
    print(f"  telegram paired:     hash={'set' if paired_hash else 'NULL'}"
          f"  decrypt={'ok -> ' + str(tg_id) if decrypt_ok else 'FAILED/none'}")
    print(f"  active push subs:    {push_active}")
    print(f"  REACHABLE by cron:   {reachable}")
    print(f"  reminder_enabled:    {prefs.reminder_enabled}")
    print(f"  reminder_times:      {prefs.reminder_times}")

    if bounds:
        local_now = now_utc.astimezone(pytz.timezone(user.timezone or "Asia/Bangkok"))
        ws, we = bounds
        print("  --- current window ---")
        print(f"  now (UTC):           {now_utc.isoformat()}")
        print(f"  user local now:      {local_now.strftime('%Y-%m-%d %H:%M')}")
        print(f"  window:              [{ws.strftime('%H:%M')}, {we.strftime('%H:%M')})")
        print(f"  due in window now:   {due_now}")

    # First blocking gate, in the same order the cron applies them.
    blockers = []
    if not user.is_active:
        blockers.append("is_active=False -> cron never even queries this user.")
    if not reachable:
        blockers.append(
            "NOT REACHABLE: no Telegram pairing and no active push sub -> "
            "SILENTLY SKIPPED. Fix: pair Telegram (send /start to the bot) "
            "or enable web push.")
    if paired_hash and not decrypt_ok:
        blockers.append(
            "Telegram hash is set but telegram_id can't be decrypted "
            "(ENCRYPTION_KEY mismatch?) -> Telegram send returns 'not_paired' "
            "and counts as FAILED, not skipped.")
    if not prefs.reminder_enabled:
        blockers.append("reminder_enabled=False -> skipped.")
    if not prefs.reminder_times:
        blockers.append("reminder_times is empty -> nothing to fire.")
    if not tz_valid:
        blockers.append(
            f"timezone {user.timezone!r} is not a valid IANA name -> skipped.")

    print("  --- verdict ---")
    if blockers:
        print("  BLOCKING ISSUES:")
        for b in blockers:
            print(f"    - {b}")
    else:
        print("  No config blockers. This user fires correctly — but ONLY when a")
        print("  scheduler actually hits /api/v1/cron/reminders during one of their")
        print(f"  reminder windows ({', '.join(prefs.reminder_times)} {user.timezone}).")
        print("  Vercel's daily backstop (0 0 * * *) only covers the 07:00 window;")
        print("  09:00/19:00 need the external 15-min scheduler to be running.")


def _list_enabled(db, now_utc: datetime) -> None:
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    print(f"{'id':>5}  {'reach':>5}  {'enab':>4}  {'due':>3}  tz / times")
    for u in users:
        prefs = parse_preferences(u.notification_preferences)
        if not prefs.reminder_enabled or not prefs.reminder_times:
            continue
        push = db.query(PushSubscription).filter(
            PushSubscription.user_id == u.id,
            PushSubscription.is_active == True,  # noqa: E712
        ).count()
        reachable = bool(u.telegram_id_hash) or push > 0
        bounds = _window_bounds(now_utc, u.timezone)
        due = bool(bounds) and _due_in_window(prefs.reminder_times, *bounds)
        print(f"{u.id:>5}  {str(reachable):>5}  {'on':>4}  {str(due):>3}  "
              f"{u.timezone} / {prefs.reminder_times}")


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnose BP reminder delivery for a user.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--id")
    g.add_argument("--phone")
    g.add_argument("--email")
    g.add_argument("--telegram")
    g.add_argument("--list", action="store_true",
                   help="List all active users with reminders enabled.")
    args = p.parse_args()

    now_utc = datetime.now(pytz.UTC)
    db = SessionLocal()
    try:
        if args.list:
            _list_enabled(db, now_utc)
            return
        user = _lookup(db, args)
        if not user:
            print("No matching user found.")
            sys.exit(1)
        _diagnose(db, user, now_utc)
    finally:
        db.close()


if __name__ == "__main__":
    main()
