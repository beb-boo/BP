"""API Integration tests - tests actual HTTP endpoints."""

import pytest


class TestHealthEndpoints:
    """Basic API health checks."""

    def test_root_endpoint(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Blood Pressure" in data["message"]

    def test_health_endpoint(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_docs_endpoint(self, test_client):
        response = test_client.get("/docs")
        assert response.status_code == 200


class TestAuthEndpoints:
    """Authentication API tests."""

    def test_register_requires_api_key(self, test_client):
        """Register without API key should fail."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com", "password": "test1234", "full_name": "Test", "role": "patient"},
            headers={}  # No API key
        )
        # Should fail with 401/403/422 (missing API key)
        assert response.status_code in [401, 403, 422, 400]

    def test_register_user(self, test_client):
        """Register a new user."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "testpass123",
                "full_name": "Test User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["role"] == "patient"

    def test_register_duplicate_email(self, test_client):
        """Register with same email should fail."""
        # First registration
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "testpass123",
                "full_name": "Dup User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        # Second registration with same email
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "testpass123",
                "full_name": "Dup User 2",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400

    def test_login_with_valid_credentials(self, test_client):
        """Login with correct credentials."""
        # Register first
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@test.com",
                "password": "testpass123",
                "full_name": "Login User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        # Login
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "testpass123"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]

    def test_login_with_wrong_password(self, test_client):
        """Login with wrong password should fail."""
        # Register first
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpwd@test.com",
                "password": "testpass123",
                "full_name": "Wrong Pwd User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        # Login with wrong password
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpwd@test.com", "password": "wrongpassword"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 401


class TestBPRecordsEndpoints:
    """Blood Pressure Records API tests."""

    def _get_auth_headers(self, test_client):
        """Helper to register, login, and get auth headers."""
        import uuid
        email = f"bp_{uuid.uuid4().hex[:8]}@test.com"
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "full_name": "BP Test User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        login_resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "testpass123"},
            headers={"X-API-Key": "test-api-key"}
        )
        token = login_resp.json()["data"]["access_token"]
        return {
            "X-API-Key": "test-api-key",
            "Authorization": f"Bearer {token}"
        }

    def test_create_bp_record(self, test_client):
        headers = self._get_auth_headers(test_client)
        response = test_client.post(
            "/api/v1/bp-records",
            json={
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72,
                "measurement_date": "2024-01-15T10:00:00",
                "measurement_time": "10:00"
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["record"]["systolic"] == 120

    def test_get_bp_records(self, test_client):
        headers = self._get_auth_headers(test_client)
        # Create a record first
        test_client.post(
            "/api/v1/bp-records",
            json={
                "systolic": 130,
                "diastolic": 85,
                "pulse": 75,
                "measurement_date": "2024-01-16T10:00:00",
                "measurement_time": "10:00"
            },
            headers=headers
        )
        # Get records
        response = test_client.get("/api/v1/bp-records", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "records" in data["data"]

    def test_get_bp_stats(self, test_client):
        headers = self._get_auth_headers(test_client)
        response = test_client.get("/api/v1/stats/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data["data"]

    def test_bp_records_requires_auth(self, test_client):
        """BP records without auth should fail."""
        response = test_client.get(
            "/api/v1/bp-records",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code in [401, 403]


class TestChangePasswordEndpoint:
    """Test the change password fix (Phase 1.4)."""

    def test_change_password_with_confirm(self, test_client):
        """Change password should work with confirm_new_password field."""
        import uuid
        email = f"chgpwd_{uuid.uuid4().hex[:8]}@test.com"

        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "oldpass123",
                "full_name": "ChgPwd User",
                "role": "patient"
            },
            headers={"X-API-Key": "test-api-key"}
        )

        # Login
        login_resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "oldpass123"},
            headers={"X-API-Key": "test-api-key"}
        )
        token = login_resp.json()["data"]["access_token"]
        headers = {
            "X-API-Key": "test-api-key",
            "Authorization": f"Bearer {token}"
        }

        # Change password
        response = test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "oldpass123",
                "new_password": "newpass456",
                "confirm_new_password": "newpass456"
            },
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
