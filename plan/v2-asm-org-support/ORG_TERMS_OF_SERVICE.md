---
title: "Organization Terms of Service"
aliases:
  - "Org ToS"
  - "Organization Terms"
  - "รพ.สต. ToS"
tags:
  - legal
  - terms-of-service
  - organization
  - pdpa
  - v2-asm-org
order: 12
status: draft
version: 1.0
updated: 2026-04-18
summary: "Ready-to-use Thai Terms of Service for organization admins (รพ.สต., คลินิก). Joint controller model, responsibilities, ownership transfer, termination."
related:
  - "[[PDPA_COMPLIANCE]]"
  - "[[CONSENT_FORMS]]"
  - "[[LEGACY_DOCS_MIGRATION]]"
  - "[[ORG_FOUNDATION]]"
---
# Organization Terms of Service (Ready-to-Use)

> **Status:** Draft v1 — สำหรับ legal review ก่อน deploy
> **Language:** ภาษาไทย (primary) + English references
> **Version:** 1.0
> **Target audience:** Admin ของ รพ.สต. หรือองค์กรอื่น ๆ ที่สมัครใช้ BP Monitor

---

## 1. Purpose & Usage

ข้อตกลงฉบับนี้ใช้สำหรับ:
- **Admin ขององค์กร** (รพ.สต., โรงพยาบาล, คลินิก, บริษัท) ที่ลงทะเบียนใช้ BP Monitor ในนามองค์กร
- **แตกต่างจาก** Terms of Service ของ individual users (ดู `docs/terms-of-service.md`)

ข้อตกลงนี้แสดงในระบบตอน:
- Admin onboard องค์กรครั้งแรก
- เมื่อมี version update ที่สำคัญ

**Admin ต้องยอมรับข้อตกลงนี้ก่อนใช้ features ขององค์กร**

---

## 2. Document Structure

เอกสารนี้มี 2 ส่วน:

1. **Part A:** ข้อตกลงฉบับสมบูรณ์ (ภาษาไทย, legal)
2. **Part B:** Implementation notes (for dev team)

---

# PART A: ข้อตกลงการใช้บริการสำหรับองค์กร

---

```
============================================================================
             ข้อกำหนดการใช้บริการสำหรับองค์กร
             (Organization Terms of Service)
             
             แพลตฟอร์ม BP Monitor
             
             วันที่มีผลบังคับใช้: [วัน/เดือน/ปี]
             ปรับปรุงล่าสุด: [วัน/เดือน/ปี]
             เวอร์ชัน: 1.0
============================================================================
```

## 1. คำนิยาม

- **"ข้อกำหนด"** หมายถึง ข้อกำหนดการใช้บริการสำหรับองค์กรฉบับนี้
- **"เรา"** หรือ **"ผู้ให้บริการ"** หมายถึง [ชื่อผู้ให้บริการ / นิติบุคคล]
- **"องค์กร"** หมายถึง โรงพยาบาลส่งเสริมสุขภาพตำบล (รพ.สต.), โรงพยาบาล, คลินิก, หรือ หน่วยงานอื่น ที่ลงทะเบียนใช้บริการในฐานะองค์กร
- **"Admin องค์กร"** หมายถึง บุคคลที่ได้รับมอบหมายจากองค์กรให้เป็นผู้ดูแลบัญชีองค์กรในระบบ
- **"สมาชิกองค์กร"** หมายถึง บุคคลที่ Admin เพิ่มเข้ามาในระบบในนามองค์กร เช่น อาสาสมัครสาธารณสุข (อสม.), พยาบาล, เจ้าหน้าที่
- **"เจ้าของข้อมูล"** หมายถึง บุคคลที่ข้อมูลส่วนบุคคลของตนถูกเก็บในระบบ รวมถึงชาวบ้านที่รับบริการจากองค์กร
- **"ข้อมูลส่วนบุคคล"** หมายถึง ข้อมูลตามนิยามใน พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA) รวมถึงข้อมูลสุขภาพซึ่งเป็นข้อมูลอ่อนไหว
- **"บริการ"** หมายถึง แพลตฟอร์ม BP Monitor รวมถึงเว็บแอปพลิเคชัน, PWA สำหรับ อสม., Telegram bot, และ API

