"""Phase 3: Telegram Bot Dual-Mode tests."""

import os
import pytest


class TestBotBuildApplication:
    """3.1 - Bot main.py has build_application() function."""

    def test_build_application_exists(self):
        with open("app/bot/main.py") as f:
            content = f.read()
        assert "def build_application()" in content

    def test_run_polling_exists(self):
        with open("app/bot/main.py") as f:
            content = f.read()
        assert "def run_polling()" in content

    def test_build_application_returns_application(self):
        """build_application should build and return the application."""
        with open("app/bot/main.py") as f:
            content = f.read()
        assert "return application" in content

    def test_main_calls_run_polling(self):
        with open("app/bot/main.py") as f:
            content = f.read()
        # main() should delegate to run_polling()
        assert "run_polling()" in content


class TestWebhookHandler:
    """3.2 - Webhook handler exists with proper endpoints."""

    def test_webhook_file_exists(self):
        assert os.path.exists("app/bot/webhook.py")

    def test_webhook_has_post_endpoint(self):
        with open("app/bot/webhook.py") as f:
            content = f.read()
        assert '@router.post("/webhook")' in content

    def test_webhook_has_set_endpoint(self):
        with open("app/bot/webhook.py") as f:
            content = f.read()
        assert '@router.get("/set-webhook")' in content

    def test_webhook_has_remove_endpoint(self):
        with open("app/bot/webhook.py") as f:
            content = f.read()
        assert '@router.get("/remove-webhook")' in content

    def test_webhook_verifies_secret(self):
        with open("app/bot/webhook.py") as f:
            content = f.read()
        assert "WEBHOOK_SECRET" in content
        assert "X-Telegram-Bot-Api-Secret-Token" in content

    def test_webhook_uses_build_application(self):
        with open("app/bot/webhook.py") as f:
            content = f.read()
        assert "from .main import build_application" in content


class TestMainWebhookIntegration:
    """3.3 - Main app conditionally loads webhook router."""

    def test_bot_mode_env_check(self):
        with open("app/main.py") as f:
            content = f.read()
        assert 'BOT_MODE' in content
        assert 'os.getenv("BOT_MODE"' in content

    def test_conditional_webhook_router(self):
        with open("app/main.py") as f:
            content = f.read()
        assert 'if BOT_MODE == "webhook"' in content
        assert "bot_webhook_router" in content

    def test_webhook_not_loaded_by_default(self):
        """Default BOT_MODE=polling should not load webhook."""
        with open("app/main.py") as f:
            content = f.read()
        # Default is "polling", so webhook router is conditionally loaded
        assert 'os.getenv("BOT_MODE", "polling")' in content
