import os
from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL")
RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"

if REDIS_URL:
    # Rate limiting must FAIL OPEN: a Redis hiccup (frequent on
    # serverless — frozen connection pools, transient DNS errors like
    # "[Errno 16] Device or resource busy" on Vercel) must never 500
    # the actual request. On storage errors slowapi falls back to
    # per-instance in-memory counting and, failing that, lets the
    # request through (swallow_errors).
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=REDIS_URL,
        enabled=RATELIMIT_ENABLED,
        swallow_errors=True,
        in_memory_fallback_enabled=True,
    )
else:
    limiter = Limiter(key_func=get_remote_address, enabled=RATELIMIT_ENABLED)
