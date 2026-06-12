"""Redis health/keep-alive helper.

Two jobs:
1. /health reports Redis status so uptime monitoring catches a broken
   REDIS_URL early (e.g. an Upstash database deleted for inactivity)
   instead of users discovering it via failing OTP/rate limits.
2. Each ping counts as database activity, which prevents Upstash's
   free-tier inactivity cleanup in the first place — the reminder cron
   calls this every 15 minutes.
"""

import logging
import os

logger = logging.getLogger(__name__)


def ping_redis(timeout: float = 3.0) -> str:
    """Returns 'ok' | 'unreachable' | 'not_configured'. Never raises."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return "not_configured"
    try:
        import redis
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
        client.ping()
        client.close()
        return "ok"
    except Exception as e:
        logger.warning(f"Redis ping failed: {e}")
        return "unreachable"
