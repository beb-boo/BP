import os
from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL")
RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"

if REDIS_URL:
    limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL, enabled=RATELIMIT_ENABLED)
else:
    limiter = Limiter(key_func=get_remote_address, enabled=RATELIMIT_ENABLED)
