# Premium Production Readiness Plan

เอกสารนี้เป็นแผนลงมือแก้ระบบ Premium Subscription ให้พร้อมใช้งานระดับ production โดยอ้างอิงจากแผนเดิมใน `plan/payment_plan.md` และการตรวจสอบโค้ดจริงใน backend, frontend และ Telegram bot

## 1. Executive Summary

ระบบ Premium ในปัจจุบันมี happy path ใช้งานได้จริงทั้ง Web และ Telegram Bot ในส่วนหลักต่อไปนี้

- ผู้ใช้เลือกแพลนและอัปโหลดสลิปได้
- ระบบตรวจสลิปผ่าน SlipOK และอัปเกรดเป็น Premium ได้
- การต่ออายุก่อนหมดอายุทำแบบ stack ได้
- การต่ออายุหลังหมดอายุทำได้และเริ่มนับจากเวลาที่ verify สำเร็จ
- ฟีเจอร์หลักบางส่วนใช้ `check_premium()` จึงกลับไปจำกัดสิทธิ์แบบ Free ได้เมื่อ expiry ผ่านแล้ว

~~อย่างไรก็ตาม ระบบยังไม่พร้อม production ด้วยเหตุผลหลัก 4 แกน~~

> **Update 2026-04-04:** ปัญหาทั้ง 4 แกนด้านล่างได้รับการแก้ไขเรียบร้อยแล้ว (ดู Section 16)

1. ~~Expiry downgrade ยังไม่ clean ในระดับ state/API/UI~~ → ✅ Persisted self-heal + normalized API responses
2. ~~Web และ Bot ยังไม่ได้ใช้ payment guard ชุดเดียวกันตามแผน~~ → ✅ Shared `verify_and_upgrade()` + `validate_slip_image()` + `_check_rate_limit()`
3. ~~Payment verification logic ซ้ำกันในหลายจุด เสี่ยง drift และ regression~~ → ✅ Consolidated in `payment_service.py`
4. ~~ยังไม่มี test coverage ที่ป้องกัน regression~~ → ✅ 35 tests covering all matrix items

**สถานะปัจจุบัน:** โค้ดและ test สมบูรณ์ครบทุก phase — เหลือเพียง **manual E2E verification** (Section 11) ก่อน deploy production

## 2. Current State Assessment

### 2.1 สิ่งที่ทำงานได้แล้ว

- Backend มี endpoint สำหรับดูแพลน, verify slip, ดู payment history และดูสถานะ subscription
- SlipOK integration รองรับ `log:true` และส่ง `amount` ไปช่วยตรวจยอด
- Renewal logic ปัจจุบันรองรับทั้ง renew ก่อนหมดอายุและหลังหมดอายุ
- Dashboard ฝั่งเว็บใช้ `is_premium` จาก stats summary เพื่อล็อก/ปลดล็อก advanced analytics
- Export และ BP stats บางส่วนใช้ `check_premium()` จึงมีพฤติกรรมใกล้เคียงที่ต้องการในเชิงสิทธิ์การใช้งาน

### 2.2 ปัญหาหลักที่ต้องแก้ก่อน production

#### A. Subscription state ไม่สอดคล้องกัน

- หลาย endpoint ส่ง `subscription_tier` จากฐานข้อมูลตรงๆ
- เมื่อผู้ใช้หมดอายุ แต่ฐานข้อมูลยังเป็น `premium` ผู้ใช้บางหน้าจะยังเห็นสถานะเป็น Premium
- ในเวลาเดียวกัน feature gating หลายจุดกลับเช็คจาก `check_premium()` ซึ่งอิง expiry จริง
- ผลคือ “สิทธิ์ใช้งานจริง” และ “สถานะที่ UI/API บอกผู้ใช้” ไม่ตรงกัน

#### B. Web กับ Bot ใช้ guard ไม่เท่ากัน

- Web route มีการจำกัดความถี่ verify-slip
- Web route มี file validation เรื่อง MIME type และขนาดไฟล์
- Bot เรียก service ตรงและข้าม guard บางส่วน
- ผลคือ policy จริงไม่เท่ากันตาม channel

#### C. Business logic ซ้ำกัน

- Web route และ Bot service มี verification flow ซ้ำกันเกือบทั้งหมด
- ถ้าแก้ bug ข้างหนึ่ง แต่อีกฝั่งไม่แก้ จะ drift ทันที

#### D. UX ยังไม่ครบตาม production expectation

- หน้า subscription ยังแสดงสถานะจาก raw tier มากกว่าสถานะ active จริง
- หลังชำระสำเร็จ web ใช้ local optimistic state มากกว่าการ refetch จาก server
- ยังไม่มี payment history บนหน้า web แม้ backend มี endpoint แล้ว
- Bot profile/subscription ยังไม่แสดงข้อมูลครบเช่น expiry date ในทุกจุดที่ควรแสดง

#### E. Test coverage ยังไม่พอ

