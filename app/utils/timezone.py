"""
Timezone Utility Module
=======================
Centralized timezone handling for the application.
Allows configurable timezone via APP_TIMEZONE environment variable.
"""

import os
from datetime import datetime
from typing import Optional
from pytz import timezone, UTC, all_timezones
from pytz.exceptions import UnknownTimeZoneError

# Default timezone from environment variable (fallback to UTC)
DEFAULT_TIMEZONE = os.getenv("APP_TIMEZONE", "UTC")

# Common timezone choices for user selection
TIMEZONE_CHOICES = [
    ("UTC", "UTC (Coordinated Universal Time)", "UTC (เวลาสากลเชิงพิกัด)"),
    ("Asia/Bangkok", "Asia/Bangkok (ICT, UTC+7)", "เอเชีย/กรุงเทพ (ICT, UTC+7)"),
    ("Asia/Tokyo", "Asia/Tokyo (JST, UTC+9)", "เอเชีย/โตเกียว (JST, UTC+9)"),
    ("Asia/Singapore", "Asia/Singapore (SGT, UTC+8)", "เอเชีย/สิงคโปร์ (SGT, UTC+8)"),
    ("Asia/Hong_Kong", "Asia/Hong Kong (HKT, UTC+8)", "เอเชีย/ฮ่องกง (HKT, UTC+8)"),
    ("Asia/Seoul", "Asia/Seoul (KST, UTC+9)", "เอเชีย/โซล (KST, UTC+9)"),
    ("Asia/Shanghai", "Asia/Shanghai (CST, UTC+8)", "เอเชีย/เซี่ยงไฮ้ (CST, UTC+8)"),
    ("Asia/Kolkata", "Asia/Kolkata (IST, UTC+5:30)", "เอเชีย/โกลกาตา (IST, UTC+5:30)"),
    ("Asia/Dubai", "Asia/Dubai (GST, UTC+4)", "เอเชีย/ดูไบ (GST, UTC+4)"),
    ("America/New_York", "America/New York (EST/EDT)", "อเมริกา/นิวยอร์ก (EST/EDT)"),
    ("America/Los_Angeles", "America/Los Angeles (PST/PDT)", "อเมริกา/ลอสแอนเจลิส (PST/PDT)"),
    ("America/Chicago", "America/Chicago (CST/CDT)", "อเมริกา/ชิคาโก (CST/CDT)"),
    ("Europe/London", "Europe/London (GMT/BST)", "ยุโรป/ลอนดอน (GMT/BST)"),
    ("Europe/Paris", "Europe/Paris (CET/CEST)", "ยุโรป/ปารีส (CET/CEST)"),
    ("Europe/Berlin", "Europe/Berlin (CET/CEST)", "ยุโรป/เบอร์ลิน (CET/CEST)"),
    ("Australia/Sydney", "Australia/Sydney (AEST/AEDT)", "ออสเตรเลีย/ซิดนีย์ (AEST/AEDT)"),
    ("Pacific/Auckland", "Pacific/Auckland (NZST/NZDT)", "แปซิฟิก/โอ๊คแลนด์ (NZST/NZDT)"),
]


def get_timezone(tz_name: Optional[str] = None):
    """
    Get timezone object by name.
    Falls back to DEFAULT_TIMEZONE if invalid or not provided.

    Args:
        tz_name: Timezone name (e.g., "Asia/Bangkok")

    Returns:
        pytz timezone object
    """
    tz_name = tz_name or DEFAULT_TIMEZONE
    try:
        return timezone(tz_name)
    except UnknownTimeZoneError:
        return timezone(DEFAULT_TIMEZONE)


def now_utc() -> datetime:
    """Get current time in UTC (timezone-aware)"""
    return datetime.now(UTC)


def now_tz(tz_name: Optional[str] = None) -> datetime:
    """
    Get current time in specified timezone.

    Args:
        tz_name: Timezone name. If None, uses DEFAULT_TIMEZONE.

    Returns:
        Timezone-aware datetime
    """
    return datetime.now(get_timezone(tz_name))


def to_user_timezone(dt: datetime, user_tz: Optional[str] = None) -> datetime:
    """
    Convert datetime to user's timezone.

    Args:
        dt: Datetime object (naive or aware)
        user_tz: User's timezone name

    Returns:
        Datetime in user's timezone
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is in UTC
        dt = UTC.localize(dt)
    return dt.astimezone(get_timezone(user_tz))


def to_utc(dt: datetime, source_tz: Optional[str] = None) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime object
        source_tz: Source timezone (if dt is naive)

    Returns:
        Datetime in UTC
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        source = get_timezone(source_tz)
        dt = source.localize(dt)
    return dt.astimezone(UTC)


def format_datetime(
    dt: datetime,
    user_tz: Optional[str] = None,
    fmt: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format datetime in user's timezone.

    Args:
        dt: Datetime object
        user_tz: User's timezone name
        fmt: strftime format string

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    local_dt = to_user_timezone(dt, user_tz)
    return local_dt.strftime(fmt)


def format_date(dt: datetime, user_tz: Optional[str] = None) -> str:
    """Format date only (YYYY-MM-DD)"""
    return format_datetime(dt, user_tz, "%Y-%m-%d")


def format_time(dt: datetime, user_tz: Optional[str] = None) -> str:
    """Format time only (HH:MM)"""
    return format_datetime(dt, user_tz, "%H:%M")


def is_valid_timezone(tz_name: str) -> bool:
    """Check if timezone name is valid"""
    if not tz_name:
        return False
    return tz_name in all_timezones


def get_timezone_choices_dict(lang: str = "en") -> list:
    """
    Get timezone choices for frontend/API.

    Args:
        lang: Language code ("en" or "th")

    Returns:
        List of dicts with value and label
    """
    result = []
    for tz_value, label_en, label_th in TIMEZONE_CHOICES:
        result.append({
            "value": tz_value,
            "label": label_th if lang == "th" else label_en
        })
    return result


# Legacy compatibility - maps to now_tz with default timezone
def now_th() -> datetime:
    """
    Legacy function for backward compatibility.
    Returns current time in the default app timezone.

    DEPRECATED: Use now_tz() instead.
    """
    return now_tz()
