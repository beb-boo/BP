import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from ..models import StaffManagementState, User
from .encryption import hash_value
from .timezone import now_tz

logger = logging.getLogger(__name__)

_CONFIG_CACHE_KEY: Optional[str] = None
_CONFIG_CACHE_VALUE = None
_SYNC_LOCK = threading.Lock()
_SYNC_SIGNATURE: Optional[Tuple[Optional[str], str]] = None

VALID_ORIGINAL_ROLES = {"patient", "doctor"}


@dataclass
class StaffAllowlistConfig:
    raw_state: str
    should_sync: bool
    enforce_access_filter: bool
    explicit_none: bool = False
    user_ids: Set[int] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    phone_hashes: Set[str] = field(default_factory=set)
    telegram_hashes: Set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def reset_staff_sync_state() -> None:
    global _CONFIG_CACHE_KEY, _CONFIG_CACHE_VALUE, _SYNC_SIGNATURE
    _CONFIG_CACHE_KEY = None
    _CONFIG_CACHE_VALUE = None
    _SYNC_SIGNATURE = None


def _normalize_sync_mode(raw_mode: Optional[str] = None) -> str:
    value = (raw_mode or os.getenv("STAFF_SYNC_MODE", "apply")).strip().lower()
    if value in {"apply", "dry-run"}:
        return value
    logger.warning("[staff-sync] Invalid STAFF_SYNC_MODE=%r, defaulting to apply", raw_mode or value)
    return "apply"


def _get_timeout_seconds() -> float:
    try:
        timeout_ms = int(os.getenv("STAFF_SYNC_TIMEOUT_MS", "800"))
    except ValueError:
        timeout_ms = 800
    return max(timeout_ms, 50) / 1000.0


def _get_lock_timeout_seconds() -> float:
    try:
        timeout_ms = int(os.getenv("STAFF_SYNC_LOCK_TIMEOUT_MS", "50"))
    except ValueError:
        timeout_ms = 50
    return max(timeout_ms, 0) / 1000.0


def get_staff_allowlist_config(raw_value: Optional[str] = None) -> StaffAllowlistConfig:
    global _CONFIG_CACHE_KEY, _CONFIG_CACHE_VALUE

    cache_key = "__MISSING__" if raw_value is None else raw_value
    if _CONFIG_CACHE_KEY == cache_key and _CONFIG_CACHE_VALUE is not None:
        return _CONFIG_CACHE_VALUE

    config = _parse_staff_allowlist(raw_value)
    _CONFIG_CACHE_KEY = cache_key
    _CONFIG_CACHE_VALUE = config
    return config


def _parse_staff_allowlist(raw_value: Optional[str]) -> StaffAllowlistConfig:
    if raw_value is None:
        return StaffAllowlistConfig(
            raw_state="missing",
            should_sync=False,
            enforce_access_filter=False,
        )

    stripped = raw_value.strip()
    if not stripped:
        return StaffAllowlistConfig(
            raw_state="empty",
            should_sync=False,
            enforce_access_filter=False,
            warnings=[
                "[staff-sync] STAFF_ALLOWLIST is empty; skipping sync. Use STAFF_ALLOWLIST=NONE to demote env-managed staff explicitly."
            ],
        )

    if stripped.upper() == "NONE":
        return StaffAllowlistConfig(
            raw_state="none",
            should_sync=True,
            enforce_access_filter=True,
            explicit_none=True,
        )

    user_ids: Set[int] = set()
    email_hashes: Set[str] = set()
    phone_hashes: Set[str] = set()
    telegram_hashes: Set[str] = set()
    warnings: list[str] = []

    for token in [part.strip() for part in stripped.split(",") if part.strip()]:
        prefix: Optional[str] = None
        value = token

        if ":" in token:
            prefix, value = token.split(":", 1)
            prefix = prefix.strip().lower()
            value = value.strip()
        elif "@" in token:
            prefix = "email"
        elif token.isdigit():
            prefix = "user"

        if not value:
            warnings.append(f"[staff-sync] Ignoring malformed allowlist entry: {token!r}")
            continue

        if prefix in {"user", "id", "user_id"}:
            if value.isdigit():
                user_ids.add(int(value))
            else:
                warnings.append(f"[staff-sync] Invalid user identifier: {token!r}")
        elif prefix in {"email"}:
            hashed = hash_value(value)
            if hashed:
                email_hashes.add(hashed)
            else:
                warnings.append(f"[staff-sync] Invalid email identifier: {token!r}")
        elif prefix in {"phone"}:
            hashed = hash_value(value)
            if hashed:
                phone_hashes.add(hashed)
            else:
                warnings.append(f"[staff-sync] Invalid phone identifier: {token!r}")
        elif prefix in {"telegram", "tg"}:
            hashed = hash_value(value)
            if hashed:
                telegram_hashes.add(hashed)
            else:
                warnings.append(f"[staff-sync] Invalid telegram identifier: {token!r}")
        else:
            warnings.append(
                f"[staff-sync] Ignoring unsupported allowlist entry: {token!r}. Supported prefixes: user:, email:, phone:, telegram:."
            )

    has_entries = any((user_ids, email_hashes, phone_hashes, telegram_hashes))
    if not has_entries:
        warnings.append("[staff-sync] STAFF_ALLOWLIST has no valid entries; skipping sync.")
        return StaffAllowlistConfig(
            raw_state="invalid",
            should_sync=False,
            enforce_access_filter=False,
            warnings=warnings,
        )

    return StaffAllowlistConfig(
        raw_state="configured",
        should_sync=True,
        enforce_access_filter=True,
        user_ids=user_ids,
        email_hashes=email_hashes,
        phone_hashes=phone_hashes,
        telegram_hashes=telegram_hashes,
        warnings=warnings,
    )