---

## 2. การยอมรับในนามองค์กร

### 2.1 Admin กระทำในนามองค์กร

โดยการยอมรับข้อกำหนดฉบับนี้ Admin องค์กรยืนยันว่า:

1. ท่านเป็นบุคคลที่มีอำนาจตามกฎหมายในการผูกพันองค์กร กับข้อตกลงนี้ (เช่น ผู้อำนวยการ, ผู้จัดการ, หรือผู้ได้รับมอบอำนาจ)
2. ข้อมูลองค์กรที่ท่านให้ในการสมัครถูกต้องและครบถ้วน
3. ท่านได้รับอนุญาตจากองค์กรในการเก็บข้อมูลสมาชิก (เช่น อสม.) และเจ้าของข้อมูล (ชาวบ้าน)
4. ท่านจะแจ้งเราโดยไม่ชักช้าหากบทบาทของท่านเปลี่ยน (เช่น ลาออก, โอนย้าย, หมดวาระ)

### 2.2 หากไม่มีอำนาจ

หากท่านไม่มีอำนาจผูกพันองค์กร กรุณาหยุดการใช้งาน และให้บุคคลที่มีอำนาจยอมรับข้อกำหนดฉบับนี้แทน

---

## 3. บทบาท Joint Controller

### 3.1 ภายใต้ PDPA

เราและองค์กรของท่านเป็น **ผู้ควบคุมข้อมูลร่วม (Joint Controllers)** ตามมาตรา 24 แห่ง PDPA

หมายความว่า:
- ทั้งสองฝ่ายร่วมกันกำหนดวัตถุประสงค์และวิธีการประมวลผลข้อมูล
- ทั้งสองฝ่ายรับผิดชอบร่วมกันในการปฏิบัติตาม PDPA
- เจ้าของข้อมูลสามารถใช้สิทธิของตนต่อฝ่ายใดฝ่ายหนึ่งหรือทั้งสองฝ่ายก็ได้

### 3.2 การแบ่งความรับผิดชอบ

**ความรับผิดชอบของเรา (ผู้ให้บริการระบบ):**
1. ความพร้อมใช้งานและเสถียรภาพของระบบ
2. ความปลอดภัยทางเทคนิค (encryption, access control)
3. Audit logging และ security monitoring
4. การปฏิบัติตาม PDPA ด้านเทคนิค
5. การปฏิบัติต่อคำขอของเจ้าของข้อมูล (ด้านเทคนิค — การ export, ลบ, แก้ไข)
6. การแจ้งเหตุการละเมิดข้อมูลต่อสำนักงาน สคส. (ในกรณีที่ breach เกิดจากระบบของเรา)

**ความรับผิดชอบขององค์กร:**
1. ความถูกต้องและชอบธรรมของข้อมูลที่ป้อนเข้าระบบ
2. การได้รับความยินยอมจากเจ้าของข้อมูลก่อนป้อนข้อมูล (ตาม มาตรา 26 PDPA)
3. การเก็บเอกสาร consent กระดาษในสถานที่ปลอดภัย (ตู้ล็อก) ที่องค์กร
4. การใช้ข้อมูลเพื่อการดูแลสุขภาพตามวัตถุประสงค์ที่แจ้งไว้เท่านั้น (Purpose limitation)
5. การจัดการสมาชิก — เพิ่ม, ลบ, ควบคุมการเข้าถึง
6. การฝึกอบรมสมาชิก (เช่น อสม.) ให้ปฏิบัติตาม PDPA และมาตรฐานของระบบ
7. การตอบคำถามเบื้องต้นจากเจ้าของข้อมูล
8. การแจ้งเราโดยไม่ชักช้าหากตรวจพบเหตุการละเมิดข้อมูลในฝั่งองค์กร (เช่น เอกสารกระดาษหาย, สมาชิกใช้สิทธิ์เกินขอบเขต)

### 3.3 Documentation

