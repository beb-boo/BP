# Localization Dictionary for Telegram Bot

LOCALES = {
    "en": {
        "welcome": "Welcome back, {name}! ✅\nYou are already linked to the system.\nUse /stats to see your blood pressure trends or just send a photo to record.",
        "welcome_new": "Hi {name}! 👋\nTo start using the Blood Pressure Monitor Bot, please share your phone number to verify your identity.",
        "share_contact_btn": "📱 Share Contact",
        "wrong_contact": "❌ Please share your own contact.",
        "found_account": "✅ Found account for {phone}!\nPlease enter your **Web Password** to confirm linking:",
        "new_account": "🆕 Phone {phone} not registered.\nLet's create a new account.\n\nPlease enter your **Full Name** (e.g. John Doe):",
        "enter_dob": "📅 Please enter your **Date of Birth** (DD-MM-YYYY)\nExample: 15-04-1990",
        "enter_gender": "Please select your **Gender**:",
        "role_select": "Are you a **User** or a **Doctor**?",
        "set_password": "🔐 Finally, set a **Password** for your Web Login (min 8 chars):",
        "reg_success": "✅ Registration Complete!\nWe have linked this Telegram account.\n\nType /help to see what I can do, or send a photo to record BP!",
        "login_success": "✅ Login Successful!\nWelcome {name}.",
        "login_fail": "❌ Invalid password. Please try again.",
        "ocr_confirm": "I read:\nSys: **{sys}**\nDia: **{dia}**\nPulse: **{pulse}**\nDate: **{date}**\nTime: **{time}**\n\nIs this correct?",
        "btn_confirm": "✅ Confirm",
        "btn_edit": "✏️ Edit",
        "save_success": "✅ Saved! ({sys}/{dia} {pulse})\nSee /stats for trends.",
        "save_duplicate": "⚠️ Duplicate Record.\nYou already recorded this recently.",
        "stats_header": "**Your BP Profile**\n**Average** (Last 30 Records):\n{sys}/{dia} mmHg (Pulse {pulse})\n\n**Latest Entries**:",
        "no_records": "- No records found.",
        "help_msg": "**Need Help?** 🤖\n\n**General Commands:**\n/start - Register or Connect Account\n/settings - Manage Settings (Language/Timezone)\n/stats - View your Blood Pressure trends\n/help - Show this message\n/cancel - Cancel current operation\n\n**Subscription & Premium:** 💎\n/upgrade - Upgrade to Premium Plan\n/subscription - Check Subscription Status\n\n**How to Record BP:**\nJust send a photo of your monitor! 📸\n(If numbers are wrong, click 'Edit' to fix them)",        "lang_select": "Please select your language / กรุณาเลือกภาษา:",
        "lang_set": "✅ Language set to English.",
        "cancel": "Cancelled.",
        "error": "❌ An error occurred. Please try again.",
        "btn_cancel": "❌ Cancel",
        "settings_title": "⚙️ **Settings**",
        "settings_language": "🌐 Language: {lang}",
        "settings_timezone": "🕐 Timezone: {tz}",
        "btn_change_lang": "🌐 Language",
        "btn_change_tz": "🕐 Timezone",
        "tz_select": "Please select your timezone:",
        "tz_set": "✅ Timezone set to {tz}.",
        "error_pwd_length": "⚠️ Password must be at least 8 characters. Please try again:"
    },
    "th": {
        "welcome": "ยินดีต้อนรับกลับครับ, {name}! ✅\nบัญชีของคุณเชื่อมต่อเรียบร้อยแล้ว\nพิมพ์ /stats เพื่อดูสถิติ หรือส่งรูปมาเพื่อบันทึกได้เลยครับ",
        "welcome_new": "สวัสดีครับ {name}! 👋\nเพื่อเริ่มต้นใช้งาน บอทวัดความดัน กรุณากดปุ่มแชร์เบอร์โทรศัพท์เพื่อยืนยันตัวตนครับ",
        "share_contact_btn": "📱 แชร์เบอร์โทรศัพท์",
        "wrong_contact": "❌ กรุณาแชร์เบอร์โทรศัพท์ของตัวเองครับ",
        "found_account": "✅ บัญชีนี้มีอยู่ในระบบแล้ว ({phone})!\nกรุณากรอก **รหัสผ่าน Web** เพื่อยืนยันการเชื่อมต่อ:",
        "new_account": "🆕 เบอร์ {phone} ยังไม่ลงทะเบียน\nมาสร้างบัญชีใหม่กันครับ\n\nกรุณากรอก **ชื่อ-นามสกุล** (เช่น สมชาย ใจดี):",
        "enter_dob": "📅 กรุณากรอก **วันเกิด** (วว-ดด-ปปปป)\nตัวอย่าง: 15-04-1990",
        "enter_gender": "กรุณาเลือก **เพศ**:",
        "role_select": "คุณเป็น **ผู้ใช้งานทั่วไป (User)** หรือ **หมอ (Doctor)**?",
        "set_password": "🔐 สุดท้าย, ตั้ง **รหัสผ่าน** สำหรับเข้าเว็บ (ขั้นต่ำ 8 ตัว):",
        "reg_success": "✅ ลงทะเบียนสำเร็จ!\nเชื่อมต่อบัญชี Telegram เรียบร้อยแล้ว\n\nพิมพ์ /help เพื่อดูคำสั่ง หรือส่งรูปเพื่อบันทึกความดันได้เลย!",
        "login_success": "✅ เข้าสู่ระบบสำเร็จ!\nยินดีต้อนรับ {name} ครับ",
        "login_fail": "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่ครับ",
        "ocr_confirm": "อ่านค่าได้ดังนี้ครับ:\nบน: **{sys}**\nล่าง: **{dia}**\nชีพจร: **{pulse}**\nวันที่: **{date}**\nเวลา: **{time}**\n\nถูกต้องไหมครับ?",
        "btn_confirm": "✅ ถูกต้อง",
        "btn_edit": "✏️ แก้ไข",
        "save_success": "✅ บันทึกแล้ว! ({sys}/{dia} {pulse})\nดูสถิติพิมพ์ /stats",
        "save_duplicate": "⚠️ ข้อมูลซ้ำ\nคุณเพิ่งบันทึกค่านี้ไปเมื่อสักครู่นี้เองครับ",
        "stats_header": "**ข้อมูลสุขภาพของคุณ**\n**ค่าเฉลี่ย** (30 ครั้งล่าสุด):\n{sys}/{dia} mmHg (ชีพจร {pulse})\n\n**รายการล่าสุด**:",
        "no_records": "- ไม่พบประวัติการบันทึก",
        "help_msg": "**ช่วยเหลือ** 🤖\n\n**คำสั่งทั่วไป:**\n/start - เริ่มต้น / เชื่อมต่อบัญชี\n/settings - ตั้งค่า (เปลี่ยนภาษา / เขตเวลา)\n/stats - ดูสถิติความดันโลหิต\n/help - แสดงข้อความนี้\n/cancel - ยกเลิกรายการ\n\n**สมาชิก & พรีเมียม:** 💎\n/upgrade - อัพเกรดเป็นพรีเมียม\n/subscription - เช็คสถานะวันหมดอายุ\n\n**วิธีบันทึกค่าความดัน:**\nเพียงแค่ **ส่งรูปถ่าย** หน้าจอเครื่องวัดมาที่นี่! 📸\n(ถ้าเลขผิด สามารถกดปุ่ม 'แก้ไข' ได้ครับ)",
        "lang_select": "กรุณาเลือกภาษา / Please select your language:",
        "lang_set": "✅ เปลี่ยนภาษาเป็น ภาษาไทย เรียบร้อยครับ",
        "cancel": "ยกเลิกรายการแล้ว",
        "error": "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
        "btn_cancel": "❌ ยกเลิก",
        "settings_title": "⚙️ **ตั้งค่า**",
        "settings_language": "🌐 ภาษา: {lang}",
        "settings_timezone": "🕐 เขตเวลา: {tz}",
        "btn_change_lang": "🌐 ภาษา",
        "btn_change_tz": "🕐 เขตเวลา",
        "tz_select": "กรุณาเลือกเขตเวลาของคุณ:",
        "tz_set": "✅ ตั้งค่าเขตเวลาเป็น {tz} เรียบร้อยครับ",
        "error_pwd_length": "⚠️ รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร กรุณาลองใหม่อีกครั้ง:"
    }
}

def get_text(key: str, lookup_lang: str = "th", **kwargs) -> str:
    """Get localized text formatted with kwargs"""
    # Fallback to English if key missing in desired lang
    if lookup_lang not in LOCALES:
        lookup_lang = "en"
    
    text = LOCALES.get(lookup_lang, {}).get(key)
    
    if not text:
        # Fallback to English key
        text = LOCALES.get("en", {}).get(key, key)
        
    try:
        return text.format(**kwargs)
    except KeyError:
        return text
