
import os
import json
import logging
import google.generativeai as genai
import PIL.Image
from PIL.ExifTags import TAGS
from dotenv import load_dotenv
from ..schemas import OCRResult

load_dotenv()
logger = logging.getLogger(__name__)

GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)

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


def read_blood_pressure_with_gemini(image_path: str) -> OCRResult:
    """Read blood pressure values from image using Gemini API"""
    if not GOOGLE_AI_API_KEY:
        return OCRResult(error="Google AI API key not configured")

    # Use flash model as per original code
    model = genai.GenerativeModel('gemini-2.0-flash')

    try:
        img = PIL.Image.open(image_path)
    except FileNotFoundError:
        return OCRResult(error="Image not found")
    except Exception as e:
        return OCRResult(error=f"Error opening image: {str(e)}")

    prompt = """
    จากภาพเครื่องวัดความดันนี้:
    1. บอกค่าความดัน Systolic, Diastolic และ Pulse
    2. ให้บอกค่าเวลามาด้วย แต่ถ้าไม่มีค่าเวลาให้คืนเป็นค่าว่าง
    3. บอกค่ามาในรูปแบบ JSON เท่านั้น เช่น {"systolic": 120, "diastolic": 80, "pulse": 70, "time": "10:30"}
    4. ถ้าอ่านค่าไม่ได้ให้ใส่ null สำหรับค่านั้นๆ
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

            return OCRResult(
                systolic=result_data.get("systolic"),
                diastolic=result_data.get("diastolic"),
                pulse=result_data.get("pulse"),
                time=result_data.get("time"),
                confidence=0.95,
                image_metadata=metadata
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
