"""Shared fixtures for BP Monitor test suite."""

import os
import sys
import types
import pytest
from unittest.mock import MagicMock
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock external SDKs that may not be installed in test environment
_mock_modules = {
    "google": {},
    "google.generativeai": {"GenerativeModel": MagicMock, "configure": MagicMock()},
    "google.generativeai.types": {},
    "google.ai": {},
    "google.ai.generativelanguage": {},
    "google.api_core": {},
    "google.protobuf": {},
    "telegram": {"Update": MagicMock},
    "telegram.ext": {"Application": MagicMock, "CommandHandler": MagicMock,
                     "MessageHandler": MagicMock, "ConversationHandler": MagicMock,
                     "CallbackQueryHandler": MagicMock, "filters": MagicMock()},
    "telegram.ext.filters": {"TEXT": MagicMock(), "Document": MagicMock()},
    "PIL": {"Image": MagicMock()},
    "PIL.Image": {"open": MagicMock()},
    "PIL.ExifTags": {"TAGS": {}},
}

# phonenumbers needs special handling for NumberParseException
class _NumberParseException(Exception):
    pass

_mock_modules["phonenumbers"] = {
    "parse": MagicMock(),
    "is_valid_number": MagicMock(return_value=True),
    "format_number": MagicMock(return_value="+66800000000"),
    "PhoneNumberFormat": MagicMock(),
    "NumberParseException": _NumberParseException,
}

for mod_name, attrs in _mock_modules.items():
    if mod_name not in sys.modules:
        mock_mod = types.ModuleType(mod_name)
        mock_mod.__path__ = []
        mock_mod.__all__ = []
        for k, v in attrs.items():
            setattr(mock_mod, k, v)
        sys.modules[mod_name] = mock_mod

# Set test env vars BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bp.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("API_KEYS", "test-api-key")
os.environ.setdefault("BYPASS_OTP", "true")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("BOT_MODE", "disabled")
os.environ.setdefault("GOOGLE_AI_API_KEY", "test-fake-key")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DISABLE_EMAIL_DELIVERY", "true")

from app.database import Base


@pytest.fixture(scope="session")
def test_engine():
    """Create a test SQLite database engine."""
    engine = create_engine("sqlite:///./test_bp.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Clean up test db file
    try:
        os.unlink("./test_bp.db")
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a transactional database session for each test."""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def test_client(test_engine):
    """Create a FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from app.utils.rate_limiter import limiter

    # Disable rate limiting for tests
    limiter.enabled = False

    TestSession = sessionmaker(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