การแบ่งความรับผิดชอบนี้ถือเป็น joint controller arrangement ตามกฎหมาย และทั้งสองฝ่ายตกลงที่จะเก็บบันทึกประกอบ

---

## 4. การจัดการสมาชิก (Member Management)

### 4.1 การเพิ่มสมาชิก

Admin องค์กรมีหน้าที่:

1. **สมัครสมาชิก (อสม./เจ้าหน้าที่) ในระบบ** พร้อมข้อมูลที่ถูกต้อง
2. **จัดส่ง pairing code** ให้สมาชิกเพื่อเชื่อมต่อ Telegram
3. **ฝึกอบรมสมาชิก** เกี่ยวกับ:
   - การเก็บ consent จากเจ้าของข้อมูล
   - การใช้ระบบอย่างถูกต้อง
   - การรักษาความปลอดภัยข้อมูล (ไม่แชร์ account, ไม่ใช้อุปกรณ์ที่ไม่ปลอดภัย)
4. **ติดตามการทำงาน** ของสมาชิก
5. **เอาออก (deactivate) สมาชิก** เมื่อไม่ได้ทำงานให้องค์กรอีกต่อไป

### 4.2 ความรับผิดชอบต่อการกระทำของสมาชิก

องค์กรรับผิดชอบต่อการกระทำของสมาชิกในการใช้ระบบ เช่น:
- สมาชิกใช้ระบบผิดวัตถุประสงค์ — องค์กรต้องแก้ไข
- สมาชิกเก็บข้อมูลโดยไม่มี consent — องค์กรรับผิดชอบร่วมกับสมาชิก
- สมาชิกเปิดเผยข้อมูลแก่บุคคลที่ 3 — องค์กรต้องรายงานและดำเนินการ

### 4.3 การโอนสิทธิดูแลชาวบ้าน (Care Assignment Transfer)

เมื่อสมาชิก (เช่น อสม.) ลาออกหรือย้าย:
- Admin ต้อง transfer care assignments ของสมาชิกไปยังสมาชิกคนอื่น
- หากไม่มีผู้รับ: ต้อง pause การเก็บข้อมูลจนกว่าจะมี
- ต้องแจ้งเจ้าของข้อมูล (ชาวบ้าน) ว่ามีการเปลี่ยนผู้ดูแล

---

## 5. Ownership Transfer (การโอนสิทธิ์ Admin)

### 5.1 หลักการ

บัญชี **องค์กร** ควรมี admin อย่างน้อย 1 คนเสมอ หาก admin คนเดียวลาออก องค์กรจะไม่สามารถจัดการได้

### 5.2 ขั้นตอนการโอนสิทธิ์

**Admin ปัจจุบันยังทำงานอยู่:**

1. Admin ปัจจุบัน login เข้าระบบ
2. ไปที่ Settings → Organization → Transfer Admin Role
3. ระบุบัญชีของ admin ใหม่ (ต้องมี user account ในระบบก่อน)
4. ยืนยันด้วย OTP หรือ re-authentication
5. Admin ใหม่จะได้รับ notification + ต้องยอมรับ (ยอมรับ Org ToS นี้อีกครั้ง)
6. Admin เก่าสามารถ deactivate ตัวเองหลังการ transfer สำเร็จ

**Admin ปัจจุบันไม่สามารถโอนได้ (ลาออกกะทันหัน, เสียชีวิต):**

1. องค์กรส่งคำขอเป็นทางการถึงเรา (เอกสารขององค์กร + หลักฐานอำนาจของผู้ขอ)
2. เราตรวจสอบ (อาจใช้เวลา 3-7 วันทำการ)
3. Superadmin ของเราเป็นผู้ reassign ownership ให้ admin ใหม่
4. Admin ใหม่ต้องยอมรับ Org ToS

### 5.3 ข้อมูลขององค์กรระหว่างช่วงเปลี่ยน

- ข้อมูลยังคงอยู่ในระบบ
- สมาชิกที่ไม่ใช่ admin ยังใช้งานได้ปกติ
- แต่การจัดการ (เพิ่ม/ลบสมาชิก, ปรับ care assignment) จะหยุดจนกว่าจะมี admin ใหม่

