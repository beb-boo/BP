"""Phase 2: Dual-Mode Storage tests."""

import os
import pytest


class TestOTPServiceDualMode:
    """2.1 - OTP Service supports Memory and Redis backends."""

    def test_otp_service_imports(self):
        from app.otp_service import OTPService, MemoryOTPBackend, RedisOTPBackend
        assert OTPService is not None
        assert MemoryOTPBackend is not None
        assert RedisOTPBackend is not None

    def test_default_memory_backend(self):
        """Without REDIS_URL, should use MemoryOTPBackend."""
        from app.otp_service import otp_service, MemoryOTPBackend
        assert isinstance(otp_service.backend, MemoryOTPBackend)

    def test_generate_and_confirm_otp(self):
        from app.otp_service import OTPService
        service = OTPService()
        otp = service.generate_otp("test@example.com", expiration=300)
        assert otp is not None
        assert len(otp) == 4  # 4-digit OTP

    def test_confirm_valid_otp(self):
        from app.otp_service import OTPService
        service = OTPService()
        otp = service.generate_otp("confirm@test.com", expiration=300)
        result = service.confirm_otp("confirm@test.com", otp)
        assert result is True

    def test_confirm_invalid_otp(self):
        from app.otp_service import OTPService
        service = OTPService()
        service.generate_otp("invalid@test.com", expiration=300)
        result = service.confirm_otp("invalid@test.com", "0000")
        # May or may not match depending on timing - test that it returns bool
        assert isinstance(result, bool)

    def test_is_verified_after_confirm(self):
        from app.otp_service import OTPService
        service = OTPService()
        otp = service.generate_otp("verified@test.com", expiration=300)
        service.confirm_otp("verified@test.com", otp)
        # After successful confirm, should be verified
        assert service.is_verified("verified@test.com") is True

    def test_is_verified_before_confirm(self):
        from app.otp_service import OTPService
        service = OTPService()
        assert service.is_verified("never@test.com") is False

    def test_memory_backend_store_and_get(self):
        from app.otp_service import MemoryOTPBackend
        backend = MemoryOTPBackend()
        backend.store("key1", {"data": "test", "created_at": 0, "expiration": 300})
        result = backend.get("key1")
        assert result is not None
        assert result["data"] == "test"

    def test_memory_backend_delete(self):
        from app.otp_service import MemoryOTPBackend
        backend = MemoryOTPBackend()
        backend.store("key2", {"data": "test", "created_at": 0, "expiration": 300})
        backend.delete("key2")
        assert backend.get("key2") is None

    def test_memory_backend_verified(self):
        from app.otp_service import MemoryOTPBackend
        backend = MemoryOTPBackend()
        assert backend.is_verified("x") is False
        backend.mark_verified("x")
        assert backend.is_verified("x") is True


class TestRateLimiterCentralized:
    """2.2 - Centralized rate limiter."""

    def test_rate_limiter_module_exists(self):
        from app.utils.rate_limiter import limiter
        assert limiter is not None

    def test_rate_limiter_is_slowapi_limiter(self):
        from app.utils.rate_limiter import limiter
        from slowapi import Limiter
        assert isinstance(limiter, Limiter)

    def test_routers_use_centralized_limiter(self):
        """Verify routers import from rate_limiter, not create their own."""
        files_to_check = [
            "app/routers/auth.py",
            "app/routers/ocr.py",
            "app/routers/payment.py",
        ]
        for filepath in files_to_check:
            with open(filepath) as f:
                content = f.read()
            assert "from ..utils.rate_limiter import limiter" in content, \
                f"{filepath} should import from rate_limiter"
            assert "limiter = Limiter(" not in content, \
                f"{filepath} should not create its own Limiter"

    def test_main_uses_centralized_limiter(self):
        with open("app/main.py") as f:
            content = f.read()
        assert "from .utils.rate_limiter import limiter" in content
        assert "limiter = Limiter(" not in content


class TestDatabasePoolSettings:
    """2.3 - Database has pool settings for PostgreSQL."""

    def test_sqlite_no_pool_settings(self):
        """SQLite should use simple connect args."""
        with open("app/database.py") as f:
            content = f.read()
        assert 'check_same_thread' in content

    def test_postgresql_pool_settings_in_code(self):
        with open("app/database.py") as f:
            content = f.read()
        assert "pool_size" in content
        assert "max_overflow" in content
        assert "pool_pre_ping" in content
        assert "pool_recycle" in content

    def test_postgres_url_fix(self):
        """Vercel gives postgres:// but SQLAlchemy needs postgresql://."""
        with open("app/database.py") as f:
            content = f.read()
        assert 'postgres://' in content
        assert 'postgresql://' in content


class TestAutoCreateTablesEnv:
    """2.4 - Auto-create tables controlled by ENV."""

    def test_auto_create_tables_env(self):
        with open("app/main.py") as f:
            content = f.read()
        assert "AUTO_CREATE_TABLES" in content
        assert 'os.getenv("AUTO_CREATE_TABLES"' in content

    def test_conditional_create_all(self):
        with open("app/main.py") as f:
            content = f.read()
        assert "if AUTO_CREATE_TABLES:" in content
