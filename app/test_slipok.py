import os
import requests
import json
from dotenv import load_dotenv

# 1. โหลดค่า config จากไฟล์ .env
load_dotenv() 

# 2. ดึงค่าตัวแปรออกมาใช้งาน
SLIPOK_API_KEY = os.getenv("SLIPOK_API_KEY")
BRANCH_ID = os.getenv("SLIPOK_BRANCH_ID", "1") # ถ้าหาไม่เจอ ให้ใช้ค่า default เป็น "1"
SLIP_IMAGE_PATH = "app/IMG_6731.JPG" # ชื่อไฟล์รูปสลิปที่จะทดสอบ

def verify_slip(image_path):
    # ตรวจสอบว่ามี API KEY หรือไม่ ก่อนเริ่มทำงาน
    if not SLIPOK_API_KEY:
        print("Error: ไม่พบ SLIPOK_API_KEY ในไฟล์ .env")
        return

    url = f"https://api.slipok.com/api/line/apikey/{BRANCH_ID}"
    
    headers = {
        "x-authorization": SLIPOK_API_KEY
    }
    
    try:
        # เปิดไฟล์รูปภาพแบบ Binary
        with open(image_path, 'rb') as image_file:
            files = {'files': image_file}
            
            print(f"กำลังส่งข้อมูลไปยัง SlipOK... (Branch: {BRANCH_ID})")
            response = requests.post(url, headers=headers, files=files)
            
            # แปลงผลลัพธ์เป็น JSON
            result = response.json()
            
            # --- ส่วนตรวจสอบความถูกต้อง ---
            if result.get('success') == True:
                data = result['data']
                print("\n✅ ตรวจสอบสลิปสำเร็จ! (Valid Slip)")
                print("-" * 30)
                print(f"ธนาคารผู้โอน: {data['sendingBank']}")
                print(f"ชื่อผู้โอน: {data['sender']['displayName']}")
                print(f"จำนวนเงิน: {data['amount']} บาท")
                print(f"วัน-เวลาโอน: {data['transDate']} {data['transTime']}")
                print(f"รหัสอ้างอิง (TransRef): {data['transRef']}")
            else:
                print("\n❌ ตรวจสอบไม่ผ่าน หรือ สลิปปลอม")
                print(f"เหตุผล: {result.get('message')}")
                
            return result

    except FileNotFoundError:
        print(f"Error: หาไฟล์รูปภาพ '{image_path}' ไม่เจอ")
    except Exception as e:
        print(f"Error: เกิดข้อผิดพลาด {e}")

if __name__ == "__main__":
    verify_slip(SLIP_IMAGE_PATH)