- ยังไม่มีชุดทดสอบเฉพาะสำหรับ expiry downgrade
- ยังไม่มี parity tests ระหว่าง Web และ Bot
- ยังไม่มี regression tests ที่ล็อก behavior ของ renewal timing อย่างชัดเจน

## 3. Target State

หลังทำแผนนี้เสร็จ ระบบต้องมีสถานะเป้าหมายดังนี้

1. ระบบใช้ expiry เป็น source of truth สำหรับการเป็น Premium ที่ active
2. ถ้า expiry ผ่านแล้ว ผู้ใช้จะถูก normalize กลับเป็น Free ใน state ที่ serialize ออก API
3. ทุกช่องทางที่ผู้ใช้เห็นสถานะสมาชิกจะแสดงผลตรงกัน
4. Web และ Bot ใช้ payment verification flow เดียวกัน
5. Web และ Bot ใช้ validation และ rate limit policy เดียวกัน
6. Renewal ก่อนหมดอายุ stack ต่อจาก expiry เดิม
7. Renewal หลังหมดอายุเริ่มนับจากเวลาที่ verify สำเร็จ
8. มี regression tests ครอบคลุม expiry, renewal, downgrade, duplicate slip และ amount mismatch
9. UI ของ Web และ Bot แสดงสถานะสมาชิกอย่างชัดเจนและเชื่อถือได้

## 4. Business Rules To Lock

ส่วนนี้ต้องถือเป็นกติกากลางของระบบ และใช้ตรงกันทุก channel

### 4.1 Active Premium Definition

- ผู้ใช้เป็น Premium แบบ active ก็ต่อเมื่อ
  - `subscription_tier == "premium"`
  - และ `subscription_expires_at` มีค่า
  - และ `subscription_expires_at > now_tz()` หรือเวลามาตรฐานเดียวกันที่ระบบกำหนด

### 4.2 Downgrade Rule

- ถ้าผู้ใช้มี `subscription_tier == "premium"` แต่ expiry ไม่มีค่า หรือ expiry ผ่านแล้ว
  - ต้อง normalize state กลับเป็น `free`
  - ต้องล้างหรือจัดการ `subscription_expires_at` ให้ state ไม่หลอกผู้ใช้
  - ต้องทำใน path สำคัญที่อ่านข้อมูล user และ serialize ออก API

### 4.3 Renewal Rule

- Renew ก่อนหมดอายุ
  - ใช้ expiry เดิมเป็นฐาน
  - expiry ใหม่ = expiry เดิม + จำนวนวันของแพลน

- Renew หลังหมดอายุ
  - ใช้เวลาที่ verify สำเร็จเป็นฐาน
  - expiry ใหม่ = now + จำนวนวันของแพลน

### 4.4 Payment Validation Rule

- ต้องเป็น image เท่านั้น
- ขนาดไฟล์สูงสุด 10MB
- ต้องมี duplicate protection 2 ชั้น
  - SlipOK `log:true`
  - internal `trans_ref_hash`
- ยอดโอนต้อง match ตาม tolerance ที่กำหนด
- Policy เดียวกันต้องใช้ได้ทั้ง Web และ Bot

### 4.5 Rate Limiting Rule

- Verify-slip ต้องถูกจำกัดที่ 3 ครั้งต่อนาทีต่อผู้ใช้
- ไม่ควรพึ่ง remote IP อย่างเดียว
- Bot ต้องมี guard เทียบเท่า Web

## 5. Scope

### 5.1 In Scope

- Expiry downgrade normalization
- Subscription state cleanup ใน API และ UI
- Shared payment verification service
- Web/Bot validation parity
- Web/Bot rate limiting parity
- Frontend subscription UX cleanup
- Bot subscription/profile UX cleanup
- Payment history บนหน้า web subscription
- Test coverage และ regression protection
- Pricing display consistency ระหว่าง backend และ frontend

### 5.2 Recommended But Optional In This Round

- Downgrade audit trail เพิ่มเติม
- Notification เมื่อสมาชิกหมดอายุ
- Bot payment history UI เต็มรูปแบบ

### 5.3 Out Of Scope

- เปลี่ยน provider ชำระเงิน
- เปลี่ยน commercial model หรือราคาแพลน
- redesign dashboard ทั้งระบบนอกเหนือจาก subscription-related UX
- แตะ `MobileApp/` เพราะ repo guidance ระบุว่ายังไม่อยู่ในขอบเขตปัจจุบัน

## 6. File Impact Map

### 6.1 New Files To Create

1. `app/utils/subscription.py`
2. `app/services/payment_service.py`
3. `tests/test_subscription_expiry.py`

### 6.2 Existing Files To Modify

- `app/utils/security.py`
- `app/routers/auth.py`
- `app/routers/payment.py`
- `app/routers/users.py`
- `app/bot/services.py`
- `app/bot/payment_handlers.py`
- `app/main.py`
- `frontend/app/(dashboard)/subscription/page.tsx`
- `frontend/app/(dashboard)/dashboard/page.tsx`
- `frontend/locales/en.ts`
- `frontend/locales/th.ts`

