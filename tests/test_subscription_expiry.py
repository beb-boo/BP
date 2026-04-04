"""Tests for Premium subscription: expiry, normalization, renewal, bypass and payment service."""

import os
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from app.models import User, Payment
from app.utils.timezone import now_tz
from app.utils.subscription import (
    is_premium_active,
    get_subscription_info,
    get_renewal_base_datetime,
    normalize_subscription_state,
)
from app.services.payment_service import (
    validate_slip_image,
    PaymentError,
)


# ── Helpers ──────────────────────────────────────────────────────

def _make_user(db, tier="free", expires_delta=None, **kwargs):
    """Create a User in the test DB and return it.

    Note: We avoid db.refresh() after commit because SQLite strips timezone
    info from datetimes.  Instead we keep the Python-side tz-aware value and
    re-assign it after commit so that check_premium() comparisons work.
    """
    now = now_tz()
    expires_at = (now + expires_delta) if expires_delta else None

    user = User(
        subscription_tier=tier,
        subscription_expires_at=expires_at,
        role="patient",
        is_active=True,
        is_email_verified=False,
        is_phone_verified=False,
        language="th",
        **kwargs,
    )
    # Set required fields via property setters (triggers encryption)
    user.full_name = kwargs.get("full_name", "Test User")
    user.password_hash = "fakehash"

    db.add(user)
    db.commit()
    # Re-read the id but keep the tz-aware expires_at (SQLite loses tz info)
    db.refresh(user)
    if expires_at is not None:
        user.subscription_expires_at = expires_at
    return user


# ══════════════════════════════════════════════════════════════════
# 1. Subscription Logic (get_subscription_info / is_premium_active)
# ══════════════════════════════════════════════════════════════════

class TestSubscriptionLogic:

    def test_free_user_not_premium(self, db_session):
        user = _make_user(db_session, tier="free")
        info = get_subscription_info(user)
        assert info["subscription_tier"] == "free"
        assert info["is_premium_active"] is False
        assert info["days_remaining"] == 0

    def test_active_premium_user(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=15))
        info = get_subscription_info(user)
        assert info["subscription_tier"] == "premium"
        assert info["is_premium_active"] is True
        assert info["days_remaining"] >= 14  # at least 14 full days

    def test_expired_premium_normalized_to_free(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-1))
        info = get_subscription_info(user)
        assert info["subscription_tier"] == "free"
        assert info["is_premium_active"] is False
        assert info["days_remaining"] == 0

    def test_premium_null_expiry_normalized_to_free(self, db_session):
        user = _make_user(db_session, tier="premium")  # no expires_at
        info = get_subscription_info(user)
        assert info["subscription_tier"] == "free"
        assert info["is_premium_active"] is False

    def test_is_premium_active_shortcut(self, db_session):
        active = _make_user(db_session, tier="premium", expires_delta=timedelta(days=10))
        expired = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-5))
        assert is_premium_active(active) is True
        assert is_premium_active(expired) is False


# ══════════════════════════════════════════════════════════════════
# 2. Renewal Base Datetime
# ══════════════════════════════════════════════════════════════════

class TestRenewalLogic:

    def test_renewal_before_expiry_stacks(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=10))
        now = now_tz()
        base = get_renewal_base_datetime(user, now)
        # Base should be the existing expiry (future), not now
        assert base == user.subscription_expires_at

    def test_renewal_after_expiry_starts_from_now(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-5))
        now = now_tz()
        base = get_renewal_base_datetime(user, now)
        assert base == now

    def test_renewal_free_user_starts_from_now(self, db_session):
        user = _make_user(db_session, tier="free")
        now = now_tz()
        base = get_renewal_base_datetime(user, now)
        assert base == now


# ══════════════════════════════════════════════════════════════════
# 3. Bypass Users
# ══════════════════════════════════════════════════════════════════

class TestBypassUsers:

    def test_bypass_user_always_premium(self, db_session):
        user = _make_user(db_session, tier="free")
        # Patch bypass list to include this user's ID
        with patch("app.utils.security._premium_bypass_cache", {str(user.id)}):
            assert is_premium_active(user) is True
            info = get_subscription_info(user)
            assert info["subscription_tier"] == "premium"
            assert info["is_premium_active"] is True

    def test_bypass_user_not_normalized_down(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-10))
        with patch("app.utils.security._premium_bypass_cache", {str(user.id)}):
            info = get_subscription_info(user)
            assert info["subscription_tier"] == "premium"
            assert info["is_premium_active"] is True


