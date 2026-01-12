
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
    2. Extract Date and Time IF visible on the screen.
    3. Return ONLY a JSON object: {"systolic": int, "diastolic": int, "pulse": int, "date": "YYYY-MM-DD", "time": "HH:MM"}
    4. If any value is not visible, use null.
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
            final_date = None
            final_time = None
            source_notes = []

            # 1. OCR Date key
            ocr_date = result_data.get("date")
            ocr_time = result_data.get("time")
            
            if ocr_date and ocr_time:
                try:
                    # Validating parsed values (simple check)
                    datetime.strptime(f"{ocr_date} {ocr_time}", "%Y-%m-%d %H:%M")
                    final_date = ocr_date
                    final_time = ocr_time
                    source_notes.append("OCR Screen Timestamp")
                except ValueError:
                    source_notes.append("OCR Timestamp Invalid")

            # 2. EXIF Data (if step 1 failed or partial)
            if not final_date or not final_time:
                exif_dt = extract_exif_datetime(metadata)
                if exif_dt:
                    if not final_date:
                        final_date = exif_dt.strftime("%Y-%m-%d")
                    if not final_time:
                        # Round to HH:MM for simplicity in UI
                        final_time = exif_dt.strftime("%H:%M")
                    source_notes.append("EXIF Data")
            
            # 3. File Creation Time (if still missing)
            if not final_date or not final_time:
                 try:
                    creation_time = os.path.getctime(image_path)
                    ct_dt = datetime.fromtimestamp(creation_time)
                    if not final_date:
                        final_date = ct_dt.strftime("%Y-%m-%d")
                    if not final_time:
                        final_time = ct_dt.strftime("%H:%M")
                    source_notes.append("File Creation Time")
                 except Exception:
                     pass

            # 4. Current Time (Fallback)
            if not final_date or not final_time:
                now = now_th()
                if not final_date:
                    final_date = now.strftime("%Y-%m-%d")
                if not final_time:
                    final_time = now.strftime("%H:%M")
                source_notes.append("Upload Time (Fallback)")

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