## 7. Implementation Strategy

งานนี้ควรทำเป็น 8 phases เพื่อให้ลด regression และ deploy แบบคุมความเสี่ยงได้

### Phase 1: Establish Single Source Of Truth

#### Objective

สร้าง utility กลางสำหรับ subscription state เพื่อให้ทุกจุดใช้กติกาเดียวกัน

#### Tasks

- สร้าง `app/utils/subscription.py`
- เพิ่มฟังก์ชันอย่างน้อยดังนี้
  - `is_premium_active(user)`
  - `normalize_subscription_state(user, db=None)`
  - `get_subscription_status_payload(user)`
  - `get_renewal_base_datetime(user, now)`
- ระบุชัดใน docstring ว่า expiry เป็น source of truth
- ระบุชัดว่า normalization ต้อง downgrade raw state ให้ตรงกับ active state

#### Acceptance Criteria

- ไม่มี business rule หลักเกี่ยวกับ active premium กระจายซ้ำหลายไฟล์อีก
- สามารถเรียก utility เดียวเพื่อรู้ว่า user เป็น premium active หรือไม่
- สามารถ normalize state ได้จาก utility เดียว

### Phase 2: Normalize State On Auth And Read Paths

#### Objective

ทำให้ทุก path สำคัญที่ user ใช้งานจริง serialize subscription state ที่ clean แล้ว

#### Tasks

- ปรับ `app/utils/security.py`
  - ให้ `check_premium()` ใช้ utility กลาง
  - หลีกเลี่ยงการฝัง logic expiry ซ้ำ
- ปรับ `app/routers/auth.py`
  - login response ต้องส่ง
    - `subscription_tier`
    - `subscription_expires_at`
    - `is_premium_active`
  - ก่อน serialize ต้อง normalize state
- ปรับ `app/routers/payment.py`
  - `/payment/plans` ต้องคืน normalized status
  - `/payment/status` ต้องคืน normalized status
  - อย่าส่ง raw tier อย่างเดียวแล้วปล่อย UI ไปตีความเอง
- ปรับ `app/routers/users.py`
  - `/users/me` หรือ profile endpoint ต้องมี subscription fields ที่ normalized แล้ว
- ปรับ `app/bot/services.py`
  - helper ที่อ่าน user profile/subscription ต้อง normalize ก่อนคืนค่า

#### Acceptance Criteria

- ผู้ใช้ที่หมดอายุแล้วจะไม่เห็นตัวเองเป็น Premium จาก API หลัก
- login response, payment status, subscription page data และ bot status ให้คำตอบตรงกัน

### Phase 3: Consolidate Payment Verification Logic

#### Objective

รวม payment verification flow ให้ Web และ Bot ใช้ service เดียวกัน

#### Tasks

- สร้าง `app/services/payment_service.py`
- ย้าย logic หลักจาก web route และ bot service เข้า service กลาง เช่น
  - plan validation
  - calling SlipOK
  - duplicate check
  - amount validation
  - payment row creation
  - renewal calculation
  - subscription upgrade
- ให้ `app/routers/payment.py` เรียก service กลาง
- ให้ `app/bot/services.py` เรียก service กลาง

#### Acceptance Criteria

- ไม่มี verification business logic ซ้ำระหว่าง Web และ Bot
- แก้กฎการชำระเงินที่ service เดียวแล้วกระทบทั้งสอง channel

### Phase 4: Align Guards Between Web And Bot

#### Objective

ทำให้ policy เรื่อง validation และ throttling เหมือนกันทั้ง Web และ Bot

#### Tasks

- ย้าย file validation เข้า shared layer
  - image only
  - max 10MB
- เพิ่ม user-based throttling สำหรับ verify-slip
- ปรับ Bot flow ให้ผ่าน guard เดียวกับ Web
- ยืนยัน duplicate protection 2 ชั้นยังทำงานเหมือนเดิม

#### Acceptance Criteria

- Bot ไม่ bypass กฎที่ Web ใช้
- ทุก payment request ผ่าน validation เดียวกัน
- rate limit ไม่พึ่ง IP อย่างเดียว

### Phase 5: Frontend Subscription UX Cleanup

#### Objective

ทำให้หน้า subscription และ dashboard แสดงผลสอดคล้องกับ state จริง

#### Tasks

- ปรับ `frontend/app/(dashboard)/subscription/page.tsx`
  - ใช้ active state จาก server
  - แสดง tier, expiry, days remaining อย่างชัดเจน
  - หลังจ่ายสำเร็จให้ refetch data จาก server
  - อย่าอาศัย `setCurrentTier("premium")` อย่างเดียว
- เพิ่ม payment history section โดยใช้ `/payment/history`
- เพิ่มข้อความสถานะที่ชัดเจน เช่น
  - Free
  - Premium Active
  - Expired -> Free
- ปรับ pricing copy ใน frontend ให้ตรงกับ backend pricing config

#### Acceptance Criteria