---

## 6. ข้อห้าม

องค์กร **ห้าม**:

1. **ใช้ข้อมูลสมาชิก/เจ้าของข้อมูลเพื่อการตลาด** โดยไม่ได้รับความยินยอมแยกและชัดเจน
2. **ขายข้อมูลหรือส่งให้บุคคลที่สาม** นอกเหนือจากที่ได้รับ consent ชัดแจ้ง
3. **ใช้ระบบเพื่อวัตถุประสงค์ที่ไม่ใช่การดูแลสุขภาพ** (เช่น วิจัยเชิงพาณิชย์ที่ไม่ได้รับอนุญาต, การตลาดยา)
4. **Bypass ระบบ consent, audit log, หรือกลไกความปลอดภัย** ใด ๆ
5. **ให้สมาชิกหลายคนใช้บัญชีเดียวกัน** (ต้องมี 1 บัญชี ต่อ 1 คน)
6. **ให้บุคคลภายนอกองค์กรเข้าถึงข้อมูลในระบบ** (เช่น ผ่านการแชร์ account หรือ URL)
7. **กระทำการใด ๆ ที่ขัดต่อ PDPA** หรือกฎหมายที่เกี่ยวข้อง
8. **Modify, reverse-engineer, หรือ attack** ระบบของเรา
9. **บันทึกข้อมูลปลอม** หรือข้อมูลของบุคคลที่ไม่มีอยู่จริง

---

## 7. การใช้งานและข้อจำกัด

### 7.1 จำนวนสมาชิกและเจ้าของข้อมูล

ตามแผนบริการที่ท่านสมัคร อาจมีข้อจำกัด:
- จำนวน admin ต่อองค์กร
- จำนวนสมาชิก (อสม.) ต่อองค์กร
- จำนวนเจ้าของข้อมูล (ชาวบ้าน) ต่อองค์กร
- จำนวน BP readings ต่อเดือน

**แผน Pilot (ช่วงทดสอบ):**
- 1 admin
- ไม่เกิน 10 อสม.
- ไม่เกิน 100 เจ้าของข้อมูล
- ไม่จำกัด readings

**แผน Production (อนาคต):**
[TBD — จะกำหนดเมื่อ launch จริง]

### 7.2 การใช้งานที่เกินขีดจำกัด

หากการใช้งานเกินขีดจำกัดของแผน เราอาจ:
- แจ้งเตือนและขอให้ upgrade
- จำกัดการใช้งาน feature บางส่วน
- ไม่ลบข้อมูล (ข้อมูลปลอดภัย)

### 7.3 Downtime และ Maintenance

เราจะพยายามให้ระบบพร้อมใช้ 99% ของเวลา แต่อาจมี:
- Scheduled maintenance (แจ้งล่วงหน้าผ่าน email/in-app)
- Unscheduled downtime เนื่องจากเหตุสุดวิสัย

เราไม่รับผิดชอบต่อความเสียหายที่เกิดจาก downtime ยกเว้นกรณีเรามีความประมาทเลินเล่ออย่างร้ายแรง

---

## 8. การชำระเงิน (ในอนาคต — Pilot ไม่เสียค่าใช้จ่าย)

[TBD — จะกำหนดเมื่อ launch จริง]

เงื่อนไขการชำระเงิน, การเรียกเก็บ, การคืนเงิน — จะระบุใน subscription agreement แยกต่างหาก

---

## 9. การยกเลิกบริการ

### 9.1 องค์กรต้องการยกเลิก

องค์กรสามารถยกเลิกการใช้บริการได้โดย:

1. **แจ้งล่วงหน้า 30 วัน** ผ่าน in-app settings หรือ email
2. เราจะ:
   - **Export ข้อมูลทั้งหมดขององค์กร** ให้ (CSV/JSON/PDF format)
   - Deactivate สมาชิกทั้งหมดในองค์กร (admin + อสม.)
   - แจ้งเจ้าของข้อมูล (ชาวบ้าน) ว่าองค์กรยกเลิกบริการ
   - หลังจาก 90 วัน: ลบข้อมูลระบบทั้งหมดขององค์กร (ยกเว้น audit log + backup)
   - ข้อมูลเจ้าของข้อมูลที่เป็น self-managed จะยังคงอยู่ (ไม่ถูกกระทบ)
