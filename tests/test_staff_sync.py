import logging

from sqlalchemy import text

from app.models import StaffManagementState, User
from app.utils.security import hash_password
from app.utils.staff_sync import ensure_staff_sync_for_request, reset_staff_sync_state


def _make_user(db, role="patient", full_name="Test User", email=None, phone_number=None, telegram_id=None):
    user = User(
        role=role,
        verification_status="verified",
        is_active=True,
        is_email_verified=bool(email),
        is_phone_verified=bool(phone_number),
        language="en",
        password_hash=hash_password("testpass123"),
    )
    user.full_name = full_name
    if email:
        user.email = email
    if phone_number:
        user.phone_number = phone_number
    if telegram_id is not None:
        user.telegram_id = telegram_id
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_env_state(db, user, original_role="patient"):
    state = StaffManagementState(
        user_id=user.id,
        management_source="env",
        original_role=original_role,
        last_sync_action="promote",
    )
    db.add(state)
    db.commit()
    return state


def _reset(monkeypatch):
    monkeypatch.delenv("STAFF_ALLOWLIST", raising=False)
    monkeypatch.delenv("STAFF_SYNC_MODE", raising=False)
    monkeypatch.delenv("STAFF_SYNC_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("STAFF_SYNC_LOCK_TIMEOUT_MS", raising=False)
    reset_staff_sync_state()


def test_missing_allowlist_skips_sync(db_session, monkeypatch):
    _reset(monkeypatch)
    user = _make_user(db_session, role="patient", full_name="Missing Env")

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(user)

    assert user.role == "patient"
    assert db_session.query(StaffManagementState).count() == 0


def test_empty_allowlist_skips_sync_and_warns(db_session, monkeypatch, caplog):
    _reset(monkeypatch)
    monkeypatch.setenv("STAFF_ALLOWLIST", "")
    monkeypatch.setenv("STAFF_SYNC_MODE", "apply")
    user = _make_user(db_session, role="patient", full_name="Empty Env")

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(user)

    assert user.role == "patient"
    assert "Use STAFF_ALLOWLIST=NONE" in caplog.text


def test_none_sentinel_demotes_only_env_managed_staff(db_session, monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("STAFF_ALLOWLIST", "NONE")
    monkeypatch.setenv("STAFF_SYNC_MODE", "apply")

    env_staff = _make_user(db_session, role="staff", full_name="Env Staff")
    manual_staff = _make_user(db_session, role="staff", full_name="Manual Staff")
    _add_env_state(db_session, env_staff, original_role="doctor")

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(env_staff)
    db_session.refresh(manual_staff)

    assert env_staff.role == "doctor"
    assert manual_staff.role == "staff"
    assert db_session.query(StaffManagementState).count() == 0


def test_dry_run_logs_without_writes(db_session, monkeypatch, caplog):
    _reset(monkeypatch)
    caplog.set_level(logging.INFO)
    monkeypatch.setenv(
        "STAFF_ALLOWLIST",
        "user:999999,email:alpha@example.com,phone:+66811111111,telegram:32971348",
    )
    monkeypatch.setenv("STAFF_SYNC_MODE", "dry-run")

    email_user = _make_user(db_session, role="patient", full_name="Email User", email="alpha@example.com")
    phone_user = _make_user(db_session, role="doctor", full_name="Phone User", phone_number="+66811111111")
    telegram_user = _make_user(db_session, role="patient", full_name="Telegram User", telegram_id=32971348)

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(email_user)
    db_session.refresh(phone_user)
    db_session.refresh(telegram_user)

    assert email_user.role == "patient"
    assert phone_user.role == "doctor"
    assert telegram_user.role == "patient"
    assert db_session.query(StaffManagementState).count() == 0
    assert "Would promote user" in caplog.text
    assert "unmatched=1" in caplog.text


def test_apply_promotes_and_creates_state(db_session, monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("STAFF_ALLOWLIST", "email:beta@example.com")
    monkeypatch.setenv("STAFF_SYNC_MODE", "apply")
    user = _make_user(db_session, role="doctor", full_name="Beta", email="beta@example.com")

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(user)
    state = db_session.query(StaffManagementState).filter(StaffManagementState.user_id == user.id).first()

    assert user.role == "staff"
    assert state is not None
    assert state.original_role == "doctor"


def test_sync_runs_once_per_process_for_same_signature(db_session, monkeypatch, caplog):
    _reset(monkeypatch)
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("STAFF_ALLOWLIST", "user:1")
    monkeypatch.setenv("STAFF_SYNC_MODE", "dry-run")

    ensure_staff_sync_for_request(db_session)
    first_logs = caplog.text
    caplog.clear()

    ensure_staff_sync_for_request(db_session)

    assert "[staff-sync] mode=dry-run" in first_logs
    assert "[staff-sync] mode=dry-run" not in caplog.text


def test_missing_metadata_table_skips_without_crashing(db_session, monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("STAFF_ALLOWLIST", "user:1")
    monkeypatch.setenv("STAFF_SYNC_MODE", "apply")
    user = _make_user(db_session, role="patient", full_name="No Table")

    db_session.execute(text("DROP TABLE staff_management_states"))
    db_session.commit()

    ensure_staff_sync_for_request(db_session)
    db_session.refresh(user)

    assert user.role == "patient"

    StaffManagementState.__table__.create(bind=db_session.bind, checkfirst=True)