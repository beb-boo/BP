# Telegram Mini App — Auto-Login BP Recording

## สรุปภาพรวม

สร้าง Telegram Mini App (Web App) ที่เปิดจากปุ่มใน Telegram chat แล้ว user ได้รับการ authenticate อัตโนมัติ (ไม่ต้อง login) เพื่อเข้าหน้าบันทึกความดันโลหิตได้ทันที

หลักการทำงานเหมือน LINE LIFF — Telegram inject `initData` ที่มี user info + HMAC signature → Server verify → ออก JWT → ใช้ API ปกติได้เลย

---

## Architecture Overview

```
User กดปุ่มใน Telegram Chat
        │
        ▼
Telegram เปิด WebView → GET /telegram/bp
        │
        ▼
Frontend อ่าน window.Telegram.WebApp.initData
        │
        ▼
POST /api/v1/auth/telegram/mini-app-auth  { init_data: "..." }
        │
        ▼
Server verify HMAC-SHA256 ด้วย BOT_TOKEN
        │
        ▼
ดึง telegram_id จาก initData → หา User ใน DB (telegram_id_hash)
        │
        ▼
Return JWT access_token
        │
        ▼
Frontend เก็บ token → ใช้ API /bp-records ปกติ
```

---

## Phase 1: Backend — API Endpoint ใหม่

### 1.1 สร้างไฟล์ `app/routers/telegram_auth.py`

**Endpoint:** `POST /api/v1/auth/telegram/mini-app-auth`

**Input:**
```json
{
  "init_data": "query_id=AAH...&user=%7B%22id%22%3A123...&auth_date=1234567890&hash=abc..."
}
```

**Logic:**
1. Parse `init_data` string (URL-encoded key-value pairs)
2. Extract `hash` field
3. สร้าง `data_check_string` = sort remaining fields by key, join with `\n`
4. คำนวณ `secret_key` = HMAC-SHA256("WebAppData", BOT_TOKEN)
5. คำนวณ `computed_hash` = HMAC-SHA256(secret_key, data_check_string)
6. Compare `computed_hash` กับ `hash` (constant-time)
7. ตรวจ `auth_date` ไม่เกิน 24 ชม.
8. Parse `user` JSON → ได้ `telegram_id`
9. หา User จาก DB ด้วย `telegram_id_hash`
10. ถ้าไม่เจอ user → return error "Account not linked"
11. ถ้าเจอ → สร้าง JWT token (เหมือน login ปกติ) → return token + user info

**Output (success):**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "full_name": "สมชาย",
      "role": "patient",
      "language": "th",
      "telegram_id": 123456789
    }
  }
}
```

**Output (not linked):**
```json
{
  "status": "error",
  "message": "Telegram account not linked. Please use /start in the bot first."
}
```

**Security considerations:**
- ไม่ต้องใช้ API Key header (Mini App ไม่รู้ API key — ใช้ Telegram signature แทน)
- Rate limit: 10/minute per IP
- auth_date expiry: 86400 วินาที (24 ชม.)
- ไม่ต้องใช้ password

### 1.2 Schema ใหม่ใน `app/schemas.py`

```python
class TelegramMiniAppAuth(BaseModel):
    init_data: str = Field(..., min_length=10, description="Telegram WebApp initData string")
```

### 1.3 Register router ใน `app/main.py`

```python
from .routers import telegram_auth
app.include_router(telegram_auth.router)
```

### 1.4 ตำแหน่งไฟล์ที่ต้องแก้ไข

| ไฟล์ | Action | รายละเอียด |
|------|--------|------------|
| `app/routers/telegram_auth.py` | **สร้างใหม่** | Endpoint verify initData + issue JWT |
| `app/schemas.py` | **เพิ่ม** | `TelegramMiniAppAuth` schema |
| `app/main.py` | **แก้ไข** | Include `telegram_auth.router` |
| `app/utils/security.py` | **ไม่ต้องแก้** | ใช้ `create_access_token()` ที่มีอยู่แล้ว |
| `app/bot/services.py` | **ไม่ต้องแก้** | ใช้ `get_user_by_telegram_id()` ที่มีอยู่แล้ว |

---

## Phase 2: Frontend — Telegram Mini App Page

### 2.1 สร้าง route ใหม่: `frontend/app/telegram/bp/page.tsx`

**หลักการ:**
- หน้านี้จะถูกเปิดจาก Telegram WebView เท่านั้น
- ไม่ต้อง login — authenticate ผ่าน `initData` อัตโนมัติ
- แสดง form บันทึกความดัน (SYS/DIA/PULSE) + ปุ่มถ่ายรูป OCR
- แสดง recent records (5 รายการล่าสุด)
- UI ต้อง compact เพราะเปิดใน WebView ของ Telegram (มือถือ)

### 2.2 Flow ของหน้า

```
1. Page load → ตรวจว่ามี window.Telegram.WebApp หรือไม่
   - ไม่มี → แสดง "Please open from Telegram" + redirect link
   - มี → เรียก tg.ready(), tg.expand()