3. องค์กรต้องรับผิดชอบดำเนินการกับเอกสารกระดาษ consent (เก็บต่อ, โอน, หรือทำลาย ตาม retention policy)

### 9.2 เรายกเลิกการให้บริการแก่องค์กร

เราอาจยกเลิกหรือระงับบัญชีองค์กรหาก:

- องค์กรละเมิดข้อกำหนดฉบับนี้อย่างร้ายแรง
- องค์กรละเมิด PDPA
- องค์กรไม่ชำระค่าบริการ (กรณีมี subscription)
- มีคำสั่งจากหน่วยงานรัฐ
- องค์กรให้ข้อมูลเท็จในการสมัคร

**ก่อนยกเลิก** เราจะพยายามแจ้งและให้โอกาสแก้ไข ยกเว้นกรณีเร่งด่วนที่ต้องดำเนินการทันทีเพื่อความปลอดภัยของระบบหรือผู้ใช้รายอื่น

### 9.3 เราหยุดบริการโดยสิ้นเชิง

หากเราตัดสินใจหยุดให้บริการทั้งระบบ เราจะ:
- แจ้งล่วงหน้าอย่างน้อย 90 วัน
- Export ข้อมูลทั้งหมดให้ทุกองค์กร
- ช่วยหา alternative ถ้าเป็นไปได้
- ไม่ละทิ้งข้อมูลโดยไม่เก็บ

---

## 10. การจัดการเมื่อเกิดเหตุการณ์ผิดปกติ

### 10.1 Breach Notification (สำคัญ)

**หากองค์กรตรวจพบเหตุการละเมิดข้อมูลในฝั่งของตน** (เช่น เอกสารกระดาษหาย, สมาชิกใช้สิทธิ์เกินขอบเขต, ถูกแฮก):

1. **แจ้งเราโดยไม่ชักช้า** (ภายใน 24 ชั่วโมง หรือเร็วกว่าถ้าเป็นไปได้)
2. ผ่านช่องทาง: privacy@yourdomain.com หรือโทร [...]
3. เราจะร่วมมือในการ:
   - ประเมินขอบเขตความเสียหาย
   - แจ้งเจ้าของข้อมูลที่ได้รับผลกระทบ
   - แจ้งสำนักงาน สคส. ภายใน 72 ชม. (หากจำเป็น)
   - ดำเนินการแก้ไขและป้องกัน

### 10.2 Breach จากระบบของเรา

หากเหตุการละเมิดข้อมูลเกิดจากระบบของเรา:
- เราจะแจ้งองค์กรภายใน 24 ชั่วโมง
- เราจะดำเนินการตาม [[BREACH_RESPONSE_RUNBOOK]]
- เราเป็นผู้หลักในการแจ้ง สคส.

---

## 11. สิทธิและหน้าที่ของเจ้าของข้อมูล

### 11.1 องค์กรต้องเคารพสิทธิของเจ้าของข้อมูล

ตาม PDPA เจ้าของข้อมูลมีสิทธิ:
- ขอดูข้อมูลตัวเอง
- ขอแก้ไข
- ขอลบ
- ถอนความยินยอม
- ขอโอนย้าย (portability)
- คัดค้าน
- ระงับชั่วคราว

**องค์กรต้อง:**
1. รับคำขอจากเจ้าของข้อมูลและดำเนินการภายใน 30 วัน
2. ประสานงานกับเราหากจำเป็น (เช่น ต้อง export ข้อมูลทางเทคนิค)
3. บันทึกคำขอและการตอบสนอง
4. ไม่เรียกเก็บค่าใช้จ่ายจากเจ้าของข้อมูล

### 11.2 ช่องทางติดต่อ

องค์กรต้องมีช่องทางให้เจ้าของข้อมูลติดต่อได้:
- เบอร์โทร (อย่างน้อย)
- ที่อยู่ของ รพ.สต. / องค์กร
- Optional: อีเมล

