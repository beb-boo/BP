"""Central settings for PWA-era configuration (T4.4).

Scope (deliberate): only the env vars introduced by the PWA work
(Web Push VAPID, cron) plus the bot token the notification adapters
need. Pre-existing env reads scattered across the codebase
(SECRET_KEY, DATABASE_URL, ...) are a follow-up — migrating them all
at once is high-risk for zero behavior gain.

No pydantic-settings dependency: a frozen dataclass + lru_cache is
enough for read-only process-lifetime config.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class PWASettings:
    vapid_public: str
    vapid_private: str
    vapid_subject: str
    cron_secret: str
    telegram_bot_token: str

    @property
    def web_push_configured(self) -> bool:
        return bool(self.vapid_private and self.vapid_subject)

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token)


@lru_cache(maxsize=1)
def get_pwa_settings() -> PWASettings:
    return PWASettings(
        vapid_public=os.getenv("WEB_PUSH_VAPID_PUBLIC", ""),
        vapid_private=os.getenv("WEB_PUSH_VAPID_PRIVATE", ""),
        vapid_subject=os.getenv("WEB_PUSH_VAPID_SUBJECT", ""),
        cron_secret=os.getenv("CRON_SECRET", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
    )