2. อ่าน initData → POST /api/v1/auth/telegram/mini-app-auth
   - สำเร็จ → เก็บ token ใน state (ไม่ต้องเก็บ cookie)
   - ไม่สำเร็จ → แสดง error + link ไป /start bot

3. แสดง UI:
   ┌─────────────────────────────┐
   │  สวัสดี สมชาย               │
   │  บันทึกความดันโลหิต          │
   ├─────────────────────────────┤
   │  [Systolic]  [Diastolic]    │
   │  [Pulse]     [Date] [Time]  │
   │  [📸 ถ่ายรูป]  [💾 บันทึก]   │
   ├─────────────────────────────┤
   │  ── สถิติ (จาก 25 รายการ) ──│
   │                             │
   │  ค่าเฉลี่ย: 130/85 (72)     │
   │  🟠 ความดันสูงระยะที่ 1      │
   │                             │
   │  ▸ Premium only:            │
   │  SD: ±8.5/±6.2  CV: 6.5%   │
   │  PP: 45  MAP: 100           │
   │  Trend: 📈 +0.5 mmHg/day   │
   │  (หรือ 🔒 Upgrade banner)   │
   ├─────────────────────────────┤
   │  ── 5 รายการล่าสุด ──       │
   │  31/03 08:00  120/80 (72)   │
   │  30/03 07:30  130/85 (75)   │
   │  ...                        │
   └─────────────────────────────┘

   **Stats section logic:**
   - เรียก `GET /api/v1/stats/summary?days=30` (ใช้ JWT จาก mini-app-auth)
   - Response มี `is_premium` flag → ใช้กำหนดว่าแสดงอะไร
   - **Free tier**: แสดง avg SBP/DBP/Pulse + Classification (พร้อม emoji สี)
   - **Premium tier**: เพิ่ม SD, CV, Pulse Pressure, MAP, Trend (slope + direction)
   - **Free upgrade prompt**: แสดง 🔒 พร้อมข้อความ "ปลดล็อคการวิเคราะห์ขั้นสูง" + link ไป /subscription
   - Classification emoji: 🟢 normal, 🟡 elevated, 🟠 stage_1, 🔴 stage_2, 🚨 crisis
   - Trend emoji: 📈 increasing, 📉 decreasing, ➡️ stable

4. บันทึกสำเร็จ → แสดง success toast
   → tg.showAlert("บันทึกเรียบร้อย!")
   → tg.close() (ปิด WebView กลับไป chat) [optional]
