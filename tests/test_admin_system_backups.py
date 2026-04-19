"""Tests for System-level admin API — Neon branch backup management.

Spec: plan/v2-asm-org-support/BACKUP_AND_MIGRATION_SPEC.md
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from app.models import AdminAuditLog, User
from app.services import neon_service
from app.utils.security import create_access_token, hash_password


def _run(coro):
    """Run an async coroutine synchronously for a unit test."""
    return asyncio.new_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# ── Helpers ──────────────────────────────────────────────────────

def _make_user(db, role="patient", **kwargs):
    user = User(
        role=role,
        verification_status=kwargs.get("verification_status", "verified"),
        is_active=True,
        is_email_verified=False,
        is_phone_verified=False,
        language="en",
        password_hash=hash_password("testpass123"),
    )
    user.full_name = kwargs.get("full_name", f"Test {role.title()}")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user):
    token = create_access_token({"user_id": user.id})
    return {"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"}


def _branch(
    branch_id="br-test-1",
    name="pre-v2-2026-04-18",
    default=False,
    protected=False,
    parent_id="br-main",
):
    return {
        "id": branch_id,
        "name": name,
        "default": default,
        "protected": protected,
        "parent_id": parent_id,
        "current_state": "ready",
        "logical_size": 42_000_000,
        "created_at": "2026-04-18T12:00:00Z",
        "updated_at": "2026-04-18T12:00:00Z",
    }


@pytest.fixture(autouse=True)
def neon_env(monkeypatch):
    """Default Neon env for the whole module. Also clears STAFF_ALLOWLIST so
    the default-allowed behavior applies unless a test opts in."""
    monkeypatch.setenv("NEON_API_KEY", "test-neon-key")
    monkeypatch.setenv("NEON_PROJECT_ID", "test-project-id")
    monkeypatch.delenv("STAFF_ALLOWLIST", raising=False)
    yield


# ══════════════════════════════════════════════════════════════════
# neon_service unit tests (mocked httpx)
# ══════════════════════════════════════════════════════════════════

class TestNeonService:

    def test_config_missing_raises(self, monkeypatch):
        monkeypatch.delenv("NEON_API_KEY", raising=False)
        with pytest.raises(Exception) as exc:
            neon_service._config()
        assert "not configured" in str(exc.value).lower()

    def test_list_branches_parses_response(self):
        fake_resp = type("R", (), {
            "status_code": 200,
            "json": lambda self: {"branches": [_branch()]},
            "text": "",
        })()
        with patch("httpx.AsyncClient") as Mock:
            client = Mock.return_value.__aenter__.return_value
            client.get = AsyncMock(return_value=fake_resp)
            out = _run(neon_service.list_branches())
        assert len(out) == 1
        assert out[0]["id"] == "br-test-1"

    def test_list_branches_raises_on_non_200(self):
        fake_resp = type("R", (), {"status_code": 401, "text": "unauthorized"})()
        with patch("httpx.AsyncClient") as Mock:
            client = Mock.return_value.__aenter__.return_value
            client.get = AsyncMock(return_value=fake_resp)
            with pytest.raises(Exception) as exc:
                _run(neon_service.list_branches())
        assert "502" in str(exc.value) or "Neon" in str(exc.value)

    def test_get_default_branch_id(self):
        branches = [_branch(branch_id="br-1"), _branch(branch_id="br-main", default=True)]
        with patch.object(neon_service, "list_branches", AsyncMock(return_value=branches)):
            out = _run(neon_service.get_default_branch_id())
        assert out == "br-main"

    def test_create_branch_uses_default_parent_when_unset(self):
        created = {"branch": _branch(branch_id="br-new", name="backup-1")}
        fake_resp = type("R", (), {
            "status_code": 201,
            "json": lambda self: created,
            "text": "",
        })()
        with patch.object(
            neon_service, "get_default_branch_id", AsyncMock(return_value="br-main")
        ), patch("httpx.AsyncClient") as Mock:
            client = Mock.return_value.__aenter__.return_value
            post_mock = AsyncMock(return_value=fake_resp)
            client.post = post_mock
            out = _run(neon_service.create_branch("backup-1"))
        assert out == created
        call_kwargs = post_mock.call_args.kwargs
        assert call_kwargs["json"]["branch"]["parent_id"] == "br-main"
        assert call_kwargs["json"]["branch"]["name"] == "backup-1"

    def test_create_branch_forwards_4xx_error(self):
        fake_resp = type("R", (), {"status_code": 409, "text": "name taken"})()
        with patch.object(
            neon_service, "get_default_branch_id", AsyncMock(return_value="br-main")
        ), patch("httpx.AsyncClient") as Mock:
            client = Mock.return_value.__aenter__.return_value
            client.post = AsyncMock(return_value=fake_resp)
            with pytest.raises(Exception) as exc:
                _run(neon_service.create_branch("dup"))
        assert "409" in str(exc.value) or "name taken" in str(exc.value)

    def test_delete_branch_accepts_202(self):
        fake_resp = type("R", (), {"status_code": 202, "text": ""})()
        with patch("httpx.AsyncClient") as Mock:
            client = Mock.return_value.__aenter__.return_value
            client.delete = AsyncMock(return_value=fake_resp)
            _run(neon_service.delete_branch("br-new"))


# ══════════════════════════════════════════════════════════════════
# Access control
# ══════════════════════════════════════════════════════════════════

class TestAccessControl:

    def test_staff_can_list_backups(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        with patch.object(
            neon_service, "list_branches", AsyncMock(return_value=[_branch(default=True, name="main")])
        ):
            resp = test_client.get("/api/v1/admin/system/backups", headers=_headers(staff))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "success"
        assert len(body["data"]["branches"]) == 1
        assert body["data"]["branches"][0]["is_default"] is True

    def test_patient_gets_403(self, test_client, db_session):
        patient = _make_user(db_session, role="patient")
        resp = test_client.get("/api/v1/admin/system/backups", headers=_headers(patient))
        assert resp.status_code == 403

    def test_doctor_gets_403(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor")
        resp = test_client.get("/api/v1/admin/system/backups", headers=_headers(doctor))
        assert resp.status_code == 403

    def test_missing_api_key_rejected(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        token = create_access_token({"user_id": staff.id})
        resp = test_client.get(
            "/api/v1/admin/system/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (401, 403, 422)

    def test_allowlist_blocks_unlisted_staff(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        with patch.dict(os.environ, {"STAFF_ALLOWLIST": "99999"}):
            resp = test_client.get("/api/v1/admin/system/backups", headers=_headers(staff))
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
# Create backup
# ══════════════════════════════════════════════════════════════════

class TestCreateBackup:

    def test_happy_path_creates_and_audits(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        created = {"branch": _branch(branch_id="br-new", name="pre-v2-2026-04-18")}
        with patch.object(neon_service, "create_branch", AsyncMock(return_value=created)) as mock_create:
            resp = test_client.post(
                "/api/v1/admin/system/backups",
                headers=_headers(staff),
                json={"name": "pre-v2-2026-04-18", "description": "Before v2"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["branch"]["id"] == "br-new"
        mock_create.assert_awaited_once_with(name="pre-v2-2026-04-18")

        # Audit row written
        audit = (
            db_session.query(AdminAuditLog)
            .filter(AdminAuditLog.action == "system_backup_created")
            .order_by(AdminAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        details = json.loads(audit.details)
        assert details["branch_name"] == "pre-v2-2026-04-18"
        assert details["branch_id"] == "br-new"
        assert details["description"] == "Before v2"
        assert audit.admin_user_id == staff.id

    def test_invalid_branch_name_rejected_422(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        # Uppercase / too short / starts with hyphen
        for bad in ["Bad_Name", "ab", "-leading", "x" * 65]:
            resp = test_client.post(
                "/api/v1/admin/system/backups",
                headers=_headers(staff),
                json={"name": bad},
            )
            assert resp.status_code == 422, f"{bad!r} unexpectedly accepted"

    def test_short_name_below_pydantic_minlen_is_422(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        resp = test_client.post(
            "/api/v1/admin/system/backups",
            headers=_headers(staff),
            json={"name": "ab"},
        )
        assert resp.status_code == 422

    def test_no_audit_when_neon_fails(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        before = db_session.query(AdminAuditLog).filter(
            AdminAuditLog.action == "system_backup_created"
        ).count()
        from fastapi import HTTPException

        async def raise_err(*_a, **_kw):
            raise HTTPException(502, "Neon down")

        with patch.object(neon_service, "create_branch", side_effect=raise_err):
            resp = test_client.post(
                "/api/v1/admin/system/backups",
                headers=_headers(staff),
                json={"name": "valid-name"},
            )
        assert resp.status_code == 502
        after = db_session.query(AdminAuditLog).filter(
            AdminAuditLog.action == "system_backup_created"
        ).count()
        assert after == before


# ══════════════════════════════════════════════════════════════════
# Delete backup
# ══════════════════════════════════════════════════════════════════

class TestDeleteBackup:

    def test_happy_path(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        branches = [
            _branch(branch_id="br-main", name="main", default=True),
            _branch(branch_id="br-del", name="backup-to-delete"),
        ]
        with patch.object(
            neon_service, "list_branches", AsyncMock(return_value=branches)
        ), patch.object(
            neon_service, "delete_branch", AsyncMock(return_value=None)
        ) as mock_del:
            resp = test_client.delete(
                "/api/v1/admin/system/backups/br-del", headers=_headers(staff)
            )
        assert resp.status_code == 200, resp.text
        mock_del.assert_awaited_once_with("br-del")

        audit = (
            db_session.query(AdminAuditLog)
            .filter(AdminAuditLog.action == "system_backup_deleted")
            .order_by(AdminAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert json.loads(audit.details)["branch_id"] == "br-del"

    def test_cannot_delete_default_branch(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        branches = [_branch(branch_id="br-main", name="main", default=True)]
        with patch.object(
            neon_service, "list_branches", AsyncMock(return_value=branches)
        ), patch.object(
            neon_service, "delete_branch", AsyncMock(return_value=None)
        ) as mock_del:
            resp = test_client.delete(
                "/api/v1/admin/system/backups/br-main", headers=_headers(staff)
            )
        assert resp.status_code == 400
        mock_del.assert_not_awaited()

    def test_missing_branch_returns_404(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        branches = [_branch(branch_id="br-main", name="main", default=True)]
        with patch.object(
            neon_service, "list_branches", AsyncMock(return_value=branches)
        ):
            resp = test_client.delete(
                "/api/v1/admin/system/backups/br-missing", headers=_headers(staff)
            )
        assert resp.status_code == 404

    def test_cannot_delete_protected_branch(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        branches = [_branch(branch_id="br-prot", name="prot", protected=True)]
        with patch.object(
            neon_service, "list_branches", AsyncMock(return_value=branches)
        ):
            resp = test_client.delete(
                "/api/v1/admin/system/backups/br-prot", headers=_headers(staff)
            )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════
# Audit log endpoint
# ══════════════════════════════════════════════════════════════════

class TestSystemAuditLog:

    def test_returns_only_system_backup_actions(self, test_client, db_session):
        staff = _make_user(db_session, role="staff")
        # Seed mixed audit rows
        db_session.add(AdminAuditLog(admin_user_id=staff.id, action="deactivate_user",
                                     target_user_id=staff.id, details="other"))
        db_session.add(AdminAuditLog(admin_user_id=staff.id, action="system_backup_created",
                                     target_user_id=None, details='{"branch_name": "x"}'))
        db_session.add(AdminAuditLog(admin_user_id=staff.id, action="system_backup_deleted",
                                     target_user_id=None, details='{"branch_id": "br-x"}'))
        db_session.commit()

        resp = test_client.get("/api/v1/admin/system/audit-log", headers=_headers(staff))
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        actions = {e["action"] for e in entries}
        assert "system_backup_created" in actions
        assert "system_backup_deleted" in actions
        assert "deactivate_user" not in actions


# ══════════════════════════════════════════════════════════════════
# Env var missing
# ══════════════════════════════════════════════════════════════════

class TestUnconfigured:

    def test_missing_api_key_returns_500(self, test_client, db_session, monkeypatch):
        staff = _make_user(db_session, role="staff")
        monkeypatch.delenv("NEON_API_KEY", raising=False)
        resp = test_client.get("/api/v1/admin/system/backups", headers=_headers(staff))
        assert resp.status_code == 500
        assert "not configured" in resp.json()["detail"].lower()
