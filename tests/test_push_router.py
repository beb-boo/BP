"""Push router: subscribe upsert, ownership, auth, preferences endpoints."""

import pytest

API_KEY = "test-api-key"
EP = "https://fcm.googleapis.com/fcm/send/router-test-1"


@pytest.fixture(scope="module")
def auth_headers(test_client):
    def make(email):
        test_client.post("/api/v1/auth/register",
                         headers={"X-API-Key": API_KEY},
                         json={"email": email, "password": "password123",
                               "full_name": "Push Tester", "role": "patient"})
        res = test_client.post("/api/v1/auth/login",
                               headers={"X-API-Key": API_KEY},
                               json={"email": email, "password": "password123"})
        token = res.json()["data"]["access_token"]
        return {"X-API-Key": API_KEY, "Authorization": f"Bearer {token}"}

    return {"u1": make("push-r1@test.com"), "u2": make("push-r2@test.com")}


SUB_BODY = {"endpoint": EP, "keys": {"p256dh": "BKey", "auth": "AKey"}}


class TestSubscribe:
    def test_requires_auth(self, test_client):
        res = test_client.post("/api/v1/push/subscribe",
                               headers={"X-API-Key": API_KEY}, json=SUB_BODY)
        assert res.status_code in (401, 403)

    def test_subscribe_then_upsert(self, test_client, auth_headers):
        r1 = test_client.post("/api/v1/push/subscribe",
                              headers=auth_headers["u1"], json=SUB_BODY)
        assert r1.status_code == 200
        sub_id = r1.json()["data"]["id"]

        r2 = test_client.post("/api/v1/push/subscribe",
                              headers=auth_headers["u1"], json=SUB_BODY)
        assert r2.status_code == 200
        assert r2.json()["data"]["id"] == sub_id

    def test_other_user_cannot_claim_endpoint(self, test_client, auth_headers):
        res = test_client.post("/api/v1/push/subscribe",
                               headers=auth_headers["u2"], json=SUB_BODY)
        assert res.status_code == 409

    def test_unsubscribe_idempotent(self, test_client, auth_headers):
        r = test_client.request("DELETE", "/api/v1/push/subscribe",
                                headers=auth_headers["u1"],
                                json={"endpoint": EP})
        assert r.status_code == 200
        r = test_client.request("DELETE", "/api/v1/push/subscribe",
                                headers=auth_headers["u1"],
                                json={"endpoint": "https://unknown/x"})
        assert r.status_code == 200

    def test_resubscribe_reactivates(self, test_client, auth_headers):
        r = test_client.post("/api/v1/push/subscribe",
                             headers=auth_headers["u1"], json=SUB_BODY)
        assert r.status_code == 200


class TestPreferences:
    def test_get_defaults(self, test_client, auth_headers):
        r = test_client.get("/api/v1/users/me/notification-preferences",
                            headers=auth_headers["u1"])
        assert r.status_code == 200
        prefs = r.json()["data"]["preferences"]
        assert prefs["show_details_in_push"] is False
        assert prefs["reminder_times"] == ["07:00", "19:00"]

    def test_patch_shallow_merge(self, test_client, auth_headers):
        r = test_client.patch("/api/v1/users/me/notification-preferences",
                              headers=auth_headers["u1"],
                              json={"show_details_in_push": True})
        assert r.status_code == 200
        prefs = r.json()["data"]["preferences"]
        assert prefs["show_details_in_push"] is True
        assert prefs["reminder_enabled"] is True  # untouched key intact

    def test_patch_rejects_bad_time(self, test_client, auth_headers):
        r = test_client.patch("/api/v1/users/me/notification-preferences",
                              headers=auth_headers["u1"],
                              json={"reminder_times": ["25:99"]})
        assert r.status_code == 422
