/**
 * Date/Time Utility Functions with Timezone Support
 * ==================================================
 * Provides consistent date formatting across the application
 * with user timezone support.
 */

// Common timezone choices matching backend
export const TIMEZONE_CHOICES = [
  { value: "UTC", label: { en: "UTC (Coordinated Universal Time)", th: "UTC (เวลาสากลเชิงพิกัด)" } },
  { value: "Asia/Bangkok", label: { en: "Asia/Bangkok (ICT, UTC+7)", th: "เอเชีย/กรุงเทพ (ICT, UTC+7)" } },
  { value: "Asia/Tokyo", label: { en: "Asia/Tokyo (JST, UTC+9)", th: "เอเชีย/โตเกียว (JST, UTC+9)" } },
  { value: "Asia/Singapore", label: { en: "Asia/Singapore (SGT, UTC+8)", th: "เอเชีย/สิงคโปร์ (SGT, UTC+8)" } },
  { value: "Asia/Hong_Kong", label: { en: "Asia/Hong Kong (HKT, UTC+8)", th: "เอเชีย/ฮ่องกง (HKT, UTC+8)" } },
  { value: "Asia/Seoul", label: { en: "Asia/Seoul (KST, UTC+9)", th: "เอเชีย/โซล (KST, UTC+9)" } },
  { value: "Asia/Shanghai", label: { en: "Asia/Shanghai (CST, UTC+8)", th: "เอเชีย/เซี่ยงไฮ้ (CST, UTC+8)" } },
  { value: "Asia/Kolkata", label: { en: "Asia/Kolkata (IST, UTC+5:30)", th: "เอเชีย/โกลกาตา (IST, UTC+5:30)" } },
  { value: "Asia/Dubai", label: { en: "Asia/Dubai (GST, UTC+4)", th: "เอเชีย/ดูไบ (GST, UTC+4)" } },
  { value: "America/New_York", label: { en: "America/New York (EST/EDT)", th: "อเมริกา/นิวยอร์ก (EST/EDT)" } },
  { value: "America/Los_Angeles", label: { en: "America/Los Angeles (PST/PDT)", th: "อเมริกา/ลอสแอนเจลิส (PST/PDT)" } },
  { value: "America/Chicago", label: { en: "America/Chicago (CST/CDT)", th: "อเมริกา/ชิคาโก (CST/CDT)" } },
  { value: "Europe/London", label: { en: "Europe/London (GMT/BST)", th: "ยุโรป/ลอนดอน (GMT/BST)" } },
  { value: "Europe/Paris", label: { en: "Europe/Paris (CET/CEST)", th: "ยุโรป/ปารีส (CET/CEST)" } },
  { value: "Europe/Berlin", label: { en: "Europe/Berlin (CET/CEST)", th: "ยุโรป/เบอร์ลิน (CET/CEST)" } },
  { value: "Australia/Sydney", label: { en: "Australia/Sydney (AEST/AEDT)", th: "ออสเตรเลีย/ซิดนีย์ (AEST/AEDT)" } },
  { value: "Pacific/Auckland", label: { en: "Pacific/Auckland (NZST/NZDT)", th: "แปซิฟิก/โอ๊คแลนด์ (NZST/NZDT)" } },
];

/**
 * Get locale string for language
 */
function getLocaleString(lang: string): string {
  return lang === "th" ? "th-TH" : "en-GB";
}

/**
 * Format a date with optional timezone
 * @param date - Date string or Date object
 * @param timezone - IANA timezone string (e.g., "Asia/Bangkok")
 * @param lang - Language code ("en" or "th")
 * @param options - Additional Intl.DateTimeFormat options
 */
export function formatDate(
  date: string | Date | null | undefined,
  timezone?: string,
  lang: string = "en",
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "-";

  try {
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "-";

    const defaultOptions: Intl.DateTimeFormatOptions = {
      day: "numeric",
      month: "short",
      year: "numeric",
      ...(timezone && { timeZone: timezone }),
      ...options,
    };

    return d.toLocaleDateString(getLocaleString(lang), defaultOptions);
  } catch {
    return "-";
  }
}

/**
 * Format time with optional timezone
 * @param date - Date string or Date object
 * @param timezone - IANA timezone string
 * @param lang - Language code
 */
export function formatTime(
  date: string | Date | null | undefined,
  timezone?: string,
  lang: string = "en"
): string {
  if (!date) return "-";

  try {
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "-";

    const options: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
      ...(timezone && { timeZone: timezone }),
    };

    return d.toLocaleTimeString(getLocaleString(lang), options);
  } catch {
    return "-";
  }
}

/**
 * Format date and time together
 * @param date - Date string or Date object
 * @param timezone - IANA timezone string
 * @param lang - Language code
 */
export function formatDateTime(
  date: string | Date | null | undefined,
  timezone?: string,
  lang: string = "en"
): string {
  if (!date) return "-";

  try {
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "-";

    const options: Intl.DateTimeFormatOptions = {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      ...(timezone && { timeZone: timezone }),
    };

    return d.toLocaleString(getLocaleString(lang), options);
  } catch {
    return "-";
  }
}

/**
 * Format date for form input (YYYY-MM-DD)
 * @param date - Date object or string
 */
export function formatDateForInput(date: string | Date | null | undefined): string {
  if (!date) return "";

  try {
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "";

    return d.toISOString().split("T")[0];
  } catch {
    return "";
  }
}

/**
 * Format time for form input (HH:MM)
 * @param date - Date object or string
 * @param timezone - Optional timezone to convert to
 */
export function formatTimeForInput(
  date: string | Date | null | undefined,
  timezone?: string
): string {
  if (!date) return "";

  try {
    const d = typeof date === "string" ? new Date(date) : date;
    if (isNaN(d.getTime())) return "";

    if (timezone) {
      return d.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: timezone,
        hour12: false,
      });
    }

    return d.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "";
  }
}

/**
 * Get timezone label for display
 * @param timezone - IANA timezone string
 * @param lang - Language code
 */
export function getTimezoneLabel(timezone: string, lang: string = "en"): string {
  const tz = TIMEZONE_CHOICES.find((t) => t.value === timezone);
  if (tz) {
    return lang === "th" ? tz.label.th : tz.label.en;
  }
  return timezone;
}

/**
 * Get current time in a specific timezone formatted as string
 * @param timezone - IANA timezone string
 * @param lang - Language code
 */
export function getCurrentTimeInTimezone(timezone: string, lang: string = "en"): string {
  return formatDateTime(new Date(), timezone, lang);
}