def is_staff_access_allowed(user: User) -> bool:
    config = get_staff_allowlist_config(os.getenv("STAFF_ALLOWLIST"))
    if not config.enforce_access_filter:
        return True
    if config.explicit_none:
        return False
    if user.id in config.user_ids:
        return True

    if user.email and hash_value(user.email) in config.email_hashes:
        return True
    if user.phone_number and hash_value(user.phone_number) in config.phone_hashes:
        return True
    if user.telegram_id is not None and hash_value(str(user.telegram_id)) in config.telegram_hashes:
        return True
    return False


def ensure_staff_sync_for_request(db: Session) -> None:
    global _SYNC_SIGNATURE

    raw_allowlist = os.getenv("STAFF_ALLOWLIST")
    mode = _normalize_sync_mode()
    signature = (raw_allowlist, mode)
    if signature == _SYNC_SIGNATURE:
        return

    if not _SYNC_LOCK.acquire(timeout=_get_lock_timeout_seconds()):
        logger.warning("[staff-sync] Another request is already running sync; skipping this request.")
        return

    try:
        if signature == _SYNC_SIGNATURE:
            return

        config = get_staff_allowlist_config(raw_allowlist)
        for warning in config.warnings:
            logger.warning(warning)

        if not config.should_sync:
            _SYNC_SIGNATURE = signature
            return

        if not _metadata_table_exists(db):
            logger.warning(
                "[staff-sync] Metadata table '%s' is missing; skipping sync until migrations are applied.",
                StaffManagementState.__tablename__,
            )
            _SYNC_SIGNATURE = signature
            return

        deadline = time.monotonic() + _get_timeout_seconds()
        result = _run_sync(db, config, mode, deadline)
        if result["completed"]:
            _SYNC_SIGNATURE = signature
    finally:
        _SYNC_LOCK.release()


def _metadata_table_exists(db: Session) -> bool:
    try:
        inspector = sqlalchemy_inspect(db.get_bind())
        return inspector.has_table(StaffManagementState.__tablename__)
    except Exception as exc:
        logger.warning("[staff-sync] Failed to inspect metadata table: %s", exc)
        return False


def _collect_target_users(db: Session, config: StaffAllowlistConfig, deadline: float) -> tuple[Dict[int, User], dict[str, int]]:
    matched_users: Dict[int, User] = {}
    unmatched = {
        "user": len(config.user_ids),
        "email": len(config.email_hashes),
        "phone": len(config.phone_hashes),
        "telegram": len(config.telegram_hashes),
    }

    if time.monotonic() > deadline:
        raise TimeoutError("target resolution timed out before queries started")

    if config.user_ids:
        users = db.query(User).filter(User.id.in_(config.user_ids)).all()
        for user in users:
            matched_users[user.id] = user
        unmatched["user"] -= len(users)

    if config.email_hashes:
        users = db.query(User).filter(User.email_hash.in_(config.email_hashes)).all()
        seen_hashes = {user.email_hash for user in users if user.email_hash}
        for user in users:
            matched_users[user.id] = user
        unmatched["email"] -= len(seen_hashes)

    if config.phone_hashes:
        users = db.query(User).filter(User.phone_number_hash.in_(config.phone_hashes)).all()
        seen_hashes = {user.phone_number_hash for user in users if user.phone_number_hash}
        for user in users:
            matched_users[user.id] = user
        unmatched["phone"] -= len(seen_hashes)

    if config.telegram_hashes:
        users = db.query(User).filter(User.telegram_id_hash.in_(config.telegram_hashes)).all()
        seen_hashes = {user.telegram_id_hash for user in users if user.telegram_id_hash}
        for user in users:
            matched_users[user.id] = user
        unmatched["telegram"] -= len(seen_hashes)

    return matched_users, unmatched


