"""Phase 1: Bug Fix verification tests."""

import ast
import os
import pytest


class TestRequirementsTxt:
    """1.1 - Verify requirements.txt has all needed dependencies."""

    def test_pyotp_in_requirements(self):
        with open("app/requirements.txt") as f:
            content = f.read()
        assert "pyotp" in content

    def test_pytz_in_requirements(self):
        with open("app/requirements.txt") as f:
            content = f.read()
        assert "pytz" in content

    def test_bcrypt_in_requirements(self):
        with open("app/requirements.txt") as f:
            content = f.read()
        assert "bcrypt" in content

    def test_redis_in_requirements(self):
        with open("app/requirements.txt") as f:
            content = f.read()
        assert "redis" in content


class TestBackgroundTasksImports:
    """1.2 - Verify background_tasks.py has proper imports."""

    def test_has_imports(self):
        with open("app/utils/background_tasks.py") as f:
            content = f.read()
        assert "import logging" in content
        assert "from sqlalchemy.orm import Session" in content
        assert "from ..models import User" in content
        assert "from ..utils.tmc_checker import verify_doctor_with_tmc" in content

    def test_no_undefined_now_th(self):
        """now_th should not be used since we import now_tz."""
        with open("app/utils/background_tasks.py") as f:
            content = f.read()
        assert "now_th()" not in content
        assert "now_tz()" in content


class TestBotServicesHashLookup:
    """1.3 - Verify bot services use hash lookup instead of property filter."""

    def test_get_user_by_phone_uses_hash(self):
        with open("app/bot/services.py") as f:
            content = f.read()
        # Should use hash_value and phone_number_hash
        assert "hash_value(phone_number)" in content
        assert "phone_number_hash" in content
        # Should NOT use User.phone_number == phone_number (property filter)
        assert "User.phone_number ==" not in content

    def test_verify_user_password_uses_hash(self):
        with open("app/bot/services.py") as f:
            content = f.read()
        # The verify_user_password method should also use hash
        # Count occurrences of phone_number_hash - should be at least 2 (one per method)
        assert content.count("phone_number_hash") >= 2


class TestChangePasswordPayload:
    """1.4 - Frontend sends confirm_new_password."""

    def test_confirm_new_password_in_payload(self):
        with open("frontend/app/(dashboard)/settings/page.tsx") as f:
            content = f.read()
        assert "confirm_new_password: confirmPassword" in content


class TestDuplicateOcrHandler:
    """1.5 - Only one get_ocr_handler definition."""

    def test_single_get_ocr_handler(self):
        with open("app/bot/handlers.py") as f:
            content = f.read()
        count = content.count("def get_ocr_handler()")
        assert count == 1, f"Expected 1 get_ocr_handler, found {count}"

    def test_ocr_handler_supports_document_image(self):
        with open("app/bot/handlers.py") as f:
            content = f.read()
        assert "filters.Document.IMAGE" in content


class TestOTPBypassEnv:
    """1.6 - OTP bypass controlled by ENV variable."""

    def test_bypass_otp_env_check(self):
        with open("app/routers/auth.py") as f:
            content = f.read()
        assert 'BYPASS_OTP' in content
        assert 'os.getenv("BYPASS_OTP"' in content
        # The old bypass comment should be gone
        assert "# bypass for demo" not in content

    def test_otp_check_is_active(self):
        with open("app/routers/auth.py") as f:
            content = f.read()
        assert "otp_service.is_verified(contact_target)" in content


class TestLocalesDuplicateKey:
    """1.7 - No duplicate tz_select keys."""

    def test_no_duplicate_tz_select_en(self):
        with open("app/bot/locales.py") as f:
            lines = f.readlines()
        tz_select_count = sum(1 for line in lines if '"tz_select"' in line)
        # Should be exactly 2 (one EN, one TH)
        assert tz_select_count == 2, f"Expected 2 tz_select entries (EN+TH), found {tz_select_count}"


class TestDoctorCancelRequestVariable:
    """1.8 - cancel_access_request uses req_uuid instead of overriding request_id."""

    def test_no_request_id_override(self):
        with open("app/routers/doctor.py") as f:
            content = f.read()
        # Find the cancel_access_request function
        func_start = content.find("async def cancel_access_request")
        assert func_start != -1
        func_body = content[func_start:content.find("\n@router", func_start + 1)]

        # Should use req_uuid, not reassign request_id
        assert "req_uuid = generate_request_id()" in func_body
        assert "request_id = generate_request_id()" not in func_body


class TestDuplicatePulseValues:
    """1.9 - No duplicate pulse_values in bp_records.py."""

    def test_single_pulse_values_declaration(self):
        with open("app/routers/bp_records.py") as f:
            content = f.read()
        # Find the stats function area
        stats_start = content.find("def get_bp_stats")
        stats_body = content[stats_start:]
        count = stats_body.count("pulse_values = [r.pulse for r in records]")
        assert count == 1, f"Expected 1 pulse_values line, found {count}"