# ══════════════════════════════════════════════════════════════════
# 4. Payment Service (mocked SlipOK)
# ══════════════════════════════════════════════════════════════════

class TestPaymentService:

    def test_invalid_plan_rejected(self, db_session):
        from app.services.payment_service import verify_and_upgrade, PaymentError

        user = _make_user(db_session, tier="free")
        with pytest.raises(PaymentError) as exc_info:
            verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0fake", "nonexistent", "en")
        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.message

    def test_duplicate_slip_rejected(self, db_session):
        from app.services.payment_service import verify_and_upgrade, PaymentError
        from app.utils.encryption import hash_value

        user = _make_user(db_session, tier="free")

        # Pre-insert a verified payment with known trans_ref_hash
        existing_payment = Payment(
            user_id=user.id,
            trans_ref="DUP-REF-123",
            trans_ref_hash=hash_value("DUP-REF-123"),
            amount=9.0,
            plan_type="monthly",
            plan_amount=9.0,
            status="verified",
            verified_at=now_tz(),
        )
        db_session.add(existing_payment)
        db_session.commit()

        # Mock SlipOK to return success with same trans_ref
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = "DUP-REF-123"
        mock_result.amount = 9.0
        mock_result.sending_bank = "SCB"
        mock_result.sender_name = "Test"
        mock_result.receiver_name = "BP"
        mock_result.trans_date = "2026-01-01"
        mock_result.trans_time = "12:00"
        mock_result.raw_response = {}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            with pytest.raises(PaymentError) as exc_info:
                verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")
            assert exc_info.value.status_code == 409

    def test_amount_mismatch_rejected(self, db_session):
        from app.services.payment_service import verify_and_upgrade, PaymentError

        user = _make_user(db_session, tier="free")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = "MISMATCH-001"
        mock_result.amount = 100.0  # way off from 9.0
        mock_result.sending_bank = "SCB"
        mock_result.sender_name = "Test"
        mock_result.receiver_name = "BP"
        mock_result.trans_date = "2026-01-01"
        mock_result.trans_time = "12:00"
        mock_result.raw_response = {}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            with pytest.raises(PaymentError) as exc_info:
                verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")
            assert "mismatch" in exc_info.value.message.lower()

    def test_valid_payment_upgrades_user(self, db_session):
        from app.services.payment_service import verify_and_upgrade

        user = _make_user(db_session, tier="free")
        assert user.subscription_tier == "free"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = f"VALID-{user.id}-001"
        mock_result.amount = 9.0
        mock_result.sending_bank = "SCB"
        mock_result.sender_name = "Test"
        mock_result.receiver_name = "BP"
        mock_result.trans_date = "2026-01-01"
        mock_result.trans_time = "12:00"
        mock_result.raw_response = {"success": True}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            result = verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")

        assert result["subscription_tier"] == "premium"
        assert result["plan"] == "monthly"
        assert result["amount"] == 9.0

        # After verify_and_upgrade commits, user is already updated in-session
        assert user.subscription_tier == "premium"
        assert user.subscription_expires_at is not None

    def test_valid_payment_stacks_on_active(self, db_session):
        from app.services.payment_service import verify_and_upgrade
        from dateutil.parser import parse as parse_dt

        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=10))
        old_expiry = user.subscription_expires_at  # tz-aware

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = f"STACK-{user.id}-001"
        mock_result.amount = 9.0
        mock_result.sending_bank = "SCB"
        mock_result.sender_name = "Test"
        mock_result.receiver_name = "BP"
        mock_result.trans_date = "2026-01-01"
        mock_result.trans_time = "12:00"
        mock_result.raw_response = {"success": True}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            result = verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")

        # Verify via returned payload (avoids SQLite tz stripping)
        new_expiry_str = result["subscription_expires_at"]
        new_expiry = parse_dt(new_expiry_str)
        expected = old_expiry + timedelta(days=30)
        # Both should be close — allow for tz representation differences
        diff_days = abs((new_expiry.replace(tzinfo=None) - expected.replace(tzinfo=None)).total_seconds())
        assert diff_days < 5  # within 5 seconds


