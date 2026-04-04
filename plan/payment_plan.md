# รายละเอียดระบบชำระเงินอัตโนมัติ (SlipOK Payment System) - [Comprehensive Documentation]

## 1. ข้อมูลทั่วไป (Overview)

ระบบชำระเงินถูกออกแบบมาเพื่อรองรับการอัพเกรดเป็น **Premium Tier** โดยอัตโนมัติผ่านการตรวจสอบสลิปโอนเงิน (Thai QR Payment) โดยใช้บริการของ SlipOK API รองรับการใช้งานทั้งบน Web Frontend และ Telegram Bot

### 1.1 Subscription Plans (Bilingual)
| Plan ID | Name (TH/EN) | Price | Duration | Features |
|---------|--------------|-------|----------|----------|
| `monthly`| Premium รายเดือน / Monthly | 9 THB | 30 Days | บันทึกไม่จำกัด, สถิติขั้นสูง, Export ไม่จำกัด |
| `yearly` | Premium รายปี / Yearly | 99 THB | 365 Days | ทุกอย่างในรายเดือน + ประหยัด 9 บาท |

---

## 2. SlipOK API Reference (Technical)

### 2.1 API Endpoint
```
POST https://api.slipok.com/api/line/apikey/{BRANCH_ID}
Header: x-authorization: {SLIPOK_API_KEY}
```

### 2.2 Request Parameters (Used in Code)
| Parameter | Type | Value | Description |
|-----------|------|-------|-------------|
| `files` | Binary | Image File | รูปสลิป (JPG/PNG) |
| `log` | Boolean | `true` | เก็บข้อมูลใน SlipOK เพื่อตรวจสลิปซ้ำ |
| `amount` | Float | `expected_price` | (Optional) ให้ API ช่วยตรวจยอดเงิน |

### 2.3 Error Codes & Localized Messages
| Code | Meaning | User Message (TH) | User Message (EN) |
|------|---------|-------------------|-------------------|
| 1006 | Invalid Image | รูปภาพไม่ถูกต้อง กรุณาอัพโหลดรูปสลิปที่ชัดเจน | Invalid image. Please upload a clear slip. |
| 1007 | No QR Code | ไม่พบ QR Code ในรูปภาพ | QR Code not found in image. |
| 1008 | Not a Slip | QR Code นี้ไม่ใช่สลิปการโอนเงิน | QR Code is not a valid bank slip. |
| 1011 | Expired/NotFound| สลิปนี้หมดอายุหรือไม่พบรายการ | Slip expired or transaction not found. |
| 1012 | Duplicate Slip | **สลิปนี้เคยใช้ชำระเงินแล้ว** | **Slip already used.** |
| 1013 | Amount Mismatch | ยอดเงินในสลิปไม่ตรงกับราคาแพลน | Amount mismatch. |
| 1014 | Wrong Receiver | บัญชีผู้รับไม่ตรง กรุณาโอนไปยังบัญชีที่ระบุ | Incorrect receiving account. |

---

## 3. โครงสร้างฐานข้อมูล (Database Schema)

### 3.1 ตาราง `payments` (Implemented in `app/models.py`)
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary Key |
| `user_id` | Integer | Foreign Key เชื่อมกับตาราง `users` |
| `trans_ref` | String | เลขอ้างอิงรายการจากธนาคาร |
| `trans_ref_hash`| String | **Unique Hash** ป้องกันการใช้สลิปซ้ำในระบบเราเอง |
| `amount` | Float | ยอดเงินจริงที่โอนมา |
| `plan_type` | String | `monthly` หรือ `yearly` |
| `status` | String | `verified`, `failed`, `pending` |
| `sender_name_encrypted`| String | ชื่อผู้โอน (เก็บแบบ Encrypted) |
| `receiver_name` | String | ชื่อผู้รับเงินในสลิป |
| `verification_response`| Text | JSON Response เต็มจาก SlipOK (เพื่อการตรวจสอบย้อนหลัง) |
| `verified_at` | DateTime | วันเวลาที่ยืนยันสำเร็จ |

---

## 4. รายละเอียดการตั้งค่าระบบ (System Configuration)

ต้องกำหนดค่าในไฟล์ `.env` ดังนี้:
```bash
# SlipOK Configuration
SLIPOK_API_KEY=your_api_key_here
SLIPOK_BRANCH_ID=1

# Payment Account Info (Display to user)
PAYMENT_BANK_NAME="ธนาคารกสิกรไทย"
PAYMENT_BANK_NAME_EN="Kasikorn Bank (KBank)"
PAYMENT_BANK_CODE="004"
PAYMENT_ACCOUNT_NUMBER="xxx-x-xxxxx-x"
PAYMENT_ACCOUNT_NAME="บริษัท บีพี มอนิเตอร์ จำกัด"
PAYMENT_AMOUNT_TOLERANCE=0.50
```

---

## 5. ความปลอดภัยและ Business Logic (Security & Rules)

### 5.1 ขั้นตอนการตรวจสอบ (Verification Flow)
1. **Rate Limiting:** จำกัดการเรียกใช้ API `verify-slip` ที่ 3 ครั้งต่อนาทีต่อผู้ใช้ เพื่อป้องกัน Brute-force หรือการปั๊มสลิป
2. **File Validation:** ตรวจสอบ MIME Type (ต้องเป็นภาพ) และขนาดไฟล์ (ไม่เกิน 10MB)
3. **Double Duplicate Check:**
   - ตรวจสอบผ่าน SlipOK API (`log:true`)
   - ตรวจสอบผ่าน Database ของเราเองโดยใช้ `trans_ref_hash`
4. **Amount Matching:** ยอดเงินต้องตรงกับราคาแพลน (อนุโลมความคลาดเคลื่อนตาม `PAYMENT_AMOUNT_TOLERANCE`)
5. **Subscription Upgrade:** 
   - หากชำระสำเร็จ ระบบจะเปลี่ยน `subscription_tier` เป็น `premium`
   - หากเป็น Premium อยู่แล้ว จะ **บวกเพิ่ม (Stack)** จำนวนวันเข้าไปใน `subscription_expires_at` เดิม

---

## 6. โครงสร้างไฟล์ (File Mapping)

| ส่วนงาน | ตำแหน่งไฟล์ | หน้าที่หลัก |
|---------|------------|-----------|
| **Core Logic** | `app/services/slipok.py` | ติดต่อ SlipOK API และจัดการ Error |
| **Pricing** | `app/config/pricing.py` | เก็บราคา แพลน และข้อมูลบัญชีธนาคาร |
| **API Router** | `app/routers/payment.py` | Endpoint สำหรับ Web Frontend |
| **Bot Handler**| `app/bot/payment_handlers.py`| คำสั่ง `/upgrade` และรับสลิปผ่าน Telegram |
| **UI Component**| `frontend/app/(dashboard)/subscription/page.tsx`| หน้าจอชำระเงินบน Web |

---

## 7. รายการสิทธิประโยชน์ (Monetization Implementation)

ระบบมีการเช็คสิทธิ์ `check_premium()` ในส่วนต่างๆ ดังนี้:
- **`app/routers/bp_records.py`**:
  - Free User: ดึงข้อมูลได้สูงสุด 30 รายการล่าสุด
  - Premium User: ดึงข้อมูลได้ไม่จำกัด (Unlimited)
- **`app/routers/bp_records.py` (Stats)**:
  - Free User: แสดงค่าเฉลี่ย, สูงสุด, ต่ำสุด
  - Premium User: แสดงค่า SD, Median, MAP, Pulse Pressure และ Trend Analysis (วิเคราะห์แนวโน้ม)