ช่องทางนี้ต้องแสดงใน consent form ที่มอบให้เจ้าของข้อมูล

---

## 12. Indemnification

องค์กรตกลงชดเชยและปกป้องเราจากข้อเรียกร้อง ความเสียหาย หรือค่าใช้จ่ายใด ๆ ที่เกิดจาก:

1. การใช้บริการผิดวัตถุประสงค์โดยสมาชิกขององค์กร
2. การให้ข้อมูลเท็จโดยองค์กรหรือสมาชิก
3. การละเมิด PDPA โดยองค์กรหรือสมาชิก
4. การละเมิดข้อกำหนดฉบับนี้
5. การใช้สิทธิ์ของสมาชิกเกินขอบเขต (unauthorized access by members)

ในทางกลับกัน เราจะปกป้ององค์กรจากข้อเรียกร้องที่เกิดจาก:
- ข้อบกพร่องของระบบของเรา
- การละเมิดความปลอดภัยที่เกิดจากระบบของเรา
- การประมวลผลข้อมูลโดยเราเกินขอบเขตที่องค์กรมอบให้

---

## 13. ข้อจำกัดความรับผิด

### 13.1 บริการ "ตามสภาพ"

เราให้บริการตามสภาพที่เป็นอยู่ (AS IS) เราไม่รับประกัน:
- ความพร้อมใช้งานตลอดเวลาโดยไม่ขาดตอน
- ความถูกต้องของข้อมูลที่ป้อนโดยสมาชิก/เจ้าของข้อมูล
- ความเหมาะสมสำหรับวัตถุประสงค์เฉพาะ (ต้องประเมินโดยองค์กรเอง)

### 13.2 ขอบเขตความรับผิด

ภายใต้ขอบเขตที่กฎหมายอนุญาต ในกรณีที่เราต้องรับผิด ความรับผิดสูงสุดจะไม่เกิน:
- ระยะเวลาที่เป็น liability period: 12 เดือนก่อนเกิดเหตุ
- จำนวนเงิน: ค่าบริการที่ชำระใน 12 เดือนก่อนเกิดเหตุ หรือ 10,000 บาท (แล้วแต่จำนวนใดจะมากกว่า)

### 13.3 ความรับผิดที่ไม่จำกัด

ข้อจำกัดข้างต้นไม่บังคับใช้กรณี:
- ความประมาทเลินเล่ออย่างร้ายแรงของเรา
- การกระทำโดยจงใจของเรา
- ความเสียหายที่เกิดจากการละเมิดกฎหมายที่เราไม่อาจจำกัดได้

---

## 14. ทรัพย์สินทางปัญญา

- ซอฟต์แวร์ของเราอยู่ภายใต้สัญญาอนุญาต **GNU Affero General Public License v3 (AGPL-3.0)**
- องค์กรสามารถตรวจสอบซอร์สโค้ดได้ที่: [URL GitHub]
- เครื่องหมายการค้า "BP Monitor" และโลโก้ เป็นของเรา
- ข้อมูลที่องค์กรเก็บในระบบ ยังคงเป็นของเจ้าของข้อมูล ไม่ใช่ขององค์กรหรือของเรา

---

## 15. การเปลี่ยนแปลงข้อกำหนด

### 15.1 การปรับปรุง

เราอาจปรับปรุงข้อกำหนดฉบับนี้เป็นครั้งคราว การเปลี่ยนแปลงที่สำคัญจะแจ้งล่วงหน้าอย่างน้อย 30 วัน

### 15.2 การยอมรับ version ใหม่

หากมี version ใหม่ Admin ต้อง:
- อ่าน changelog
- ยอมรับ version ใหม่ภายใน 30 วันหลังการแจ้ง

หากไม่ยอมรับ: บัญชีองค์กรอาจถูก restrict ใช้งานได้จำกัด

---

## 16. ข้อกำหนดทั่วไป

### 16.1 กฎหมายที่ใช้บังคับ

ข้อกำหนดฉบับนี้อยู่ภายใต้กฎหมายแห่งราชอาณาจักรไทย

### 16.2 การระงับข้อพิพาท

