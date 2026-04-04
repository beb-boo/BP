
import os
import re
import httpx
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TMC_URL = os.getenv("TMC_URL", "https://checkmd.tmc.or.th/v3/search")
TMC_REFERER = os.getenv("TMC_REFERER", "https://checkmd.tmc.or.th/v3")
TMC_TIMEOUT = float(os.getenv("TMC_TIMEOUT", "15"))

HEADERS = {
    "User-Agent": os.getenv(
        "TMC_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": TMC_REFERER,
}

# Keywords indicating license suspension/revocation
SUSPENSION_KEYWORDS = ["พักใช้", "เพิกถอน", "ระงับ", "พักใช้ใบอนุญาต"]


@dataclass
class TMCDoctorResult:
    """Structured result from TMC doctor verification."""
    verified: bool = False
    found: bool = False
    message: str = ""
    full_name_th: Optional[str] = None
    full_name_en: Optional[str] = None
    license_year_be: Optional[int] = None  # Buddhist Era
    license_year_ce: Optional[int] = None  # Common Era
    specialties: List[str] = field(default_factory=list)
    license_suspended: bool = False
    suspension_detail: Optional[str] = None
    result_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_legacy_dict(self) -> dict:
        """Backward-compatible dict for existing callers."""
        details = f"TMC v3: {self.full_name_th or 'N/A'}"
        if self.license_suspended:
            details += f", License SUSPENDED: {self.suspension_detail or 'Unknown reason'}"
        if self.specialties:
            details += f", Specialties: {', '.join(self.specialties)}"
        if self.license_year_ce:
            details += f", Licensed since {self.license_year_ce}"
        return {
            "verified": self.verified,
            "message": self.message,
            "details": details,
        }


def _parse_tmc_response(html: str) -> TMCDoctorResult:
    """Parse TMC v3 search result HTML and extract doctor information."""
    result = TMCDoctorResult()

    soup = BeautifulSoup(html, "html.parser")

    # 1. Check result count from header
    heading = soup.find("div", class_="panel-heading")
    if heading:
        heading_text = heading.get_text(strip=True)
        count_match = re.search(r"จำนวน\s*(\d+)\s*รายการ", heading_text)
        if count_match:
            result.result_count = int(count_match.group(1))

    # Not found cases
    full_text = soup.get_text()
    if result.result_count == 0 or "ไม่พบข้อมูล" in full_text:
        result.message = "Not Found in TMC Database"
        return result

    result.found = True

    # Multiple matches — don't auto-verify
    if result.result_count > 1:
        result.message = f"Multiple matches found ({result.result_count} results), manual review needed"
        return result

    # 2. Extract Thai name — first <strong> inside panel-body article
    panel_body = soup.find("div", class_="panel-body")
    if panel_body:
        name_tag = panel_body.find("strong")
        if name_tag:
            result.full_name_th = name_tag.get_text(strip=True)

    # 3. Extract English name — div with class text-info containing M.D. or uppercase
    if panel_body:
        text_info_divs = panel_body.find_all("div", class_=re.compile(r"text-info"))
        for div in text_info_divs:
            text = div.get_text(strip=True)
            if "M.D." in text or (text and text[0].isupper() and "," in text):
                result.full_name_en = text
                break

    # 4. Extract license year
    year_match = re.search(
        r"เป็นผู้ประกอบวิชาชีพเวชกรรมตั้งแต่\s*พ\.ศ\.\s*(\d{4})", full_text
    )
    if year_match:
        result.license_year_be = int(year_match.group(1))
        result.license_year_ce = result.license_year_be - 543

    # 5. Extract specialties
    specialty_lists = soup.find_all("ul", class_=re.compile(r"fa-ul.*text-info"))
    seen = set()
    for ul in specialty_lists:
        for li in ul.find_all("li"):
            text = li.get_text(strip=True)
            if text and text not in seen:
                seen.add(text)
                # Clean up: remove "สาขา " prefix if present
                cleaned = re.sub(r"^สาขา\s*", "", text).strip()
                if cleaned:
                    result.specialties.append(cleaned)

    # 6. Detect license suspension
    for keyword in SUSPENSION_KEYWORDS:
        if keyword in full_text:
            result.license_suspended = True
            # Try to extract the suspension detail sentence
            for line in full_text.split("\n"):
                line = line.strip()
                if keyword in line and len(line) > 10:
                    result.suspension_detail = line[:500]
                    break
            break

    # Also check alert-danger divs for suspension info
    if not result.license_suspended:
        danger_divs = soup.find_all("div", class_=re.compile(r"alert-danger"))
        for div in danger_divs:
            text = div.get_text(strip=True)
            if any(kw in text for kw in SUSPENSION_KEYWORDS):
                result.license_suspended = True
                result.suspension_detail = text[:500]
                break

    # Final verification: found AND not suspended
    if result.found and not result.license_suspended:
        result.verified = True
        result.message = "Found in TMC Database"
    elif result.license_suspended:
        result.message = "Doctor found but license is SUSPENDED"
    else:
        result.message = "Found in TMC Database (status unclear)"

    return result


async def verify_doctor_with_tmc_v3(
    first_name_th: str = "",
    last_name_th: str = "",
    first_name_en: str = "",
    last_name_en: str = "",
) -> TMCDoctorResult:
    """
    Verify a doctor against the TMC v3 website.
    Searches by Thai or English name.
    """
    # Determine search mode
    if first_name_th or last_name_th:
        check_code = "1"
    elif first_name_en or last_name_en:
        check_code = "2"
    else:
        return TMCDoctorResult(message="No search criteria provided")

    payload = {
        "nm": first_name_th,
        "lp": last_name_th,
        "nm_en": first_name_en,
        "lp_en": last_name_en,
        "checkCode": check_code,
        "codecpe": "",
    }

    logger.info(
        f"Verifying doctor with TMC v3: "
        f"TH='{first_name_th} {last_name_th}', EN='{first_name_en} {last_name_en}'"
    )

    try:
        async with httpx.AsyncClient(timeout=TMC_TIMEOUT) as client:
            response = await client.post(
                TMC_URL, data=payload, headers=HEADERS,
                follow_redirects=False,
            )

        # Handle redirects — TMC may have changed URL
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "")
            logger.warning(
                f"TMC returned redirect {response.status_code} → {location}. "
                f"TMC may have changed their URL. Update TMC_URL env variable."
            )
            return TMCDoctorResult(
                message=f"TMC URL redirect detected ({response.status_code}). "
                        f"Please update TMC_URL env to: {location}"
            )

        if response.status_code != 200:
            logger.error(f"TMC verification failed. Status: {response.status_code}")
            return TMCDoctorResult(
                message=f"TMC Website Error (Status {response.status_code})"
            )

        return _parse_tmc_response(response.text)

    except httpx.TimeoutException:
        logger.error("TMC verification timed out")
        return TMCDoctorResult(message="TMC Website Timeout")
    except Exception as e:
        logger.error(f"Error during TMC verification: {e}")
        return TMCDoctorResult(message="Internal Error")


# ── Backward-compatible wrapper ──────────────────────────────
async def verify_doctor_with_tmc(first_name: str, last_name: str) -> dict:
    """
    Legacy wrapper — maintains backward compatibility with existing callers.
    Returns dict with keys: verified, message, details.
    """
    result = await verify_doctor_with_tmc_v3(
        first_name_th=first_name,
        last_name_th=last_name,
    )
    return result.to_legacy_dict()
