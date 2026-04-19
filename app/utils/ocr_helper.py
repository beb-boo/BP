
import os
import json
import logging
import google.generativeai as genai
import PIL.Image
from PIL.ExifTags import TAGS
from dotenv import load_dotenv
from ..schemas import OCRResult
from datetime import datetime, timedelta
from typing import Optional
from .timezone import now_tz

# OCR date sanity check: discard OCR-read date if it's this many days away from upload time.
# BP monitors with un-set internal clocks often report defaults like 2024-01-01 — this catches them.
OCR_DATE_SANITY_WINDOW_DAYS = 30

load_dotenv()
logger = logging.getLogger(__name__)

GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
else:
    logger.warning("GOOGLE_AI_API_KEY not set, OCR features will not work")

def get_image_metadata(image_path: str) -> dict:
    """Extract metadata from image"""
    try:
        img = PIL.Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            metadata = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                metadata[tag_name] = str(value) # Convert to string for safety
            return metadata
        return {}
    except Exception as e:
        logger.error(f"Error reading image metadata: {e}")
        return {}

def extract_exif_datetime(metadata: dict):
    """Attempt to parse DateTimeOriginal from EXIF"""
    if not metadata:
        return None
    
    # Common EXIF date tags
    date_str = metadata.get('DateTimeOriginal') or metadata.get('DateTime')
    if not date_str:
        return None
    
    # EXIF format is usually "YYYY:MM:DD HH:MM:SS"
    try:
        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        return dt
    except ValueError:
        pass
        
    try:
         dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
         return dt
    except ValueError:
        pass
        
    return None

def read_blood_pressure_with_gemini(
    image_path: str,
    upload_time: Optional[datetime] = None,
) -> OCRResult:
    """Read blood pressure values from image using Gemini API with priority timestamp logic.

    Timestamp fallback order: OCR (image) → EXIF → upload_time (caller-provided) → now_tz().
    OCR date/time is discarded if it falls outside ±OCR_DATE_SANITY_WINDOW_DAYS of the
    reference time (upload_time or now) to guard against BP monitors with unset clocks.
    """
    if not GOOGLE_AI_API_KEY:
        return OCRResult(error="Google AI API key not configured")

    model = genai.GenerativeModel(GEMINI_MODEL)

    try:
        img = PIL.Image.open(image_path)
        img.verify()  # Verify it's a valid image
        img = PIL.Image.open(image_path)  # Re-open after verify (verify closes it)
    except FileNotFoundError:
        return OCRResult(error="Image not found")
    except PIL.Image.UnidentifiedImageError:
        return OCRResult(error="Unsupported image format. Please send as JPEG or PNG.")
    except Exception as e:
        logger.error(f"Error opening image {image_path}: {e}")
        return OCRResult(error=f"Cannot read image. Please try JPEG or PNG format.")

    prompt = """
    Analyze this blood pressure monitor screen image:
    1. Extract Systolic, Diastolic, and Pulse values.
       - Note: Standard vertical layout is usually Systolic (Top), Diastolic (Middle), Pulse (Bottom).
       - Note: Pulse is often smaller or at the very bottom.
    2. Extract Date and Time ONLY IF explicitly visible on the screen.
       - LOOK CAREFULLY: Date/Time might be small, in a corner, or faint.
       - Formats can vary: "YYYY/MM/DD", "DD/MM", "MM-DD", "HH:MM", "AM/PM".
       - If you see a clock or calendar icon, the numbers next to it are likely time/date.
       - DO NOT GUESS the date or year if it is not shown.
       - If only Time is shown, return Date as null.
       - If only Date is shown, return Time as null.
    3. Return ONLY a JSON object: {"systolic": int, "diastolic": int, "pulse": int, "date": "YYYY-MM-DD" or null, "time": "HH:MM" or null}
       - Convert date to YYYY-MM-DD. Use current year ONLY if month/day is visible but year is missing.
       - Convert time to 24-hour HH:MM.
    4. If any value is completely illegible or missing, use null.
    """

    try:
        # Generate content
        response = model.generate_content([prompt, img])
        
        # Clean response
        raw_text = response.text.replace("```json\n", "").replace(
            "\n```", "").replace("```json", "").replace("```", "").strip()

        try:
            result_data = json.loads(raw_text)
            metadata = get_image_metadata(image_path)
            
            # --- Timestamp Logic Priority ---
            # OCR → EXIF → upload_time (caller) → now_tz() (defensive)
            final_date = None
            final_time = None
            date_source = "Unknown"
            time_source = "Unknown"

            # Reference time for sanity checks and final fallback.
            # Prefer caller-provided upload_time (e.g. Telegram message.date or request start time);
            # fall back to now_tz() if caller didn't pass one.
            reference_time = upload_time or now_tz()
            # Normalize to naive (compare against naive datetimes built from OCR/EXIF strings).
            if reference_time.tzinfo is not None:
                reference_time = reference_time.replace(tzinfo=None)

            # 1. OCR (with sanity check to reject BP-monitor default-clock dates)
            ocr_date = result_data.get("date")
            ocr_time = result_data.get("time")
            ocr_date_rejected = False

            if ocr_date:
                try:
                    parsed_ocr_date = datetime.strptime(ocr_date, "%Y-%m-%d")
                    delta_days = abs((parsed_ocr_date.date() - reference_time.date()).days)
                    if delta_days <= OCR_DATE_SANITY_WINDOW_DAYS:
                        final_date = ocr_date
                        date_source = "OCR"
                    else:
                        ocr_date_rejected = True
                        logger.warning(
                            f"OCR date {ocr_date} rejected: {delta_days} days from reference "
                            f"{reference_time.date()} (window: {OCR_DATE_SANITY_WINDOW_DAYS})"
                        )
                except ValueError:
                    pass

            if ocr_time:
                try:
                    datetime.strptime(ocr_time, "%H:%M")  # Validate format
                    final_time = ocr_time
                    time_source = "OCR"
                except ValueError:
                    pass

            # 2. EXIF Data (fill gaps)
            exif_dt = None
            if not final_date or not final_time:
                exif_dt = extract_exif_datetime(metadata)

            if exif_dt:
                if not final_date:
                    final_date = exif_dt.strftime("%Y-%m-%d")
                    date_source = "EXIF"
                if not final_time:
                    final_time = exif_dt.strftime("%H:%M")
                    time_source = "EXIF"

            # 3. Upload time (caller-provided) — represents when the server received the file.
            # Preferred over now_tz() because the Gemini call may add several seconds of delay.
            if not final_date:
                final_date = reference_time.strftime("%Y-%m-%d")
                date_source = "Upload" if upload_time else "Fallback"
            if not final_time:
                final_time = reference_time.strftime("%H:%M")
                time_source = "Upload" if upload_time else "Fallback"

            source_notes = [f"Date: {date_source}", f"Time: {time_source}"]
            if ocr_date_rejected:
                source_notes.append(f"OCR-date-rejected: {ocr_date}")

            return OCRResult(
                systolic=result_data.get("systolic"),
                diastolic=result_data.get("diastolic"),
                pulse=result_data.get("pulse"),
                measurement_date=final_date,
                measurement_time=final_time,
                confidence=0.95,
                image_metadata=metadata,
                raw_response=f"Source: {', '.join(source_notes)}"
            )

        except json.JSONDecodeError:
            return OCRResult(
                error="Could not parse response as JSON",
                raw_response=raw_text,
                image_metadata=get_image_metadata(image_path)
            )

    except Exception as e:
        return OCRResult(
            error=f"Error calling Gemini API: {str(e)}",
            image_metadata=get_image_metadata(image_path)
        )
