"""Phase 5: Deployment Configuration tests."""

import os
import pytest


class TestDockerCompose:
    """5.1 - docker-compose.yml has all services."""

    def test_docker_compose_exists(self):
        assert os.path.exists("docker-compose.yml")

    def test_has_postgres_service(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "postgres:" in content

    def test_has_redis_service(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "redis:" in content

    def test_has_fastapi_service(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "fastapi:" in content

    def test_has_bot_service(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "bot:" in content

    def test_has_frontend_service(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "frontend:" in content

    def test_redis_url_configured(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "REDIS_URL" in content

    def test_database_url_configured(self):
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "DATABASE_URL" in content


class TestFrontendDockerfile:
    """5.2 - Frontend Dockerfile for standalone Next.js."""

    def test_frontend_dockerfile_exists(self):
        assert os.path.exists("frontend/Dockerfile")

    def test_uses_node_base(self):
        with open("frontend/Dockerfile") as f:
            content = f.read()
        assert "node:" in content

    def test_uses_standalone(self):
        with open("frontend/Dockerfile") as f:
            content = f.read()
        assert "standalone" in content

    def test_exposes_port_3000(self):
        with open("frontend/Dockerfile") as f:
            content = f.read()
        assert "3000" in content

    def test_multistage_build(self):
        with open("frontend/Dockerfile") as f:
            content = f.read()
        assert "AS deps" in content
        assert "AS builder" in content
        assert "AS runner" in content


class TestEnvExample:
    """5.3 - .env.example has all new variables."""

    def test_env_example_exists(self):
        assert os.path.exists(".env.example")

    def test_has_database_url(self):
        with open(".env.example") as f:
            content = f.read()
        assert "DATABASE_URL" in content

    def test_has_redis_url(self):
        with open(".env.example") as f:
            content = f.read()
        assert "REDIS_URL" in content

    def test_has_bot_mode(self):
        with open(".env.example") as f:
            content = f.read()
        assert "BOT_MODE" in content

    def test_has_webhook_vars(self):
        with open(".env.example") as f:
            content = f.read()
        assert "WEBHOOK_URL" in content
        assert "WEBHOOK_SECRET" in content

    def test_has_auto_create_tables(self):
        with open(".env.example") as f:
            content = f.read()
        assert "AUTO_CREATE_TABLES" in content

    def test_has_bypass_otp(self):
        with open(".env.example") as f:
            content = f.read()
        assert "BYPASS_OTP" in content

    def test_has_frontend_vars(self):
        with open(".env.example") as f:
            content = f.read()
        assert "NEXT_PUBLIC_API_URL" in content
        assert "NEXT_PUBLIC_API_KEY" in content

    def test_has_cors_var(self):
        with open(".env.example") as f:
            content = f.read()
        assert "ALLOWED_ORIGINS" in content

    def test_has_encryption_key(self):
        with open(".env.example") as f:
            content = f.read()
        assert "ENCRYPTION_KEY" in content


class TestClaudeMD:
    """5.4 - CLAUDE.md updated with deployment info."""

    def test_has_deployment_modes(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "## Deployment Modes" in content

    def test_has_local_dev_mode(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "Local Development" in content

    def test_has_production_mode(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "Production" in content

    def test_has_rate_limiter_in_architecture(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "rate_limiter.py" in content

    def test_has_webhook_in_architecture(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "webhook.py" in content

    def test_has_optional_env_vars(self):
        with open("CLAUDE.md") as f:
            content = f.read()
        assert "REDIS_URL" in content
        assert "BOT_MODE" in content