```

### 2.3 Telegram WebApp SDK

ใช้ script: `<script src="https://telegram.org/js/telegram-web-app.js"></script>`

ต้องเพิ่มใน `frontend/app/telegram/layout.tsx` หรือใช้ dynamic import

Functions ที่ใช้:
- `Telegram.WebApp.ready()` — บอก Telegram ว่า app พร้อม
- `Telegram.WebApp.expand()` — ขยาย WebView เต็มจอ
- `Telegram.WebApp.initData` — string สำหรับ verify
- `Telegram.WebApp.initDataUnsafe.user` — user info (ใช้แสดง UI ก่อน verify)
- `Telegram.WebApp.MainButton` — ปุ่มหลักของ Telegram (optional)
- `Telegram.WebApp.showAlert()` — native alert ของ Telegram
- `Telegram.WebApp.close()` — ปิด WebView
- `Telegram.WebApp.themeParams` — สี theme ของ user

### 2.4 ตำแหน่งไฟล์ที่ต้องสร้าง/แก้ไข

| ไฟล์ | Action | รายละเอียด |
|------|--------|------------|
| `frontend/app/telegram/bp/page.tsx` | **สร้างใหม่** | หน้าบันทึก BP ใน Mini App |
| `frontend/app/telegram/layout.tsx` | **สร้างใหม่** | Layout สำหรับ Telegram pages (ใส่ SDK script, ไม่มี navigation bar) |
| `frontend/lib/telegram.ts` | **สร้างใหม่** | Helper functions สำหรับ Telegram WebApp API |
| `frontend/next.config.ts` | **อาจต้องแก้** | เพิ่ม CSP header อนุญาต telegram.org script |
| `frontend/proxy.ts` | **อาจต้องแก้** | ยกเว้น /telegram/* จาก auth redirect |

### 2.5 สิ่งที่ต้องระวัง

1. **ไม่ใช้ Cookie** — Mini App token เก็บใน React state / sessionStorage เท่านั้น
2. **ไม่ใช้ API Key** — ใช้ Telegram initData เป็น credential แทน
3. **axios instance แยก** — สร้าง `telegramApi` instance ที่ไม่ attach API Key header แต่ attach JWT token ที่ได้จาก mini-app-auth
4. **Responsive** — UI ต้อง mobile-first เพราะ Telegram WebView เปิดในมือถือ
5. **Theme** — ใช้ `Telegram.WebApp.themeParams` เพื่อให้ UI match กับ theme ของ Telegram user (dark/light)
6. **Stats API call** — เรียก `/api/v1/stats/summary?days=30` ด้วย JWT ที่ได้จาก mini-app-auth เพื่อแสดงสถิติ โดย response มี `is_premium` flag ที่กำหนดว่าแสดง advanced stats หรือไม่
7. **API Key middleware** — ต้องตรวจสอบว่า API endpoints (bp-records, stats) ยอมรับ JWT-only auth จาก Mini App โดยไม่ต้องมี X-API-Key header หรือต้องปรับ middleware

---

## Phase 3: Bot — ส่งปุ่ม Web App

### 3.1 แก้ไข `app/bot/handlers.py`

เพิ่มปุ่ม Web App ใน 2 จุด:

**A) หลัง login สำเร็จ (welcome back message):**
```python
from telegram import WebAppInfo

