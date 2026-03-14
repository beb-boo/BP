"""Phase 4: Frontend Improvement tests."""

import os
import pytest


class TestDoctorViewRealData:
    """4.1 - DoctorView fetches real data from API."""

    def test_doctor_view_fetches_patients(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert 'api.get("/doctor/patients")' in content

    def test_doctor_view_fetches_access_requests(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert 'api.get("/doctor/access-requests")' in content

    def test_no_hardcoded_patient_count(self):
        """DoctorView should not have hardcoded numbers."""
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        # Find DoctorView function
        dv_start = content.find("function DoctorView")
        dv_content = content[dv_start:]
        # Should use dynamic count, not "12" or "3"
        assert '{patients.length}' in dv_content
        assert '{pendingRequests.length}' in dv_content

    def test_doctor_view_no_demo_text(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        dv_start = content.find("function DoctorView")
        dv_content = content[dv_start:]
        assert "(Demo)" not in dv_content


class TestManageDoctorsDialog:
    """4.2 - Patient can manage authorized doctors."""

    def test_manage_doctors_dialog_exists(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert "function ManageDoctorsDialog" in content

    def test_fetches_authorized_doctors(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert 'api.get("/patient/authorized-doctors")' in content

    def test_fetches_patient_access_requests(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert 'api.get("/patient/access-requests")' in content

    def test_approve_reject_buttons(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert "handleApprove" in content
        assert "handleReject" in content

    def test_remove_doctor_button(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert "handleRemoveDoctor" in content

    def test_authorize_doctor(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert 'api.post("/patient/authorize-doctor"' in content

    def test_no_coming_soon(self):
        """Manage Doctors button should not show 'coming soon'."""
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as f:
            content = f.read()
        assert "coming_soon" not in content


class TestAuthMiddleware:
    """4.3 - Next.js middleware for auth guard."""

    def test_middleware_file_exists(self):
        assert os.path.exists("frontend/middleware.ts")

    def test_protects_dashboard(self):
        with open("frontend/middleware.ts") as f:
            content = f.read()
        assert "/dashboard" in content

    def test_protects_settings(self):
        with open("frontend/middleware.ts") as f:
            content = f.read()
        assert "/settings" in content

    def test_redirects_to_login(self):
        with open("frontend/middleware.ts") as f:
            content = f.read()
        assert "/auth/login" in content

    def test_redirects_logged_in_from_auth(self):
        with open("frontend/middleware.ts") as f:
            content = f.read()
        # Should redirect authenticated users away from auth pages
        assert "authRoutes" in content


class TestAPIKeyEnv:
    """4.4 - API Key uses ENV variable."""

    def test_api_key_from_env(self):
        with open("frontend/lib/api.ts") as f:
            content = f.read()
        assert "NEXT_PUBLIC_API_KEY" in content
        assert "process.env.NEXT_PUBLIC_API_KEY" in content


class TestResendOTP:
    """4.5 - Resend OTP implementation."""

    def test_resend_calls_api(self):
        with open("frontend/app/auth/verify-otp/page.tsx") as f:
            content = f.read()
        assert 'api.post("/auth/request-otp"' in content

    def test_resend_has_cooldown(self):
        with open("frontend/app/auth/verify-otp/page.tsx") as f:
            content = f.read()
        assert "resendTimer" in content

    def test_no_coming_soon_in_resend(self):
        with open("frontend/app/auth/verify-otp/page.tsx") as f:
            content = f.read()
        assert "coming soon" not in content


class TestCustomErrorPages:
    """4.6 - Custom error and 404 pages."""

    def test_error_page_exists(self):
        assert os.path.exists("frontend/app/error.tsx")

    def test_not_found_page_exists(self):
        assert os.path.exists("frontend/app/not-found.tsx")

    def test_error_page_has_reset(self):
        with open("frontend/app/error.tsx") as f:
            content = f.read()
        assert "reset()" in content

    def test_not_found_has_links(self):
        with open("frontend/app/not-found.tsx") as f:
            content = f.read()
        assert "/dashboard" in content
        assert "404" in content


class TestNextConfig:
    """4.7 - next.config.ts has standalone output."""

    def test_standalone_output(self):
        with open("frontend/next.config.ts") as f:
            content = f.read()
        assert "'standalone'" in content