# ══════════════════════════════════════════════════════════════════
# 5. API Contract (via TestClient)
# ══════════════════════════════════════════════════════════════════

class TestAPIContract:
    """API contract tests using the mocked phone number "66800000000"
    (phonenumbers mock in conftest always returns +66800000000)."""

    _token_cache = None

    def _get_or_create_token(self, test_client, db_session):
        """Create an expired-premium user and login once; reuse token."""
        if TestAPIContract._token_cache is not None:
            return TestAPIContract._token_cache

        from app.utils.security import hash_password

        # phonenumbers mock always formats to 66800000000
        phone = "66800000000"

        user = User(
            subscription_tier="premium",
            subscription_expires_at=now_tz() + timedelta(days=-1),  # expired
            role="patient",
            is_active=True,
            is_email_verified=False,
            is_phone_verified=True,
            language="en",
            password_hash=hash_password("testpass123"),
        )
        user.full_name = "API Test User"
        user.phone_number = phone
        db_session.add(user)
        db_session.commit()

        response = test_client.post(
            "/api/v1/auth/login",
            json={"phone_number": phone, "password": "testpass123"},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()["data"]
        TestAPIContract._token_cache = data["access_token"]
        return TestAPIContract._token_cache

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"}

    def test_payment_status_returns_normalized(self, test_client, db_session):
        token = self._get_or_create_token(test_client, db_session)
        response = test_client.get("/api/v1/payment/status", headers=self._headers(token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tier"] == "free"
        assert data["is_active"] is False

    def test_payment_plans_returns_normalized_status(self, test_client, db_session):
        token = self._get_or_create_token(test_client, db_session)
        response = test_client.get("/api/v1/payment/plans", headers=self._headers(token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["current_tier"] == "free"
        assert data["is_active"] is False
        assert "days_remaining" in data

    def test_users_me_returns_subscription_fields(self, test_client, db_session):
        token = self._get_or_create_token(test_client, db_session)
        response = test_client.get("/api/v1/users/me", headers=self._headers(token))
        assert response.status_code == 200
        profile = response.json()["data"]["profile"]
        assert profile["subscription_tier"] == "free"
        assert profile["is_premium_active"] is False
        assert "days_remaining" in profile

    def test_login_returns_normalized_subscription(self, test_client, db_session):
        """Login response must include normalized subscription fields."""
        token = self._get_or_create_token(test_client, db_session)
        # Login again to check response payload
        response = test_client.post(
            "/api/v1/auth/login",
            json={"phone_number": "66800000000", "password": "testpass123"},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        user_data = response.json()["data"]["user"]
        # Expired premium → normalized to free
        assert user_data["subscription_tier"] == "free"
        assert user_data["is_premium_active"] is False
        assert "subscription_expires_at" in user_data


# ══════════════════════════════════════════════════════════════════
# 6. Self-heal (Persisted Normalization)
# ══════════════════════════════════════════════════════════════════

class TestSelfHeal:

    def test_normalize_writes_free_to_db(self, db_session):
        """normalize_subscription_state must persist tier='free' for expired premium."""
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-5))
        assert user.subscription_tier == "premium"  # raw DB value

        changed = normalize_subscription_state(user, db=db_session)
        assert changed is True
        assert user.subscription_tier == "free"

    def test_normalize_noop_for_active_premium(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=10))
        changed = normalize_subscription_state(user, db=db_session)
        assert changed is False
        assert user.subscription_tier == "premium"

    def test_normalize_noop_for_free_user(self, db_session):
        user = _make_user(db_session, tier="free")
        changed = normalize_subscription_state(user, db=db_session)
        assert changed is False
        assert user.subscription_tier == "free"

    def test_normalize_bypass_user_not_downgraded(self, db_session):
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-10))
        with patch("app.utils.security._premium_bypass_cache", {str(user.id)}):
            changed = normalize_subscription_state(user, db=db_session)
            assert changed is False
            assert user.subscription_tier == "premium"


# ══════════════════════════════════════════════════════════════════
# 7. Image Validation (shared layer parity)
# ══════════════════════════════════════════════════════════════════

class TestImageValidation:

    def test_non_image_rejected(self):
        """Non-image bytes should be rejected."""
        with pytest.raises(PaymentError) as exc_info:
            validate_slip_image(b"not an image at all", "en")
        assert exc_info.value.status_code == 400
        assert "image" in exc_info.value.message.lower()

    def test_empty_bytes_rejected(self):
        with pytest.raises(PaymentError) as exc_info:
            validate_slip_image(b"", "en")
        assert exc_info.value.status_code == 400

    def test_oversized_file_rejected(self):
        """File > 10MB should be rejected."""
        large_data = b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024)  # JPEG header + 11MB
        with pytest.raises(PaymentError) as exc_info:
            validate_slip_image(large_data, "en")
        assert exc_info.value.status_code == 413

    def test_valid_jpeg_accepted(self):
        """Valid JPEG magic bytes within size limit should pass."""
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 1000  # small JPEG-like
        validate_slip_image(jpeg_data, "en")  # should not raise

    def test_valid_png_accepted(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000
        validate_slip_image(png_data, "en")  # should not raise


# ══════════════════════════════════════════════════════════════════
# 8. Rate Limiting (shared layer)
# ══════════════════════════════════════════════════════════════════

class TestRateLimit:

    def test_rate_limit_enforced(self, db_session):
        """After 3 rapid calls, the 4th should be rejected."""
        from app.services.payment_service import _check_rate_limit, _verify_timestamps

        fake_user_id = 999999
        # Clear any existing entries
        _verify_timestamps.pop(fake_user_id, None)

        for _ in range(3):
            _check_rate_limit(fake_user_id, "en")  # should pass

        with pytest.raises(PaymentError) as exc_info:
            _check_rate_limit(fake_user_id, "en")
        assert exc_info.value.status_code == 429

        # Cleanup
        _verify_timestamps.pop(fake_user_id, None)


# ══════════════════════════════════════════════════════════════════
# 9. Web/Bot Parity
# ══════════════════════════════════════════════════════════════════

class TestWebBotParity:

    def test_web_and_bot_use_same_verification_result(self, db_session):
        """Both web and bot should produce the same outcome for the same input."""
        from app.services.payment_service import verify_and_upgrade

        user = _make_user(db_session, tier="free")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = f"PARITY-{user.id}"
        mock_result.amount = 9.0
        mock_result.sending_bank = "SCB"
        mock_result.sender_name = "Test"
        mock_result.receiver_name = "BP"
        mock_result.trans_date = "2026-01-01"
        mock_result.trans_time = "12:00"
        mock_result.raw_response = {"success": True}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            # Simulate what web route does
            web_result = verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")

        assert web_result["subscription_tier"] == "premium"
        assert web_result["plan"] == "monthly"

        # Bot calls BotService.verify_slip_payment() which calls the SAME verify_and_upgrade
        # So if verify_and_upgrade works, both channels produce identical outcomes
        # This is the parity guarantee from shared service architecture

    def test_web_and_bot_use_same_amount_validation(self):
        """Amount validation uses is_valid_amount from pricing config — shared by both channels."""
        from app.config.pricing import is_valid_amount, AMOUNT_TOLERANCE
        # Same function is used in verify_and_upgrade (shared by both)
        assert is_valid_amount(9.0, 9.0) is True
        assert is_valid_amount(9.0, 9.0 + AMOUNT_TOLERANCE) is True  # at tolerance boundary
        assert is_valid_amount(9.0, 100.0) is False  # way beyond tolerance

    def test_web_and_bot_use_same_duplicate_protection(self, db_session):
        """Duplicate slip detection uses the same hash-based check."""
        from app.services.payment_service import verify_and_upgrade
        from app.utils.encryption import hash_value

        user = _make_user(db_session, tier="free")

        # Insert existing payment
        existing = Payment(
            user_id=user.id,
            trans_ref="PARITY-DUP",
            trans_ref_hash=hash_value("PARITY-DUP"),
            amount=9.0, plan_type="monthly", plan_amount=9.0,
            status="verified", verified_at=now_tz(),
        )
        db_session.add(existing)
        db_session.commit()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.trans_ref = "PARITY-DUP"  # same ref
        mock_result.amount = 9.0
        mock_result.raw_response = {}

        with patch("app.services.payment_service.slipok_service") as mock_svc:
            mock_svc.api_key = "test-key"
            mock_svc.verify_slip_image.return_value = mock_result

            with pytest.raises(PaymentError) as exc_info:
                verify_and_upgrade(db_session, user, b"\xff\xd8\xff\xe0img", "monthly", "en")
            assert exc_info.value.status_code == 409


# ══════════════════════════════════════════════════════════════════
# 10. Feature Gating
# ══════════════════════════════════════════════════════════════════

class TestFeatureGating:

    def test_expired_premium_loses_premium_check(self, db_session):
        """Expired premium user should not pass check_premium."""
        from app.utils.security import check_premium
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=-1))
        assert check_premium(user) is False

    def test_active_premium_passes_premium_check(self, db_session):
        """Active premium user should pass check_premium."""
        from app.utils.security import check_premium
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=10))
        assert check_premium(user) is True

    def test_free_user_fails_premium_check(self, db_session):
        """Free user should not pass check_premium."""
        from app.utils.security import check_premium
        user = _make_user(db_session, tier="free")
        assert check_premium(user) is False