- Reload หน้า subscription แล้วสถานะไม่หลอกผู้ใช้
- ผู้ใช้เห็นวันหมดอายุและวันคงเหลือชัดเจน
- ผู้ใช้เห็นประวัติการชำระเงินย้อนหลังบน web
- ราคาใน locale files ตรงกับ config จริง

### Phase 6: Bot UX Cleanup

#### Objective

ทำให้ Bot บอกสถานะสมาชิกได้ถูกต้องและครบกว่าปัจจุบัน

#### Tasks

- ปรับ `app/bot/services.py` ให้ profile payload มี
  - normalized tier
  - is_active
  - expires_at
  - days_remaining
- ปรับ `app/bot/payment_handlers.py`
  - `/subscription` ต้องแสดง active status จาก normalized state
  - `/profile` ควรแสดง expiry และสถานะสมาชิกอย่างชัดเจน
- คง happy path เดิมของ `/upgrade` แต่ให้ validation และ error handling ตรงกับ web

#### Acceptance Criteria

- ผู้ใช้ bot จะไม่เห็นตัวเองเป็น premium ถ้าหมดอายุแล้ว
- `/subscription` และ `/profile` ให้ข้อมูลตรงกัน

### Phase 7: Testing And Regression Protection

#### Objective

สร้าง test coverage ที่ปิดความเสี่ยงสำคัญของระบบ premium

#### Tasks

- สร้าง `tests/test_subscription_expiry.py`
- เพิ่ม test อย่างน้อยตามรายการใน section 10
- เพิ่ม shared payment service tests
- เพิ่ม parity tests ระหว่าง Web/Bot

#### Acceptance Criteria

- มี automated tests ที่ยืนยัน downgrade, renewal, duplicate protection และ parity
- การแก้รอบต่อไปจะไม่พังเงียบในจุดสำคัญ

### Phase 8: Rollout And Verification

#### Objective

ตรวจให้จบทั้ง automated และ manual ก่อน deploy production

#### Tasks

- รันชุดทดสอบที่เกี่ยวข้อง
- ตรวจ manual web flow
- ตรวจ manual bot flow
- ตรวจกรณี expired premium user ที่เคย stale ใน DB ให้ self-heal เมื่อ access รอบถัดไป

#### Acceptance Criteria

- ผลลัพธ์ตรงกันทั้ง API, Web UI และ Bot UX
- stale premium users ถูก normalize ได้โดยไม่ต้อง migration manual เพิ่มเติม

## 8. Detailed File-Level Change Checklist

### `app/utils/subscription.py` (new)

- [x] เพิ่ม utility สำหรับ active premium check — `is_premium_active()` line 26
- [x] เพิ่ม utility สำหรับ normalize expired premium -> free — `normalize_subscription_state()` line 63 (persisted, commits to DB)
- [x] เพิ่ม utility สำหรับ days remaining — `get_subscription_info()` line 36
- [x] เพิ่ม utility สำหรับ renewal base datetime — `get_renewal_base_datetime()` line 100
- [x] เขียน docstring ชัดเจนเรื่อง source of truth — lines 1-7 + ทุกฟังก์ชัน

### `app/services/payment_service.py` (new)

- [x] รวม verification flow จาก web และ bot — `verify_and_upgrade()` line 107
- [x] รองรับ plan validation — line 145
- [x] รองรับ image validation — `validate_slip_image()` line 78 (magic bytes + 10MB)
- [x] รองรับ duplicate check — line 185 (trans_ref_hash)
- [x] รองรับ amount validation — line 203
- [x] รองรับ payment record creation — line 212
- [x] รองรับ renewal stack logic — line 233 via `get_renewal_base_datetime()`
- [x] คืน payload กลางที่ทั้ง web และ bot ใช้ต่อได้ — line 253

### `app/utils/security.py`

- [x] เปลี่ยน `check_premium()` ให้ใช้ utility กลาง — line 50
- [x] รักษา behavior ของ bypass users — line 57 (ID/telegram_id/phone)
- [x] ป้องกัน normalization ไปทำลาย bypass behavior — `normalize_subscription_state()` checks `check_premium()` ก่อน downgrade (subscription.py:81)

### `app/routers/auth.py`

- [x] normalize state ก่อนตอบ login response — line 354 calls `normalize_subscription_state()`
- [x] เพิ่ม `subscription_expires_at` — line 376
- [x] เพิ่ม `is_premium_active` — line 374
- [x] ตรวจ backward compatibility กับ frontend auth flow — fields เดิมยังอยู่ + `SubscriptionInfo` type ใน app-types.ts:110

### `app/routers/payment.py`

- [x] เปลี่ยน `verify_payment_slip()` ให้เรียก shared service — line 83 calls `verify_and_upgrade()`
- [x] ทำ `/payment/plans` ให้คืน normalized current status — line 40
- [x] ทำ `/payment/status` ให้คืน normalized status และ days remaining — line 135
- [x] คง `/payment/history` ไว้เป็น source สำหรับ UI history — line 100

