"""Reminder cron idempotency: a second scheduler hit in the same 15-min
window must not double-send (the 07:00-vs-07:13 duplicate bug)."""

from datetime import datetime

from app.routers import cron


class FakeRedis:
    """Minimal stand-in for the bits of redis-py the dedup uses."""

    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)


class TestReminderDedup:
    def test_second_hit_same_window_is_skipped(self):
        r = FakeRedis()
        ws = datetime(2026, 6, 16, 7, 0, 0)
        assert cron._claim_window(r, 42, ws) is True   # 07:00 external scheduler
        assert cron._claim_window(r, 42, ws) is False  # 07:13 backstop -> skip

    def test_release_allows_retry_in_same_window(self):
        r = FakeRedis()
        ws = datetime(2026, 6, 16, 7, 0, 0)
        assert cron._claim_window(r, 42, ws) is True
        cron._release_window(r, 42, ws)                # first send failed
        assert cron._claim_window(r, 42, ws) is True   # later hit retries

    def test_fails_open_without_redis(self):
        ws = datetime(2026, 6, 16, 7, 0, 0)
        # No client -> never block a reminder.
        assert cron._claim_window(None, 42, ws) is True
        cron._release_window(None, 42, ws)  # no-op, must not raise

    def test_claims_are_isolated_per_user_and_window(self):
        r = FakeRedis()
        w7 = datetime(2026, 6, 16, 7, 0, 0)
        w19 = datetime(2026, 6, 16, 19, 0, 0)
        assert cron._claim_window(r, 1, w7) is True
        assert cron._claim_window(r, 2, w7) is True    # different user
        assert cron._claim_window(r, 1, w19) is True   # different window
        assert cron._claim_window(r, 1, w7) is False   # same user+window -> dup

    def test_claim_error_fails_open(self):
        class Broken(FakeRedis):
            def set(self, *a, **k):
                raise RuntimeError("redis down")

        ws = datetime(2026, 6, 16, 7, 0, 0)
        assert cron._claim_window(Broken(), 42, ws) is True


class TestWindowMatch:
    def test_0700_collision_window(self):
        """Why 07:00 and 07:13 collide: a hit at 07:00 and a hit at 07:13
        both resolve to the same [07:00, 07:15) window, so the 07:00
        reminder is 'due' on both — dedup is what prevents the 2nd send."""
        in_window = (datetime(2026, 6, 16, 7, 0, 0), datetime(2026, 6, 16, 7, 15, 0))
        next_window = (datetime(2026, 6, 16, 7, 15, 0), datetime(2026, 6, 16, 7, 30, 0))
        assert cron._due_in_window(["07:00", "19:00"], *in_window) is True
        assert cron._due_in_window(["07:00", "19:00"], *next_window) is False
