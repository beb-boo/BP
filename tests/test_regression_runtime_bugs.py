"""Regression tests for confirmed runtime bugs."""

import importlib
import io
from datetime import timedelta

from app.bot.services import BotService
from app.models import User
from app.utils.security import MAX_LOGIN_ATTEMPTS, hash_password
from app.utils.timezone import now_tz


class TestBotPasswordVerificationParity:
    def _create_user(self, db_session, phone_number: str, password: str, **kwargs) -> User:
        user = User(
            full_name="Regression User",
            password_hash=hash_password(password),
            role="patient",
            is_active=kwargs.pop("is_active", True),
            failed_login_attempts=kwargs.pop("failed_login_attempts", 0),
            account_locked_until=kwargs.pop("account_locked_until", None),
        )
        user.phone_number = phone_number
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_verify_user_password_accepts_valid_active_account(self, db_session):
        self._create_user(db_session, "66810000001", "validpass123")

        result = BotService.verify_user_password("66810000001", "validpass123")

        assert result.status == "success"
        assert result.user is not None
        assert result.user.phone_number == "66810000001"

    def test_verify_user_password_rejects_locked_account(self, db_session):
        self._create_user(
            db_session,
            "66810000002",
            "validpass123",
            account_locked_until=now_tz() + timedelta(minutes=5),
        )

        result = BotService.verify_user_password("66810000002", "validpass123")

        assert result.status == "locked"
        assert result.user is None

    def test_verify_user_password_rejects_inactive_account(self, db_session):
        self._create_user(db_session, "66810000003", "validpass123", is_active=False)

        result = BotService.verify_user_password("66810000003", "validpass123")

        assert result.status == "inactive"
        assert result.user is None

    def test_verify_user_password_locks_after_max_attempts(self, db_session):
        user = self._create_user(
            db_session,
            "66810000004",
            "validpass123",
            failed_login_attempts=MAX_LOGIN_ATTEMPTS - 1,
        )

        result = BotService.verify_user_password("66810000004", "wrongpass")

        assert result.status == "locked"
        db_session.refresh(user)
        assert user.account_locked_until is not None


class TestFrontendDateSerializationRegression:
    def test_date_utils_has_local_payload_builder(self):
        with open("frontend/lib/date-utils.ts") as file_obj:
            content = file_obj.read()

        assert "buildLocalDateTimePayload" in content
        assert 'toISOString().split("T")[0]' not in content

    def test_dashboard_uses_local_payload_builder(self):
        with open("frontend/app/(dashboard)/dashboard/page.tsx") as file_obj:
            content = file_obj.read()

        assert "buildLocalDateTimePayload" in content
        assert "measurement_date: specificDate.toISOString()" not in content

    def test_telegram_page_uses_local_payload_builder(self):
        with open("frontend/app/telegram/bp/page.tsx") as file_obj:
            content = file_obj.read()

        assert "buildLocalDateTimePayload" in content
        assert "measurement_date: date.toISOString()" not in content


class TestOCRAndWebhookRegression:
    def test_ocr_rejects_large_files_with_413(self, test_client):
        payload = io.BytesIO(b"a" * (10 * 1024 * 1024 + 1))

        response = test_client.post(
            "/api/v1/ocr/process-image",
            files={"file": ("too-large.jpg", payload, "image/jpeg")},
        )

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_webhook_default_path_is_stable(self, monkeypatch):
        monkeypatch.delenv("WEBHOOK_PATH", raising=False)
        monkeypatch.setenv("WEBHOOK_SECRET", "stable-secret")

        module = importlib.import_module("app.bot.webhook")
        module = importlib.reload(module)
        first_path = module._build_default_webhook_path()

        module = importlib.reload(module)
        second_path = module._build_default_webhook_path()

        assert first_path == second_path
        assert module._webhook_path == first_path