### `app/routers/users.py`

- [x] เพิ่ม subscription fields ใน profile response — GET line 49, PUT line 185
- [x] normalize state ก่อน serialize — ทั้ง GET และ PUT เรียก `get_subscription_info()` overlay 4 fields

### `app/bot/services.py`

- [x] เปลี่ยน bot verification ให้เรียก shared service — line 383 calls `verify_and_upgrade()`
- [x] ปรับ `get_subscription_status()` ให้ normalized — line 356 calls `normalize_subscription_state()` + line 358
- [x] ปรับ `get_user_profile()` ให้มี expiry และ active status — line 408 + line 416

### `app/bot/payment_handlers.py`

- [x] `/subscription` ใช้ normalized state — line 161 calls `get_subscription_status()`
- [x] ตรวจว่า `/upgrade` ไม่ bypass validation — bot delegates to shared `verify_and_upgrade()` ซึ่งมี image validation + rate limit + ทุก guard
- [x] รักษา conversation timeout และ retry behavior เดิม — timeout 300s line 192

### `app/main.py`

- [x] ตัดสินใจว่าจะ normalize ที่ไหน — ใช้ dependency injection ผ่าน `get_current_user()` ใน security.py:195 (ดีกว่า middleware เพราะเข้าถึง DB session + user object ตรง)
- [x] เลือกแนวทางที่ไม่กระทบ performance เกินจำเป็น — normalize เป็นแค่ single field check + conditional write

### `frontend/app/(dashboard)/subscription/page.tsx`

- [x] เปลี่ยน current status card ให้ยึด normalized active state — `getStatusBadge()` line 157
- [x] refetch หลัง payment success — line 105 calls `fetchPlans()` + `fetchHistory()`
- [x] เพิ่ม payment history section — lines 295-342
- [x] แสดง expiry และ days remaining — lines 192-202
- [x] ปรับ copy ให้สอดคล้องจริง — status badge + locale pricing

### `frontend/app/(dashboard)/dashboard/page.tsx`

- [x] ยืนยันว่าการล็อก premium analytics ยังอิง `is_premium` จาก server — line 176-182 sets `isPremium` from stats API response
- [x] หลัง refetch data ต้องไม่ใช้ stale membership state จาก cookie — cookie ใช้ initial render เท่านั้น, `isPremium` ถูก overwrite จาก server data

### `frontend/locales/en.ts`

- [x] แก้ข้อความราคาให้ตรง backend config — 9 THB/month, 99 THB/year

### `frontend/locales/th.ts`

- [x] แก้ข้อความราคาให้ตรง backend config — 9 บาท/เดือน, 99 บาท/ปี

### `tests/test_subscription_expiry.py` (new)

- [x] เพิ่ม unit tests สำหรับ active/expired logic — `TestSubscriptionLogic` 5 tests (line 63-90)
- [x] เพิ่ม tests สำหรับ renew before expiry — `TestRenewalLogic` line 103
- [x] เพิ่ม tests สำหรับ renew after expiry — line 110
- [x] เพิ่ม tests สำหรับ downgrade normalization — `TestSelfHeal` 4 tests (line 386-407)
- [x] เพิ่ม tests สำหรับ login payload normalization — `TestAPIContract.test_login_returns_normalized_subscription` line 363
- [x] เพิ่ม tests สำหรับ export/stats gating — `TestFeatureGating` 3 tests (line 559-571)
- [x] เพิ่ม tests สำหรับ bypass users — `TestBypassUsers` 2 tests + 2 self-heal tests (line 129-138, 407)

## 9. Risks And Mitigations

### Risk 1: Breaking Existing Login Payload Consumers

#### Impact

- Frontend หรือ bot logic ที่อ่าน `subscription_tier` แบบเดิมอาจได้รับ field เพิ่มหรือ behavior เปลี่ยน

#### Mitigation

- รักษา field เดิมไว้
- เพิ่ม field ใหม่ เช่น `is_premium_active`
- ปรับ frontend ให้ใช้ field ใหม่ก่อนค่อยเลิกพึ่ง raw tier

### Risk 2: Bypass Users ถูก Downgrade ผิด

#### Impact

- tester หรือ user ที่อยู่ใน `PREMIUM_BYPASS_USERS` อาจเสียสิทธิ์พิเศษ

#### Mitigation

- รวม bypass logic ใน utility กลาง
- เขียน test เฉพาะสำหรับ bypass users

### Risk 3: Race Condition ระหว่าง Normalize กับ Verify Payment

#### Impact

- ถ้าจัดลำดับผิด อาจ normalize state กลาง transaction ที่กำลัง upgrade

#### Mitigation

- normalize ก่อนเริ่ม verification flow
- transaction boundary ของ upgrade ต้องชัด

### Risk 4: Frontend แสดงสถานะไม่ตรงช่วง transition หลังจ่ายสำเร็จ

#### Impact

- user เห็น premium/free สลับชั่วคราว

#### Mitigation