webapp_url = os.getenv("TELEGRAM_WEBAPP_URL", "https://your-frontend.com/telegram/bp")

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📝 บันทึกความดัน", web_app=WebAppInfo(url=webapp_url))],
    [InlineKeyboardButton("📊 สถิติ", callback_data="quick_stats")]
])
```

**B) Command ใหม่ `/bp`:**
```python
async def bp_command(update, context):
    """Open BP recording Mini App."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return
    lang = user.language or "en"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            get_text("btn_record_bp", lang),
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    await update.message.reply_text(
        get_text("bp_webapp_prompt", lang),
        reply_markup=keyboard
    )
```

### 3.2 เพิ่ม locales ใน `app/bot/locales.py`

```python
"btn_record_bp": {
    "en": "📝 Record Blood Pressure",
    "th": "📝 บันทึกความดัน"
},
"bp_webapp_prompt": {
    "en": "Tap the button below to record your blood pressure:",
    "th": "กดปุ่มด้านล่างเพื่อบันทึกความดัน:"
}
```

### 3.3 Register handler ใน `app/bot/main.py`

```python
from .handlers import bp_command
application.add_handler(CommandHandler("bp", bp_command))
```

### 3.4 ตำแหน่งไฟล์ที่ต้องแก้ไข

| ไฟล์ | Action | รายละเอียด |
|------|--------|------------|
| `app/bot/handlers.py` | **แก้ไข** | เพิ่ม `bp_command()`, แก้ welcome message |
| `app/bot/main.py` | **แก้ไข** | Register `/bp` command |
| `app/bot/locales.py` | **แก้ไข** | เพิ่ม strings สำหรับ Mini App UI |

---

## Phase 4: Environment & Config

### 4.1 Environment Variables ใหม่

```env
# .env (backend)
TELEGRAM_WEBAPP_URL=https://your-frontend.vercel.app/telegram/bp
# BOT_TOKEN ใช้อันเดิมที่มีอยู่แล้ว (TELEGRAM_BOT_TOKEN)

# .env.local (frontend)
NEXT_PUBLIC_TELEGRAM_WEBAPP=true
```

### 4.2 BotFather Configuration

ต้องตั้งค่า Web App URL ใน BotFather:
```
/mybots → เลือก Bot → Bot Settings → Menu Button
  URL: https://your-frontend.vercel.app/telegram/bp
  Text: บันทึกความดัน
```

### 4.3 Vercel / Deployment

- Frontend domain ต้องเป็น **HTTPS** (Telegram บังคับ)
- ต้อง whitelist Telegram domain ใน CSP (ถ้ามี)
- CORS: เพิ่ม telegram origin ถ้าจำเป็น (ปกติไม่ต้อง เพราะ WebView ใช้ URL ตรง)

---

## สรุปไฟล์ทั้งหมดที่ต้องทำ

### สร้างใหม่ (4 ไฟล์)
1. `app/routers/telegram_auth.py` — Backend endpoint verify initData
2. `frontend/app/telegram/bp/page.tsx` — Mini App หน้าบันทึก BP
3. `frontend/app/telegram/layout.tsx` — Layout สำหรับ Telegram pages
4. `frontend/lib/telegram.ts` — Telegram WebApp helper functions

### แก้ไข (6 ไฟล์)
5. `app/schemas.py` — เพิ่ม `TelegramMiniAppAuth`
6. `app/main.py` — Include `telegram_auth.router`
7. `app/bot/handlers.py` — เพิ่ม `bp_command`, แก้ welcome
8. `app/bot/main.py` — Register `/bp` command
9. `app/bot/locales.py` — เพิ่ม locale strings
10. `frontend/proxy.ts` — ยกเว้น `/telegram/*` จาก auth guard

### ไม่ต้องแก้ (ใช้ของเดิม)
- `app/utils/security.py` — ใช้ `create_access_token()` เดิม
- `app/bot/services.py` — ใช้ `get_user_by_telegram_id()` เดิม
- `app/routers/bp_records.py` — ใช้ API เดิม (POST /bp-records, GET /bp-records)
- `frontend/lib/api.ts` — ใช้ base URL เดิม (สร้าง instance แยกสำหรับ Mini App)

---

## ลำดับการพัฒนา (สำหรับ Claude Code)

### Step 1: Backend endpoint (ทำก่อน — ทดสอบได้อิสระ)
1. สร้าง `app/routers/telegram_auth.py`
2. เพิ่ม schema ใน `app/schemas.py`
3. Register ใน `app/main.py`
4. เขียน unit test verify HMAC logic

### Step 2: Frontend Mini App page
1. สร้าง `frontend/lib/telegram.ts`
2. สร้าง `frontend/app/telegram/layout.tsx`
3. สร้าง `frontend/app/telegram/bp/page.tsx`
4. แก้ `frontend/proxy.ts` ยกเว้น auth

### Step 3: Bot integration
1. แก้ `app/bot/handlers.py` — เพิ่ม `/bp` command + แก้ welcome
2. แก้ `app/bot/main.py` — register handler
3. แก้ `app/bot/locales.py` — เพิ่ม strings

### Step 4: Testing & Config
1. ตั้งค่า BotFather Menu Button
2. ทดสอบ end-to-end ใน Telegram
3. ทดสอบ error cases (ยังไม่ link account, expired initData)

---

## Edge Cases ที่ต้อง Handle

1. **User ยังไม่ link Telegram** → แสดง "กรุณาใช้ /start ก่อน" + deep link ไป bot
2. **initData expired (> 24 ชม.)** → แสดง error + ปุ่มกดเปิดใหม่
3. **initData signature ไม่ถูก** → แสดง error อย่าเปิดเผยรายละเอียด
4. **User เปิดจากเบราว์เซอร์ปกติ (ไม่ใช่ Telegram)** → แสดง "กรุณาเปิดจาก Telegram"
5. **Network error** → retry logic + offline indicator
6. **Account ถูก deactivate** → แสดง error ตาม API response
7. **Duplicate record** → API จะ return duplicate flag (มีอยู่แล้ว)

---

## TypeScript Types สำหรับ Frontend

```typescript
// frontend/lib/telegram.ts

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
}

interface TelegramWebApp {
  ready(): void;
  expand(): void;
  close(): void;
  showAlert(message: string, callback?: () => void): void;
  showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: TelegramUser;
    auth_date: number;
    hash: string;
  };
  themeParams: {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    secondary_bg_color?: string;
  };
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
    showProgress(leaveActive?: boolean): void;
    hideProgress(): void;
  };
  BackButton: {
    isVisible: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  colorScheme: 'light' | 'dark';
  viewportHeight: number;
  viewportStableHeight: number;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}
```

---

## หมายเหตุ

- **ไม่ต้องแก้ Database schema** — ใช้ field `telegram_id_hash` ที่มีอยู่แล้ว
- **Security เทียบเท่า LINE LIFF** — Telegram sign initData ด้วย Bot Token, ปลอมไม่ได้
- **ใช้ API เดิมทั้งหมด** สำหรับ CRUD bp_records — แค่เพิ่มช่องทาง auth ใหม่
- **Backward compatible** — ไม่กระทบ web login, mobile login, หรือ bot commands เดิม

---

## Review: ปัญหาที่ตรวจพบและข้อควรแก้ไข

### ✅ สิ่งที่ถูกต้องแล้ว
- Architecture flow (initData → HMAC verify → JWT) ถูกต้อง
- ใช้ existing API endpoints ไม่สร้างใหม่โดยไม่จำเป็น
- Security model เหมาะสม (constant-time compare, auth_date expiry)
- File structure สอดคล้องกับ Next.js app directory pattern

### ⚠️ สิ่งที่ต้องปรับ/เพิ่ม

1. **Stats section ขาดจาก UI mockup (แก้แล้ว)**
   - เดิมมีแค่ form + 5 รายการล่าสุด ไม่มีสถิติ
   - เพิ่มแล้ว: stats section ระหว่าง form กับ recent entries โดย respect Free/Premium tier

2. **API Key bypass สำหรับ Mini App**
   - Plan บอก "ไม่ต้องใช้ API Key" แต่ backend `app/main.py` มี API key check middleware
   - ต้องแน่ใจว่า `/api/v1/auth/telegram/mini-app-auth` ยกเว้นจาก API key check
   - สำหรับ API calls อื่น (bp-records, stats) ที่ใช้ JWT จาก mini-app-auth → ต้องตรวจสอบว่า JWT เพียงพอ หรือยังต้องมี API key ด้วย
   - **แนวทาง**: สร้าง axios instance แยกที่ส่ง JWT header แต่ไม่ส่ง API key หรือ backend ยกเว้น API key check เมื่อมี valid JWT จาก telegram auth

3. **`check_premium()` กับ Mini App**
   - Stats endpoint ใช้ `check_premium(current_user)` ซึ่งรองรับ `PREMIUM_BYPASS_USERS` อยู่แล้ว
   - Mini App ใช้ JWT เดียวกัน → `get_current_user` dependency จะทำงานปกติ → ไม่มีปัญหา

4. **Telegram WebApp SDK version**
   - ควรระบุว่าใช้ Bot API version ไหน (Telegram Web App API v6.x+)
   - `themeParams` มี fields ใหม่ใน v6.9+: `header_bg_color`, `accent_text_color`, `section_bg_color` ฯลฯ
   - ควรพิจารณาใช้ `@vkruglikov/react-telegram-web-app` package แทน raw SDK สำหรับ React integration

5. **OCR (ถ่ายรูป) ใน Mini App**
   - Plan กล่าวถึงปุ่ม 📸 แต่ไม่ได้ detail flow
   - Telegram WebView รองรับ file input / camera access แต่ต้องทดสอบว่า OCR endpoint `/api/v1/ocr/extract` ทำงานได้กับ Mini App auth (ไม่มี API key)

6. **proxy.ts exemption**
   - Plan บอก "ยกเว้น /telegram/* จาก auth redirect" → ต้องตรวจสอบ pattern matching ใน proxy.ts ปัจจุบัน

7. **CORS สำหรับ Mini App**
   - Telegram WebView เปิด URL ตรง (ไม่ใช่ cross-origin fetch) → CORS ไม่เป็นปัญหาสำหรับ page load
   - แต่ API calls จาก Mini App page ไปที่ backend ต้องผ่าน CORS → frontend rewrites ใน next.config.ts จะ handle ได้ถ้า Mini App อยู่บน frontend domain เดียวกัน

8. **Vercel Deployment Consideration**
   - `telegram_auth.py` — router ใหม่จะถูก import ใน `app/main.py` → Vercel จะ build ได้ปกติ (ไม่มี conditional import ที่ทำให้ static scan fail เหมือนปัญหาที่เคยเจอ)
   - ตรวจสอบว่า `hmac`, `hashlib` อยู่ใน Python stdlib → ไม่ต้องเพิ่ม dependency
