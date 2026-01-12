
import httpx
import logging

logger = logging.getLogger(__name__)

TMC_URL = "https://checkmd.tmc.or.th/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded"
}

async def verify_doctor_with_tmc(first_name: str, last_name: str) -> dict:
    """
    Verifies a doctor's status by querying the TMC website asynchronously.
    Returns:
        {
            "verified": bool,
            "message": str,
            "details": str (HTML snippet or text)
        }
    """
    try:
        payload = {
            "nm": first_name,
            "lp": last_name,
            "nm_en": "",
            "lp_en": "",
            "checkCode": "1",  # Thai Name Search
            "codecpe": ""
        }
        
        logger.info(f"Verifying doctor with TMC (Async): {first_name} {last_name}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(TMC_URL, data=payload, headers=HEADERS)
        
        if response.status_code != 200:
            logger.error(f"TMC verification failed. Status: {response.status_code}")
            return {
                "verified": False,
                "message": f"TMC Website Error (Status {response.status_code})",
                "details": "Connection failed"
            }
            
        # Check for success indicators in HTML
        if "ค้นพบผู้ประกอบวิชาชีพเวชกรรม" in response.text and "จำนวน 0 รายการ" not in response.text:
             return {
                 "verified": True,
                 "message": "Found in TMC Database",
                 "details": "Auto-verified via TMC Website"
             }
        elif "ไม่พบข้อมูล" in response.text or "จำนวน 0 รายการ" in response.text:
             return {
                 "verified": False,
                 "message": "Not Found in TMC Database",
                 "details": "Search returned 0 results"
             }
        else:
            return {
                "verified": False,
                "message": "Ambiguous Result",
                "details": "Could not determine status from HTML"
            }

    except Exception as e:
        logger.error(f"Error during TMC verification: {e}")
        return {
            "verified": False,
            "message": "Internal Error",
            "details": str(e)
        }