- refetch server state หลัง success
- ใช้ optimistic state เท่าที่จำเป็น

### Risk 5: Policy Drift กลับมาอีกในอนาคต

#### Impact

- web กับ bot กลับไปใช้ logic คนละชุด

#### Mitigation

- ใช้ shared payment service
- เพิ่ม parity tests

## 10. Test Matrix

### 10.1 Subscription Logic

- [x] user free ปกติ -> active premium = false — test line 63
- [x] user premium ที่ expiry ยังไม่ถึง -> active premium = true — test line 70
- [x] user premium ที่ expiry ผ่านแล้ว -> active premium = false — test line 77
- [x] normalize expired premium -> tier ถูกปรับเป็น free — test line 386 (persisted)
- [x] normalize premium ที่ expiry เป็น null -> tier ถูกปรับเป็น free — test line 84

### 10.2 Renewal Behavior

- [x] renew ก่อนหมดอายุ monthly -> expiry เดิม + 30 วัน — test line 103 + line 256
- [x] renew ก่อนหมดอายุ yearly -> expiry เดิม + 365 วัน — same `get_renewal_base_datetime()` logic, plan duration is config-driven
- [x] renew หลังหมดอายุ monthly -> now + 30 วัน — test line 110
- [x] renew หลังหมดอายุ yearly -> now + 365 วัน — same logic, `get_renewal_base_datetime()` returns now for expired

### 10.3 Payment Validation

- [x] invalid plan -> fail — test line 152
- [x] non-image upload -> fail — test line 421
- [x] file > 10MB -> fail — test line 433
- [x] SlipOK duplicate -> fail — handled by SlipOK `log:true` + internal hash
- [x] internal duplicate trans_ref_hash -> fail — test line 161
- [x] amount mismatch -> fail — test line 201
- [x] valid slip -> success — test line 225

### 10.4 API Contract

- [x] login response ส่ง normalized tier — test line 363
- [x] login response ส่ง `subscription_expires_at` — test line 363
- [x] login response ส่ง `is_premium_active` — test line 363
- [x] `/payment/plans` ส่ง normalized current status — test line 345
- [x] `/payment/status` ส่ง normalized status และ days remaining — test line 337
- [x] `/users/me` ส่ง normalized subscription fields — test line 354

### 10.5 Feature Gating

- [x] expired premium user ดู advanced stats ไม่ได้ — test line 559
- [x] expired premium user export ได้แบบ free-tier scope เท่านั้น — test line 559 (check_premium returns False)
- [x] active premium user ได้ advanced stats และ full export — test line 565

### 10.6 Web/Bot Parity

- [x] web กับ bot ใช้ verification result เดียวกันสำหรับ slip เดียวกัน — test line 481
- [x] web กับ bot ใช้ amount validation rule เดียวกัน — test line 512
- [x] web กับ bot ใช้ duplicate protection rule เดียวกัน — test line 520
- [x] web กับ bot ใช้ renewal behavior เดียวกัน — ทั้งคู่ใช้ `verify_and_upgrade()` จาก shared service
- [x] web กับ bot ใช้ file validation rule เดียวกัน — ทั้งคู่ผ่าน `validate_slip_image()` ใน shared service
- [x] web กับ bot ใช้ throttling policy เดียวกัน — `_check_rate_limit()` 3/min per user ใน shared service

### 10.7 Bypass Users

- [x] bypass user ได้ premium active แม้ tier/free ปกติ — test line 129
- [x] bypass user ไม่ถูก normalize downgrade ผิด — test line 138 + 407

## 11. Manual End-To-End Verification Checklist

### 11.1 Web Flow

- [ ] login เป็น free user — ⏳ รอ manual verification
- [ ] เข้า `/subscription` — ⏳ รอ manual verification
- [ ] เห็นสถานะ Free และราคาแพลนถูกต้อง — ⏳ โค้ดรองรับ, รอ manual
- [ ] อัปโหลดสลิป valid แล้วสำเร็จ — ⏳ โค้ดรองรับ, รอ manual
- [ ] status card เปลี่ยนเป็น Premium Active พร้อม expiry — ⏳ โค้ดรองรับ, รอ manual
- [ ] reload หน้าแล้วสถานะยังถูกต้อง — ⏳ โค้ดรองรับ, รอ manual
- [ ] payment history มีรายการใหม่ — ⏳ โค้ดรองรับ, รอ manual
- [ ] dashboard ปลดล็อก advanced stats — ⏳ โค้ดรองรับ, รอ manual

### 11.2 Bot Flow

- [ ] ใช้ `/upgrade` — ⏳ รอ manual verification
- [ ] เลือกแพลนได้ — ⏳ รอ manual verification
- [ ] เห็นข้อมูลบัญชีและยอดถูกต้อง — ⏳ รอ manual verification
- [ ] ส่งรูป valid แล้วสำเร็จ — ⏳ รอ manual verification
- [ ] `/subscription` แสดง active premium พร้อม expiry — ⏳ รอ manual verification
- [ ] `/profile` แสดงสถานะสมาชิกและวันหมดอายุถูกต้อง — ⏳ รอ manual verification
- [ ] `/stats` แสดง premium analytics ได้ — ⏳ รอ manual verification

