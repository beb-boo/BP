"""Tests for doctor verification guard — Phase 1 of Membership Admin & Doctor Hardening."""

import pytest
from app.models import User, DoctorPatient
from app.utils.security import hash_password, create_access_token
from app.utils.timezone import now_tz


# ── Helpers ──────────────────────────────────────────────────────

def _make_user(db, role="patient", verification_status="pending", **kwargs):
    user = User(
        role=role,
        verification_status=verification_status,
        is_active=True,
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
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user):
    token = create_access_token({"user_id": user.id})
    return {"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"}


def _link_doctor_patient(db, doctor, patient):
    dp = DoctorPatient(doctor_id=doctor.id, patient_id=patient.id, is_active=True)
    db.add(dp)
    db.commit()


# ══════════════════════════════════════════════════════════════════
# Doctor Endpoint Guards
# ══════��═══════════���═══════════════════════════════════════════════

class TestDoctorVerificationGuard:

    def test_verified_doctor_can_request_access(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="verified")
        patient = _make_user(db_session, role="patient", verification_status="verified",
                             full_name="Patient A")
        resp = test_client.post(
            "/api/v1/doctor/request-access",
            json={"patient_id": patient.id},
            headers=_headers(doctor),
        )
        assert resp.status_code == 200 or resp.status_code == 201, resp.text

    def test_pending_doctor_cannot_request_access(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="pending")
        resp = test_client.post(
            "/api/v1/doctor/request-access",
            json={"patient_id": 9999},
            headers=_headers(doctor),
        )
        assert resp.status_code == 403

    def test_rejected_doctor_cannot_view_patients(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="rejected")
        resp = test_client.get(
            "/api/v1/doctor/patients",
            headers=_headers(doctor),
        )
        assert resp.status_code == 403

    def test_pending_doctor_cannot_view_access_requests(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="pending")
        resp = test_client.get(
            "/api/v1/doctor/access-requests",
            headers=_headers(doctor),
        )
        assert resp.status_code == 403

    def test_patient_cannot_authorize_pending_doctor(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="pending")
        patient = _make_user(db_session, role="patient", verification_status="verified",
                             full_name="Patient B")
        resp = test_client.post(
            "/api/v1/patient/authorize-doctor",
            json={"doctor_id": doctor.id},
            headers=_headers(patient),
        )
        assert resp.status_code == 400
        assert "verified" in resp.json().get("detail", "").lower()

    def test_patient_can_authorize_verified_doctor(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="verified",
                            full_name="Dr Verified")
        patient = _make_user(db_session, role="patient", verification_status="verified",
                             full_name="Patient C")
        resp = test_client.post(
            "/api/v1/patient/authorize-doctor",
            json={"doctor_id": doctor.id},
            headers=_headers(patient),
        )
        assert resp.status_code == 200, resp.text

    def test_patient_blocked_from_doctor_endpoints(self, test_client, db_session):
        patient = _make_user(db_session, role="patient", verification_status="verified",
                             full_name="Patient D")
        for endpoint in ["/api/v1/doctor/patients", "/api/v1/doctor/access-requests"]:
            resp = test_client.get(endpoint, headers=_headers(patient))
            assert resp.status_code == 403, f"{endpoint} should block patient"

    def test_staff_blocked_from_doctor_endpoints(self, test_client, db_session):
        staff = _make_user(db_session, role="staff", verification_status="verified",
                           full_name="Staff A")
        resp = test_client.get(
            "/api/v1/doctor/patients",
            headers=_headers(staff),
        )
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
# Profile / Login Contract
# ═════════════════════════���════════════════════════════════════════

class TestVerificationStatusContract:

    def test_profile_includes_verification_status(self, test_client, db_session):
        doctor = _make_user(db_session, role="doctor", verification_status="pending",
                            full_name="Dr Profile")
        resp = test_client.get("/api/v1/users/me", headers=_headers(doctor))
        assert resp.status_code == 200
        profile = resp.json()["data"]["profile"]
        assert "verification_status" in profile
        assert profile["verification_status"] == "pending"

    def test_login_includes_verification_status(self, test_client, db_session):
        """Login response must include verification_status field.

        We use the email login path to avoid phonenumbers mock issues.
        """
        from app.utils.encryption import hash_value
        doctor = _make_user(db_session, role="doctor", verification_status="verified",
                            full_name="Dr Login", email="drlogin@test.com")
        resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": "drlogin@test.com", "password": "testpass123"},
            headers={"X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 200, resp.text
        user_data = resp.json()["data"]["user"]
        assert "verification_status" in user_data
        assert user_data["verification_status"] == "verified"
