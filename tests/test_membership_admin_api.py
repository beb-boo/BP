"""Tests for Membership Admin API — Phase 5 of Membership Admin & Doctor Hardening."""

import os
import pytest
from unittest.mock import patch
from app.models import User, AdminAuditLog
from app.utils.security import hash_password, create_access_token
from app.utils.timezone import now_tz


# ── Helpers ──────────────────────────────────────────────────────

def _make_user(db, role="patient", verification_status="verified", is_active=True, **kwargs):
    user = User(
        role=role,
        verification_status=verification_status,
        is_active=is_active,
        is_email_verified=False,
        is_phone_verified=False,
        language="en",
        password_hash=hash_password("testpass123"),
    )
    user.full_name = kwargs.get("full_name", f"Test {role.title()}")
    if kwargs.get("email"):
        user.email = kwargs["email"]
    if kwargs.get("phone_number"):
        user.phone_number = kwargs["phone_number"]
    if kwargs.get("medical_license"):
        user.medical_license = kwargs["medical_license"]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user):
    token = create_access_token({"user_id": user.id})
    return {"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"}


# ══════════════════════════════════════════════════════════════════
# Access Control
# ══════════════════════════════════════════════════════════════════

class TestAdminAccessControl:

    def test_staff_can_list_users(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Admin")
        resp = test_client.get("/api/v1/admin/users", headers=_headers(staff))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "users" in data["data"]

    def test_patient_cannot_access_admin(self, test_client, db_session):
        patient = _make_user(db_session, role="patient", full_name="Patient NoAdmin")
        resp = test_client.get("/api/v1/admin/users", headers=_headers(patient))
        assert resp.status_code == 403

    def test_doctor_cannot_access_admin(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", full_name="Doctor NoAdmin")
        resp = test_client.get("/api/v1/admin/users", headers=_headers(doctor))
        assert resp.status_code == 403

    def test_allowlist_blocks_unlisted_staff(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Blocked")
        # Set allowlist to a different ID
        with patch.dict(os.environ, {"STAFF_ALLOWLIST": "99999"}):
            resp = test_client.get("/api/v1/admin/users", headers=_headers(staff))
            assert resp.status_code == 403

    def test_allowlist_allows_listed_staff(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Allowed")
        with patch.dict(os.environ, {"STAFF_ALLOWLIST": str(staff.id)}):
            resp = test_client.get("/api/v1/admin/users", headers=_headers(staff))
            assert resp.status_code == 200


# ═���════════════════════��═══════════════════════════════════════════
# Doctor Verification
# ══════════════════════════════════════════════════════════════════

class TestAdminDoctorVerification:

    def test_verify_doctor_changes_status(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Verifier")
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr Pending", medical_license="LIC001")
        resp = test_client.post(
            f"/api/v1/admin/users/{doctor.id}/verify",
            json={"action": "verify", "reason": "License checked"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["verification_status"] == "verified"

    def test_reject_doctor_changes_status(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Rejector")
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr ToReject", medical_license="LIC002")
        resp = test_client.post(
            f"/api/v1/admin/users/{doctor.id}/verify",
            json={"action": "reject", "reason": "Invalid license"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["verification_status"] == "rejected"

    def test_verify_non_doctor_fails(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff VerifyFail")
        patient = _make_user(db_session, role="patient", full_name="Patient NotDoctor")
        resp = test_client.post(
            f"/api/v1/admin/users/{patient.id}/verify",
            json={"action": "verify", "reason": "Test verify non-doctor"},
            headers=_headers(staff),
        )
        assert resp.status_code == 400

    def test_audit_log_created_on_verify(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Auditor")
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr Audit", medical_license="LIC003")
        test_client.post(
            f"/api/v1/admin/users/{doctor.id}/verify",
            json={"action": "verify", "reason": "Audit test"},
            headers=_headers(staff),
        )
        entry = db_session.query(AdminAuditLog).filter(
            AdminAuditLog.admin_user_id == staff.id,
            AdminAuditLog.target_user_id == doctor.id,
        ).first()
        assert entry is not None
        assert "verify" in entry.action


# ══════════════════════════════════════════════════════════════════
# Deactivate / Activate
# ═══════════════════���═════════════════════════════════���════════════

class TestAdminDeactivateActivate:

    def test_deactivate_user(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Deact")
        patient = _make_user(db_session, role="patient", full_name="Patient ToDeact")
        resp = test_client.post(
            f"/api/v1/admin/users/{patient.id}/deactivate",
            json={"reason": "Test deactivation"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        db_session.refresh(patient)
        assert patient.is_active is False

    def test_cannot_deactivate_self(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Self")
        resp = test_client.post(
            f"/api/v1/admin/users/{staff.id}/deactivate",
            json={"reason": "Self deactivation test"},
            headers=_headers(staff),
        )
        assert resp.status_code == 400

    def test_cannot_deactivate_staff(self, test_client, db_session):
        staff1 = _make_user(db_session, role="staff", full_name="Staff One")
        staff2 = _make_user(db_session, role="staff", full_name="Staff Two")
        resp = test_client.post(
            f"/api/v1/admin/users/{staff2.id}/deactivate",
            json={"reason": "Staff deactivation test"},
            headers=_headers(staff1),
        )
        assert resp.status_code == 400

    def test_activate_user(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Activator")
        patient = _make_user(db_session, role="patient", full_name="Patient ToAct",
                             is_active=False)
        resp = test_client.post(
            f"/api/v1/admin/users/{patient.id}/activate",
            json={"reason": "Test reactivation"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        db_session.refresh(patient)
        assert patient.is_active is True

    def test_cannot_activate_other_staff(self, test_client, db_session):
        staff1 = _make_user(db_session, role="staff", full_name="Staff ActivateBlock1")
        staff2 = _make_user(db_session, role="staff", full_name="Staff ActivateBlock2",
                            is_active=False)
        resp = test_client.post(
            f"/api/v1/admin/users/{staff2.id}/activate",
            json={"reason": "Staff activation test"},
            headers=_headers(staff1),
        )
        assert resp.status_code == 400


# ══════════════════════════════���═══════════════════════════════════
# Data Masking & No Health Data
# ════════════════════════���═════════════════════════════════════════

class TestAdminAtomicAudit:

    def test_verify_and_audit_are_atomic(self, test_client, db_session):
        """Verify that doctor status change and audit log are committed together."""
        staff = _make_user(db_session, role="staff", full_name="Staff Atomic")
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr Atomic", medical_license="LIC-ATOMIC")

        # Count audit entries before
        before_count = db_session.query(AdminAuditLog).count()

        resp = test_client.post(
            f"/api/v1/admin/users/{doctor.id}/verify",
            json={"action": "verify", "reason": "Atomic test"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200

        # Both state and audit should be committed
        db_session.refresh(doctor)
        assert doctor.verification_status == "verified"
        after_count = db_session.query(AdminAuditLog).count()
        assert after_count == before_count + 1

    def test_deactivate_and_audit_are_atomic(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff AtomicDeact")
        patient = _make_user(db_session, role="patient", full_name="Patient AtomicDeact")

        before_count = db_session.query(AdminAuditLog).count()

        resp = test_client.post(
            f"/api/v1/admin/users/{patient.id}/deactivate",
            json={"reason": "Atomic deactivation test"},
            headers=_headers(staff),
        )
        assert resp.status_code == 200

        db_session.refresh(patient)
        assert patient.is_active is False
        after_count = db_session.query(AdminAuditLog).count()
        assert after_count == before_count + 1


class TestAdminDataMasking:

    def test_response_has_masked_data(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Masker")
        _make_user(db_session, role="patient", full_name="John Smith",
                   email="john@example.com", phone_number="0812345678")
        resp = test_client.get("/api/v1/admin/users", headers=_headers(staff))
        assert resp.status_code == 200
        users = resp.json()["data"]["users"]
        assert len(users) > 0
        # Check that response uses masked fields
        for u in users:
            assert "full_name_masked" in u
            assert "email_masked" in u or u.get("email_masked") is None

    def test_response_no_health_data(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff HealthCheck")
        patient = _make_user(db_session, role="patient", full_name="Patient Health")
        resp = test_client.get(f"/api/v1/admin/users/{patient.id}", headers=_headers(staff))
        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        # Must NOT contain health data fields
        for forbidden_field in ["citizen_id", "date_of_birth", "blood_type", "height", "weight", "gender", "telegram_id"]:
            assert forbidden_field not in user_data, f"Response contains forbidden field: {forbidden_field}"


# ═══════════════════════���══════════════════════════════════════════
# Filtering & Pagination
# ══��══════════════════���════════════════════════════��═══════════════

class TestAdminFiltering:

    def test_filter_by_role(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Filter")
        _make_user(db_session, role="doctor", full_name="Dr Filterable",
                   verification_status="verified")
        resp = test_client.get("/api/v1/admin/users?role=doctor", headers=_headers(staff))
        assert resp.status_code == 200
        users = resp.json()["data"]["users"]
        for u in users:
            assert u["role"] == "doctor"

    def test_filter_by_verification_status(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff StatusFilter")
        resp = test_client.get(
            "/api/v1/admin/users?verification_status=pending",
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        users = resp.json()["data"]["users"]
        for u in users:
            assert u["verification_status"] == "pending"

    def test_pagination_works(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Paginator")
        resp = test_client.get("/api/v1/admin/users?page=1&per_page=5", headers=_headers(staff))
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert "current_page" in meta
        assert "total_pages" in meta
        assert meta["current_page"] == 1


# ══���═════════════════════��═════════════════════════════════════════
# Audit Log Endpoint
# ══════════════════════════════════════════════════════════════════

class TestAdminAuditLog:

    def test_audit_log_returns_entries(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff AuditView")
        resp = test_client.get("/api/v1/admin/audit-log", headers=_headers(staff))
        assert resp.status_code == 200
        assert "entries" in resp.json()["data"]


# ════════════════════════��═════════════════════════════════════════
# User Detail & Payments
# ════════════════════════════════════════════════════���═════════════

class TestAdminUserDetail:

    def test_user_detail_includes_verification_logs_for_doctor(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Detail")
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr Detail", medical_license="LIC-DETAIL")
        # Verify the doctor first to create verification logs
        test_client.post(
            f"/api/v1/admin/users/{doctor.id}/verify",
            json={"action": "verify", "reason": "OK"},
            headers=_headers(staff),
        )
        resp = test_client.get(f"/api/v1/admin/users/{doctor.id}", headers=_headers(staff))
        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert "verification_logs" in user_data
        assert user_data["verification_logs"] is not None

    def test_user_payments_endpoint(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", full_name="Staff Payments")
        patient = _make_user(db_session, role="patient", full_name="Patient Payments")
        resp = test_client.get(
            f"/api/v1/admin/users/{patient.id}/payments",
            headers=_headers(staff),
        )
        assert resp.status_code == 200
        assert "payments" in resp.json()["data"]