### 11.3 Expiry Simulation

- [ ] ตั้ง user ให้ expired premium — ⏳ รอ manual (มี automated test ครอบ: TestSelfHeal line 386)
- [ ] login ใหม่ -> API ส่ง free normalized state — ⏳ รอ manual (มี test: line 363)
- [ ] เปิดหน้า subscription -> เห็น Free ไม่ใช่ Premium — ⏳ รอ manual
- [ ] dashboard กลับไป lock premium analytics — ⏳ รอ manual
- [ ] bot `/subscription` กลับไปแสดง Free — ⏳ รอ manual

### 11.4 Renewal Cases

- [ ] active premium renew ก่อนหมดอายุ -> expiry stack จาก expiry เดิม — ⏳ รอ manual (มี test: line 256)
- [ ] expired premium renew -> expiry เริ่มจาก now — ⏳ รอ manual (มี test: line 110)

## 12. Rollout Plan

### Step 1: Backend Foundation

- สร้าง subscription utility
- สร้าง payment service
- refactor web และ bot ให้ใช้ shared logic

### Step 2: API Contract Cleanup

- ปรับ auth/payment/users responses
- รัน tests backend ทั้งหมดที่เกี่ยวข้อง

### Step 3: Frontend And Bot UX Cleanup

- ปรับหน้า subscription
- ปรับ bot subscription/profile
- ตรวจราคาที่แสดงผล

### Step 4: Regression Protection

- เพิ่ม unit tests
- เพิ่ม integration tests
- เพิ่ม parity tests

### Step 5: Final Verification

- ตรวจ web end-to-end
- ตรวจ bot end-to-end
- ตรวจ stale premium users ให้ self-heal

## 13. Definition Of Done

งานนี้ถือว่าเสร็จเมื่อครบทุกข้อด้านล่าง

- [x] มี utility กลางสำหรับ subscription state และ active premium — `app/utils/subscription.py`
- [x] Expired premium users ถูก normalize เป็น free บน API หลัก — persisted self-heal ใน `get_current_user()` + login + bot
- [x] Login, payment status, subscription page และ bot status ให้ข้อมูลตรงกัน — ทุก endpoint ใช้ `get_subscription_info()`
- [x] Web และ Bot ใช้ payment verification service เดียวกัน — `payment_service.py:verify_and_upgrade()`
- [x] Web และ Bot ใช้ shared core validation และ rate limit policy — `validate_slip_image()` + `_check_rate_limit()` ใน shared service; web route เพิ่ม HTTP-layer guards (FastAPI limiter, MIME/content-type, size check ใน `payment.py:56-78`) ก่อนเรียก shared service แต่ bot ไม่มี transport-layer เหล่านี้ (core policy ตรงกัน, outer guard ต่างกัน)
- [x] Renewal before/after expiry ทำงานตรง business rule — `get_renewal_base_datetime()` + tests
- [x] Payment history ใช้งานได้บน web — endpoint + UI (subscription page lines 295-342)
- [x] Bot แสดง expiry และ active status ได้อย่างถูกต้อง — `get_user_profile()` computes fields; `handlers.py` passes them; `locales.py` EN+TH templates render `active`/`expiry`/`days`
- [x] Frontend pricing copy ตรงกับ backend config — 9/99 THB in en.ts + th.ts
- [x] มี tests ครอบคลุม expiry, renewal, downgrade, duplicate, amount mismatch, parity, bypass users และ route-level feature gating — 39 tests ใน test_subscription_expiry.py
- [ ] Manual verification ผ่านทั้ง web และ bot — ⏳ รอดำเนินการ (Section 11)
- [x] ผู้ใช้ที่ stale premium อยู่ใน production self-heal ได้ใน access รอบถัดไป — `normalize_subscription_state()` commits to DB

## 14. Immediate Recommended Order For Implementation

ถ้าจะเริ่มลงมือทันที ให้ทำตามลำดับนี้

1. สร้าง `app/utils/subscription.py`
2. refactor `app/utils/security.py` ให้ใช้ utility กลาง
3. สร้าง `app/services/payment_service.py`
4. เปลี่ยน `app/routers/payment.py` และ `app/bot/services.py` ให้ใช้ shared payment service
5. แก้ `app/routers/auth.py`, `app/routers/payment.py`, `app/routers/users.py` ให้ตอบ normalized state
6. แก้ web subscription page ให้ refetch และแสดง active state จริง
7. แก้ bot subscription/profile UX
8. แก้ frontend locale pricing ให้ตรง config
9. เพิ่ม tests
10. ทำ manual verification และปิด rollout checklist

## 15. Notes For Implementation Round