1. พยายามเจรจาก่อน
2. หากไม่สำเร็จภายใน 60 วัน: ใช้ศาลไทยที่มีเขตอำนาจ
3. Optional: อนุญาโตตุลาการ (ถ้าทั้งสองฝ่ายตกลง)

### 16.3 ความเป็นโมฆะบางส่วน

หากส่วนใดของข้อกำหนดเป็นโมฆะ ส่วนที่เหลือยังคงมีผล

### 16.4 ข้อตกลงทั้งหมด

ข้อกำหนดฉบับนี้ ร่วมกับ:
- Privacy Policy
- Terms of Service (สำหรับ individual)
- Subscription agreement (ถ้ามี)
- Consent forms ที่องค์กรเก็บจากเจ้าของข้อมูล

ถือเป็นข้อตกลงครบถ้วนระหว่างองค์กรกับเรา

### 16.5 การสละสิทธิ

การที่เราไม่บังคับใช้สิทธิใดในครั้งหนึ่ง ไม่ถือว่าสละสิทธิดังกล่าว

---

## 17. ช่องทางติดต่อ

| ช่องทาง | รายละเอียด |
|---------|-----------|
| อีเมลทั่วไป | support@yourdomain.com |
| อีเมลด้านข้อมูลส่วนบุคคล | privacy@yourdomain.com |
| Breach notification | security@yourdomain.com |
| ที่อยู่ | [...] |
| เว็บไซต์ | [...] |

สำหรับเรื่องด่วนเกี่ยวกับความปลอดภัยของข้อมูล: โทร [...]

---

## 18. DPO Contact

**Data Protection Officer (DPO) ของเรา:**

ชื่อ: [Pornthep / หรือผู้ที่ได้รับมอบหมาย]
อีเมล: dpo@yourdomain.com

สำหรับคำถามเฉพาะเจาะจงเกี่ยวกับ PDPA compliance

---

## 19. การร้องเรียนต่อ สคส.

หากองค์กร (หรือเจ้าของข้อมูลผ่านองค์กร) เห็นว่าเราไม่ปฏิบัติตาม PDPA สามารถร้องเรียนได้ที่:

**สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.)**
- เว็บไซต์: https://www.pdpc.or.th
- โทร: 02-141-6993
- อีเมล: saraban@pdpc.or.th

---

## 20. การยอมรับ

โดยการคลิก **"ยอมรับและดำเนินการต่อ"** หรือการใช้บริการในฐานะ admin องค์กร ท่านยืนยันว่า:

☐ ท่านได้อ่านและเข้าใจข้อกำหนดฉบับนี้
☐ ท่านมีอำนาจผูกพันองค์กร
☐ ท่านยอมรับข้อกำหนดในนามขององค์กร

---

```
============================================================================
*ข้อกำหนดฉบับนี้จัดทำเป็นภาษาไทย ในกรณีที่มีฉบับแปลเป็นภาษาอื่น
ให้ถือฉบับภาษาไทยเป็นหลัก*

เวอร์ชัน: 1.0
มีผลตั้งแต่: [วัน/เดือน/ปี]
============================================================================
```

---

# PART B: Implementation Notes (for Dev Team)

---

## 1. Storage Location

```
docs/
├── org-terms-of-service.md         # Published version (for users to read)
├── org-terms-of-service-v1.md      # Historical versions
```

Also serve at URL: `https://yourdomain.com/org-terms-of-service`

## 2. Display in App

### 2.1 First-time Admin Onboarding

When admin first logs in as `org_admin`:
- Check `organization.terms_version` against `CURRENT_ORG_TERMS_VERSION`
- If null or outdated: show modal with ToS
- Must check 3 checkboxes + click "ยอมรับและดำเนินการต่อ"
- Cannot dismiss modal (block until acceptance)

### 2.2 Version Update

When new version released:
- Show banner to admin next login
- Grace period: 30 days
- After 30 days: block admin-specific features until accepted (but read-only still works)

## 3. Backend Recording

When admin accepts:

