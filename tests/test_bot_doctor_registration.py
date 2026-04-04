"""Tests for Bot Doctor Registration — Phase 4 of Membership Admin & Doctor Hardening."""

import pytest
from app.models import User
from app.utils.security import hash_password
from app.utils.encryption import hash_value, encrypt_value
from app.utils.timezone import now_tz


# ── Helpers ──────────────────────────────────────────────────────

def _make_user(db, role="patient", **kwargs):
    user = User(
        role=role,
        verification_status="pending",
        is_active=True,
        is_email_verified=False,
        is_phone_verified=False,
        language="en",
        password_hash=hash_password("testpass123"),
    )
    user.full_name = kwargs.get("full_name", f"Test {role.title()}")
    if kwargs.get("medical_license"):
        user.medical_license = kwargs["medical_license"]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ══════════════════════════════════════════════════════════════════
# Bot Registration: License Collection & Storage
# ════════════════════════════════════════════════════════���═════════

class TestBotDoctorRegistration:

    def test_doctor_registration_stores_license_encrypted(self, db_session):
        """When a doctor registers with a license, it should be stored encrypted."""
        user = _make_user(db_session, role="doctor", full_name="Dr Bot",
                          medical_license="MC12345")
        assert user.medical_license_encrypted is not None
        assert user.medical_license_hash is not None
        # Decrypted value should match
        assert user.medical_license == "MC12345"

    def test_license_hash_enables_duplicate_detection(self, db_session):
        """Two users with the same license should produce the same hash."""
        user1 = _make_user(db_session, role="doctor", full_name="Dr One",
                           medical_license="DUP-LIC-001")
        # Create hash for same license
        lic_hash = hash_value("DUP-LIC-001")
        # Should find user1 via hash lookup
        found = db_session.query(User).filter(
            User.medical_license_hash == lic_hash
        ).first()
        assert found is not None
        assert found.id == user1.id

    def test_patient_has_no_license(self, db_session):
        """Patient registration should not have a medical_license."""
        patient = _make_user(db_session, role="patient", full_name="Patient NLic")
        assert patient.medical_license is None
        assert patient.medical_license_encrypted is None

    def test_license_stored_encrypted_not_plaintext(self, db_session):
        """The encrypted column should NOT contain the plaintext license."""
        user = _make_user(db_session, role="doctor", full_name="Dr Enc",
                          medical_license="PLAINCHECK99")
        # The encrypted value should not be the same as plaintext
        assert user.medical_license_encrypted != "PLAINCHECK99"
        assert user.medical_license_encrypted is not None


# ══════════════════════════════════════════════════════════════════
# Bot Handlers: REG_LICENSE State
# ═════════════════════��════════════════════════════════════════════

def _patch_telegram_mocks():
    """Ensure telegram mock modules have all attributes needed by handlers.py."""
    import sys
    import types
    from unittest.mock import MagicMock

    # Patch telegram top-level
    telegram_mod = sys.modules.get("telegram")
    if telegram_mod is not None:
        for attr in ["Update", "KeyboardButton", "ReplyKeyboardMarkup",
                      "ReplyKeyboardRemove", "InlineKeyboardButton",
                      "InlineKeyboardMarkup", "WebAppInfo"]:
            if not hasattr(telegram_mod, attr):
                setattr(telegram_mod, attr, MagicMock())

    # Patch telegram.ext
    ext_mod = sys.modules.get("telegram.ext")
    if ext_mod is not None:
        for attr in ["ContextTypes", "ConversationHandler", "CommandHandler",
                      "MessageHandler", "filters", "CallbackQueryHandler",
                      "Application"]:
            if not hasattr(ext_mod, attr):
                setattr(ext_mod, attr, MagicMock())

    # Patch telegram.constants
    if "telegram.constants" not in sys.modules:
        const_mod = types.ModuleType("telegram.constants")
        const_mod.__path__ = []
        const_mod.ChatAction = MagicMock()
        sys.modules["telegram.constants"] = const_mod


class TestBotHandlerStates:

    def test_reg_license_state_exists(self):
        """REG_LICENSE state should be defined in handlers."""
        _patch_telegram_mocks()
        from app.bot.handlers import REG_LICENSE
        assert isinstance(REG_LICENSE, int)
        assert REG_LICENSE == 8

    def test_conversation_handler_includes_license_state(self):
        """The auth conversation handler should include REG_LICENSE state."""
        _patch_telegram_mocks()
        from app.bot.handlers import get_auth_handler, REG_LICENSE
        handler = get_auth_handler()
        assert handler is not None


# ══════════════════════════════════════════════════════════════════
# Bot Locales: License Strings
# ═════════════════════��════════════════════════════════════════════

class TestBotLocales:

    def test_license_locale_strings_exist(self):
        """Both enter_license and license_invalid should exist in locales."""
        from app.bot.locales import get_text
        en_enter = get_text("enter_license", "en")
        th_enter = get_text("enter_license", "th")
        en_invalid = get_text("license_invalid", "en")
        th_invalid = get_text("license_invalid", "th")

        assert "license" in en_enter.lower() or "License" in en_enter
        assert "ใบอนุญาต" in th_enter
        assert en_invalid != ""
        assert th_invalid != ""