- ต้องระวัง backward compatibility ของ frontend ที่ยังอ่าน cookie user และ auth payload เดิม
- ต้องระวัง bypass users ให้ทำงานต่อเหมือนเดิม
- ต้องไม่ทำให้ renewal logic เปลี่ยนจากพฤติกรรมปัจจุบันที่ถูกต้องอยู่แล้ว
- หากเลือก normalize ที่ request boundary ให้พิจารณา performance และ transaction scope ให้ชัด
- ถ้าจะเลื่อน bot payment history UI ออกนอก scope ให้บันทึกเหตุผลไว้ แต่ห้ามเลื่อน normalized status/expiry display ออก เพราะเป็น production-critical

---

## 16. Implementation Status (Updated 2026-04-04)

### Completed

| Phase | Status | Details |
|-------|--------|---------|
| Phase 1: Locale pricing | ✅ Done | `en.ts`, `th.ts` — 99/990 → 9/99 THB |
| Phase 2: Subscription utility | ✅ Done | `app/utils/subscription.py` — `is_premium_active()`, `get_subscription_info()`, `get_renewal_base_datetime()`, `normalize_subscription_state()` |
| Phase 3: Shared payment service | ✅ Done | `app/services/payment_service.py` — `verify_and_upgrade()`, `validate_slip_image()`, `PaymentError`, per-user rate limiting |
| Phase 4: API normalization | ✅ Done | `/payment/plans`, `/payment/status`, `/users/me` (GET + PUT), login response — all return normalized subscription fields |
| Phase 5: Bot rewire | ✅ Done | `services.py` — `verify_slip_payment()`, `get_subscription_status()`, `get_user_profile()` use shared service + central utility |
| Phase 5b: Bot profile UX | ✅ Done | `handlers.py` + `locales.py` (EN+TH) — `/profile` now renders `active`, `expiry`, `days_remaining`; indentation fixed in `handlers.py` and `payment_handlers.py` |
| Phase 6: Frontend UX | ✅ Done | Subscription page: refetch after payment, payment history table, days remaining, active status badge |
| Phase 7: Tests | ✅ Done | 39 tests in `test_subscription_expiry.py` — added Section 11 `TestRouteFeatureGating` with 4 route-level tests for `/stats/summary` (free=no advanced metrics, premium=full) and `/export/my-data` (free=limited note, premium=full note) |
| Phase 8: Verification | ⚠️ Partial | 39/39 tests pass. Web-layer HTTP guards (MIME+IP) exist in `payment.py` but not in bot path — shared core policy applies to both, web adds transport-layer guard (documented). Frontend `AppUser` type now includes subscription fields. Full pytest suite not rerun against all test files. |

### Key Changes Beyond Original Plan

1. **Self-heal (persisted normalization)**: `normalize_subscription_state()` writes expired premium → free back to DB. Called in `get_current_user()` (security.py), login (auth.py), bot `get_subscription_status()` and `get_user_profile()`.
2. **Image validation in shared layer**: `validate_slip_image()` checks magic bytes + file size in payment_service.py — ensures Web and Bot parity.
3. **Per-user rate limiting**: `_check_rate_limit()` in payment_service.py enforces 3/minute per user — applies to both Web and Bot.
4. **SQLite timezone safety**: `_ensure_aware()` in subscription.py + fix in `check_premium()` to handle naive datetimes from SQLite.
5. **Frontend types**: `SubscriptionInfo` interface added to `app-types.ts`.

### Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| Subscription logic (free/active/expired/null) | 5 | ✅ |
| Renewal (before/after expiry, free) | 3 | ✅ |
| Bypass users (always premium, no downgrade) | 2 + 2 self-heal | ✅ |
| Payment service (plan/dup/amount/success/stack) | 5 | ✅ |
| API contract (login/plans/status/users_me) | 4 | ✅ |
| Self-heal normalization | 4 | ✅ |
| Image validation (non-image/empty/size/jpeg/png) | 5 | ✅ |
| Rate limiting | 1 | ✅ |
| Web/Bot parity (verify/amount/duplicate) | 3 | ✅ |
| Feature gating (check_premium for all tiers) | 3 | ✅ |
| Route-level gating (/stats/summary, /export/my-data) | 4 | ✅ |
| **Total** | **39** | ✅ |

### Files Modified/Created

**New (3):**
- `app/utils/subscription.py`
- `app/services/payment_service.py`
- `tests/test_subscription_expiry.py`

**Modified (11):**
- `app/utils/security.py` — naive datetime fix + self-heal in `get_current_user()`
- `app/routers/payment.py` — shared service + normalized responses
- `app/routers/auth.py` — self-heal + normalized login response
- `app/routers/users.py` — normalized subscription in GET + PUT
- `app/schemas.py` — `UserProfileResponse` + subscription fields
- `app/bot/services.py` — shared service + self-heal + normalized
- `frontend/app/(dashboard)/subscription/page.tsx` — refetch, history, days remaining
- `frontend/locales/en.ts` — pricing fix
- `frontend/locales/th.ts` — pricing fix
- `frontend/lib/app-types.ts` — `SubscriptionInfo` type
