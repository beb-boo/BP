"""Central subscription state utility — single source of truth.

Every API endpoint, bot handler, and frontend-facing response MUST use these
functions to determine a user's effective subscription status.  The database
field ``subscription_tier`` is treated as a *raw* value; the **active** state
is always derived from ``subscription_expires_at`` (plus the bypass list).
"""

from datetime import datetime
import pytz
from .timezone import now_tz
from .security import check_premium


def _ensure_aware(dt: datetime) -> datetime:
    """Make a naive datetime timezone-aware (assume UTC) for safe comparison.

    PostgreSQL returns tz-aware datetimes; SQLite strips timezone info.
    This helper ensures comparisons never fail due to naive vs aware mismatch.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=pytz.UTC)
    return dt


def is_premium_active(user) -> bool:
    """Return True when the user currently has premium access.

    Delegates to ``check_premium`` which handles:
    - bypass users (PREMIUM_BYPASS_USERS env)
    - expiry-based check (tier == premium AND expires_at > now)
    """
    return check_premium(user)


def get_subscription_info(user) -> dict:
    """Return a normalised subscription payload suitable for API serialisation.

    Key behaviour
    * Expired premium → ``subscription_tier`` is reported as ``"free"``.
    * Bypass users → always ``"premium"`` / ``is_premium_active=True``.
    * ``days_remaining`` is clamped to ≥ 0.
    """
    active = check_premium(user)
    effective_tier = "premium" if active else "free"

    expires_at = user.subscription_expires_at
    days_remaining = 0

    if active and expires_at:
        aware_expires = _ensure_aware(expires_at)
        delta = aware_expires - now_tz()
        days_remaining = max(0, delta.days)

    return {
        "subscription_tier": effective_tier,
        "is_premium_active": active,
        "subscription_expires_at": str(expires_at) if expires_at else None,
        "days_remaining": days_remaining,
    }


def normalize_subscription_state(user, db=None) -> bool:
    """Persist-normalize an expired premium user back to free in the database.

    If the user's raw DB state says ``premium`` but their subscription has
    actually expired (and they are NOT a bypass user), this function writes
    ``subscription_tier = "free"`` back to the database so that the stale
    state does not persist across requests.

    Returns True if the user was downgraded, False otherwise.

    If *db* is provided the caller is responsible for committing.
    If *db* is None the change is only made on the in-memory object (useful
    when the caller will commit later or when no session is available).
    """
    if user.subscription_tier != "premium":
        return False

    # Bypass users must never be downgraded
    if check_premium(user):
        return False

    # At this point: tier is premium but check_premium returned False
    # → subscription is expired (or expiry is null). Downgrade.
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        "Self-heal: downgrading expired premium user %s (expires_at=%s)",
        user.id,
        user.subscription_expires_at,
    )
    user.subscription_tier = "free"
    if db is not None:
        db.add(user)
        db.commit()
    return True


def get_renewal_base_datetime(user, now: datetime) -> datetime:
    """Determine the base datetime for a subscription renewal.

    * Active premium (expiry in the future) → stack from existing expiry.
    * Otherwise (expired / free) → start fresh from *now*.
    """
    if (
        user.subscription_tier == "premium"
        and user.subscription_expires_at
        and _ensure_aware(user.subscription_expires_at) > _ensure_aware(now)
    ):
        return user.subscription_expires_at
    return now