```python
# app/api/org_onboarding.py

@router.post("/accept-org-terms")
@require_role(UserRole.org_admin)
async def accept_org_terms(
    version: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    org = current_user.primary_organization
    
    # Verify version
    if version != CURRENT_ORG_TERMS_VERSION:
        raise HTTPException(400, "Version mismatch")
    
    # Record acceptance
    org.terms_version = version
    org.terms_accepted_at = datetime.utcnow()
    org.terms_accepted_by_user_id = current_user.id
    org.terms_accepted_from_ip = request.client.host
    
    # Audit
    await log_audit(
        action=AuditAction.org_update,
        actor_user_id=current_user.id,
        actor_organization_id=org.id,
        target_type="organization",
        target_id=str(org.id),
        metadata={
            "event": "org_terms_acceptance",
            "terms_version": version,
            "user_agent": request.headers.get("user-agent")
        }
    )
    
    await db.commit()
    return {"accepted": True}
```

## 4. Middleware Check

```python
# app/middleware/terms.py

async def check_org_terms_middleware(request: Request, call_next):
    # Only for authenticated admin requests
    user = getattr(request.state, "user", None)
    if not user or user.primary_role != UserRole.org_admin:
        return await call_next(request)
    
    # Skip for the ToS acceptance endpoint itself
    if request.url.path == "/api/v1/accept-org-terms":
        return await call_next(request)
    
    org = user.primary_organization
    if not org.terms_version or org.terms_version != CURRENT_ORG_TERMS_VERSION:
        # Allow read-only, block writes
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Organization ToS acceptance required",
                    "current_version": org.terms_version,
                    "required_version": CURRENT_ORG_TERMS_VERSION,
                    "accept_endpoint": "/api/v1/accept-org-terms"
                }
            )
    
    return await call_next(request)
```

## 5. Constants

```python
# app/config/legal.py

CURRENT_ORG_TERMS_VERSION = "1.0"
CURRENT_ORG_TERMS_URL = "/org-terms-of-service"
ORG_TERMS_GRACE_PERIOD_DAYS = 30  # after new version release
```

## 6. Frontend Component

```tsx
// frontend/app/admin/components/OrgTermsModal.tsx

export function OrgTermsModal({ version, onAccept }) {
  const [checkboxes, setCheckboxes] = useState({
    read: false,
    authority: false,
    onBehalfOfOrg: false
  });
  
  const allChecked = Object.values(checkboxes).every(v => v);
  
  return (
    <Dialog isDismissable={false}>
      <DialogHeader>ข้อกำหนดสำหรับองค์กร v{version}</DialogHeader>
      <DialogContent>
        <iframe src={`/org-terms-of-service`} />
        <CheckboxList checkboxes={checkboxes} onChange={setCheckboxes} />
      </DialogContent>
      <DialogFooter>
        <Button 
          onClick={() => onAccept(version)} 
          disabled={!allChecked}
        >
          ยอมรับและดำเนินการต่อ
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
```

## 7. Version Management

### 7.1 Adding a New Version

1. Update Part A content
2. Change version number in metadata
3. Update `CURRENT_ORG_TERMS_VERSION` constant
4. Write changelog in `CHANGELOG.md`
5. Archive old version at `docs/org-terms-of-service-v{X}.md`
6. Deploy

### 7.2 Communication

On version update:
- Email all org admins with changelog summary
- In-app banner for 30 days
- Grace period before forced re-acceptance

## 8. Audit Trail

Every acceptance creates permanent audit log entry. Queryable:

```sql
-- Find acceptance history for an org
SELECT actor_user_id, created_at, metadata
FROM audit_logs
WHERE actor_organization_id = :org_id
  AND action = 'org_update'
  AND metadata->>'event' = 'org_terms_acceptance'
ORDER BY created_at DESC;
```

Retention: 10 years (legal).

## 9. Legal Review Before Deploy

**DO NOT deploy v1.0 without:**
- [ ] External PDPA consultant review
- [ ] Thai language editor review
- [ ] Legal counsel sign-off on joint controller language
- [ ] Internal stakeholder approval
- [ ] Translation consistency check (if EN version added later)

---

**End of ORG_TERMS_OF_SERVICE.md**