def _run_sync(db: Session, config: StaffAllowlistConfig, mode: str, deadline: float) -> dict:
    summary = {
        "mode": mode,
        "completed": False,
        "promoted": 0,
        "demoted": 0,
        "unchanged": 0,
        "unmatched": 0,
        "timed_out": False,
    }

    try:
        target_users, unmatched = _collect_target_users(db, config, deadline)
    except TimeoutError:
        logger.warning("[staff-sync] Timed out while resolving allowlist targets.")
        summary["timed_out"] = True
        return summary

    summary["unmatched"] = sum(unmatched.values())
    configured_target_ids = set(target_users.keys())

    existing_states = db.query(StaffManagementState).filter(
        StaffManagementState.management_source == "env"
    ).all()
    existing_by_user_id = {state.user_id: state for state in existing_states}

    all_user_ids = set(target_users.keys()) | set(existing_by_user_id.keys())
    if all_user_ids and time.monotonic() > deadline:
        logger.warning("[staff-sync] Timed out before loading sync candidates.")
        summary["timed_out"] = True
        return summary

    missing_ids = all_user_ids.difference(target_users.keys())
    if missing_ids:
        users = db.query(User).filter(User.id.in_(missing_ids)).all()
        for user in users:
            target_users[user.id] = user

    action_logs: list[str] = []
    new_states: list[StaffManagementState] = []
    delete_states: list[StaffManagementState] = []

    for user_id in sorted(configured_target_ids):
        user = target_users[user_id]
        state = existing_by_user_id.get(user_id)
        if state is None and user.role != "staff":
            summary["promoted"] += 1
            action_logs.append(f"Would promote user {user.id} ({user.role} -> staff)")
            if mode == "apply":
                new_states.append(
                    StaffManagementState(
                        user_id=user.id,
                        management_source="env",
                        original_role=user.role,
                        last_sync_action="promote",
                        last_synced_at=now_tz(),
                    )
                )
                user.role = "staff"
        elif state is not None and user.role != "staff":
            summary["promoted"] += 1
            action_logs.append(f"Would restore env-managed user {user.id} back to staff")
            if mode == "apply":
                state.last_sync_action = "promote"
                state.last_synced_at = now_tz()
                user.role = "staff"
        else:
            summary["unchanged"] += 1

    for user_id, state in sorted(existing_by_user_id.items()):
        if user_id in configured_target_ids:
            continue

        user = target_users.get(user_id)
        if user is None:
            action_logs.append(f"Would delete stale env-managed metadata for missing user {user_id}")
            if mode == "apply":
                delete_states.append(state)
            continue

        if state.original_role not in VALID_ORIGINAL_ROLES:
            logger.error(
                "[staff-sync] Skipping demotion for user %s because original_role=%r is invalid.",
                user.id,
                state.original_role,
            )
            continue

        if user.role == "staff":
            summary["demoted"] += 1
            action_logs.append(f"Would demote user {user.id} (staff -> {state.original_role})")
            if mode == "apply":
                user.role = state.original_role
                delete_states.append(state)
        else:
            action_logs.append(f"Would clear stale env-managed metadata for user {user.id}")
            if mode == "apply":
                delete_states.append(state)

    if mode == "apply":
        if time.monotonic() > deadline:
            db.rollback()
            logger.warning("[staff-sync] Timed out before applying changes.")
            summary["timed_out"] = True
            return summary

        for state in new_states:
            db.merge(state)
        for state in delete_states:
            db.delete(state)
        if new_states or delete_states or summary["promoted"] or summary["demoted"]:
            db.commit()
        else:
            db.rollback()

    for message in action_logs:
        logger.warning("[staff-sync] %s", message)

    if config.explicit_none and summary["demoted"]:
        logger.warning("[staff-sync] STAFF_ALLOWLIST=NONE will remove %s env-managed staff entries.", summary["demoted"])

    logger.info(
        "[staff-sync] mode=%s promoted=%s demoted=%s unchanged=%s unmatched=%s timed_out=%s",
        summary["mode"],
        summary["promoted"],
        summary["demoted"],
        summary["unchanged"],
        summary["unmatched"],
        summary["timed_out"],
    )
    summary["completed"] = not summary["timed_out"]
    return summary