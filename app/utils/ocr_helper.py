
import os
import json
import logging
import google.generativeai as genai
import PIL.Image
from PIL.ExifTags import TAGS
from dotenv import load_dotenv
from ..schemas import OCRResult
from datetime import datetime
from pytz import timezone

load_dotenv()
logger = logging.getLogger(__name__)

GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)

THAI_TZ = timezone("Asia/Bangkok")

def now_th():
    return datetime.now(THAI_TZ)

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

def read_blood_pressure_with_gemini(image_path: str) -> OCRResult:
    """Read blood pressure values from image using Gemini API with priority timestamp logic"""
    if not GOOGLE_AI_API_KEY:
        return OCRResult(error="Google AI API key not configured")

    model = genai.GenerativeModel('gemini-2.0-flash')

    try:
        img = PIL.Image.open(image_path)
    except FileNotFoundError:
        return OCRResult(error="Image not found")
    except Exception as e:
        return OCRResult(error=f"Error opening image: {str(e)}")

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
            
            # --- Timestamp Logic Priority (Granular) ---
            final_date = None
            final_time = None
            date_source = "Unknown"
            time_source = "Unknown"
            
            # 1. OCR (Try individual components)
            ocr_date = result_data.get("date")
            ocr_time = result_data.get("time")

            if ocr_date:
                try:
                    datetime.strptime(ocr_date, "%Y-%m-%d") # Validate format
                    final_date = ocr_date
                    date_source = "OCR"
                except ValueError:
                    pass

            if ocr_time:
                try:
                    datetime.strptime(ocr_time, "%H:%M") # Validate format
                    final_time = ocr_time
                    time_source = "OCR"
                except ValueError:
                    pass

            # 2. EXIF Data (Fill gaps)
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

            # 3. File Creation Time (Fill gaps)
            if not final_date or not final_time:
                 try:
                    creation_time = os.path.getctime(image_path)
                    ct_dt = datetime.fromtimestamp(creation_time)
                    if not final_date:
                        final_date = ct_dt.strftime("%Y-%m-%d")
                        date_source = "File Create"
                    if not final_time:
                        final_time = ct_dt.strftime("%H:%M")
                        time_source = "File Create"
                 except Exception:
                     pass

            # 4. Current Time (Fallback)
            now = now_th()
            if not final_date:
                final_date = now.strftime("%Y-%m-%d")
                date_source = "Fallback"
            if not final_time:
                final_time = now.strftime("%H:%M")
                time_source = "Fallback"

            source_notes = [f"Date: {date_source}", f"Time: {time_source}"]

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