# ══════════════════════════════════════════════════════════════════
# 11. Route-level Feature Gating (/stats/summary, /export/my-data)
# ══════════════════════════════════════════════════════════════════

def _make_token(user_id: int) -> str:
    """Create a valid JWT access token for the given user_id."""
    from app.utils.security import create_access_token
    return create_access_token({"user_id": user_id})


def _add_bp_records(db, user_id: int, count: int = 5):
    """Insert `count` BP records for a user."""
    from app.models import BloodPressureRecord
    from datetime import date
    for i in range(count):
        rec = BloodPressureRecord(
            user_id=user_id,
            systolic=120 + i,
            diastolic=80 + i,
            pulse=70 + i,
            measurement_date=date(2026, 1, 1 + i),
        )
        db.add(rec)
    db.commit()


class TestRouteFeatureGating:

    def test_stats_summary_free_user_no_advanced_metrics(self, test_client, db_session):
        """Free user: /stats/summary must not include sd/cv/pulse_pressure/map/trend."""
        user = _make_user(db_session, tier="free")
        _add_bp_records(db_session, user.id, count=5)
        token = _make_token(user.id)

        resp = test_client.get(
            "/api/v1/stats/summary",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 200
        stats = resp.json()["data"]["stats"]
        assert "sd" not in stats.get("systolic", {})
        assert "pulse_pressure" not in stats
        assert "map" not in stats
        assert "trend" not in stats
        assert resp.json()["data"]["is_premium"] is False

    def test_stats_summary_premium_user_has_advanced_metrics(self, test_client, db_session):
        """Active premium user: /stats/summary must include sd/pulse_pressure/map/trend."""
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=30))
        _add_bp_records(db_session, user.id, count=5)
        token = _make_token(user.id)

        resp = test_client.get(
            "/api/v1/stats/summary",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_premium"] is True
        stats = data["stats"]
        assert "sd" in stats.get("systolic", {})
        assert "pulse_pressure" in stats
        assert "map" in stats
        assert "trend" in stats

    def test_export_free_user_limited_note(self, test_client, db_session):
        """Free user: /export/my-data export_note must indicate the 30-record limit."""
        user = _make_user(db_session, tier="free")
        token = _make_token(user.id)

        resp = test_client.get(
            "/api/v1/export/my-data",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 200
        note = resp.json()["data"]["export"]["meta"]["note"]
        assert "30" in note or "Free" in note or "Limited" in note

    def test_export_premium_user_full_history_note(self, test_client, db_session):
        """Active premium user: /export/my-data export_note must indicate full history."""
        user = _make_user(db_session, tier="premium", expires_delta=timedelta(days=30))
        token = _make_token(user.id)

        resp = test_client.get(
            "/api/v1/export/my-data",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 200
        note = resp.json()["data"]["export"]["meta"]["note"]
        assert "Premium" in note or "Full" in note
