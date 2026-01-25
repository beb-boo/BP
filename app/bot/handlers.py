
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from app.bot.services import BotService
from app.bot.log_service import BotLogService
from app.utils.ocr_helper import read_blood_pressure_with_gemini
from .locales import get_text
from datetime import datetime
import logging
import tempfile
import os

# --- Language States ---
SELECT_LANG = 99

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change Language."""
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇹🇭 ไทย", callback_data="lang_th")]
    ]
    
    # Get current user lang to prompt in correct language?
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = user.language if user else "en"
    
    msg = get_text("lang_select", lang)
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    lang = "en" if data == "lang_en" else "th"

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if user:
        BotService.update_user_language(user.id, lang)
        msg = get_text("lang_set", lang)
        await query.edit_message_text(msg)
    else:
        await query.edit_message_text("❌ Please /start first.")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text("⚠️ Please /start and link your account first.")
        return

    lang = user.language or "en"
    user_tz = user.timezone or "Asia/Bangkok"
    lang_display = "English" if lang == "en" else "ภาษาไทย"

    msg = get_text("settings_title", lang) + "\n\n"
    msg += get_text("settings_language", lang, lang=lang_display) + "\n"
    msg += get_text("settings_timezone", lang, tz=user_tz)

    keyboard = [
        [
            InlineKeyboardButton(get_text("btn_change_lang", lang), callback_data="settings_lang"),
            InlineKeyboardButton(get_text("btn_change_tz", lang), callback_data="settings_tz")
        ]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings menu callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await query.edit_message_text("❌ Please /start first.")
        return

    lang = user.language or "en"

    if data == "settings_lang":
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇹🇭 ไทย", callback_data="lang_th")]
        ]
        msg = get_text("lang_select", lang)
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "settings_tz":
        # Show timezone selection
        tz_choices = BotService.get_timezone_choices()
        keyboard = []
        for tz_value, label_en, label_th in tz_choices[:8]:  # Show first 8 common timezones
            label = label_th if lang == "th" else label_en
            keyboard.append([InlineKeyboardButton(label, callback_data=f"tz_{tz_value}")])

        msg = get_text("tz_select", lang)
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timezone selection callback."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("tz_"):
        return

    tz_value = data[3:]  # Remove "tz_" prefix
    user = BotService.get_user_by_telegram_id(update.effective_user.id)

    if user:
        success = BotService.update_user_timezone(user.id, tz_value)
        lang = user.language or "en"
        if success:
            msg = get_text("tz_set", lang, tz=tz_value)
        else:
            msg = get_text("error", lang)
        await query.edit_message_text(msg)
    else:
        await query.edit_message_text("❌ Please /start first.")

logger = logging.getLogger(__name__)

# --- Auth States ---
SHARE_CONTACT = 0
AUTH_PASSWORD = 1
REG_NAME = 2
REG_DOB = 3
REG_GENDER = 4
REG_ROLE = 5
REG_PASSWORD = 6

# --- OCR States ---
OCR_CONFIRM = 10
OCR_EDIT = 11

# ============================================================================
# Auth / Registration Flow
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: Check if user is linked, if not ask for contact."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 0. Check for Deep Link (verify_TOKEN)
    if context.args and context.args[0].startswith("verify_"):
        token = context.args[0].replace("verify_", "")
        linked_user = BotService.process_connection_token(token, chat_id)
        
        if linked_user:
            await update.message.reply_text(
                f"✅ **Account Connected!**\n"
                f"Welcome, {linked_user.full_name}.\n"
                "Your Telegram is now linked to your web account.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Connection link is invalid or expired.")
    
    # 1. Check if already linked
    linked_user = BotService.get_user_by_telegram_id(chat_id)
    lang = linked_user.language if linked_user else "en"
    
    if linked_user:
        msg = get_text("welcome", lang, name=linked_user.full_name)
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove()
        )
        BotLogService.log(user.id, "OUT", "welcome", "Welcome back message sent", linked_user.id)
        return ConversationHandler.END

    # 2. Not linked -> Request Contact
    # Assume EN for new users or let them choose? Default EN.
    lang = "en"
    
    contact_btn_text = get_text("share_contact_btn", lang)
    contact_keyboard = KeyboardButton(text=contact_btn_text, request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_keyboard]], one_time_keyboard=True, resize_keyboard=True)
    
    msg = get_text("welcome_new", lang, name=user.first_name)
    await update.message.reply_text(
        msg,
        reply_markup=reply_markup
    )
    return SHARE_CONTACT

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text("❌ Please share your own contact.")
        return SHARE_CONTACT
        
    phone_number = contact.phone_number
    if phone_number.startswith("+"):
        phone_number = phone_number[1:]
    
    context.user_data['phone_number'] = phone_number
    existing_user = BotService.get_user_by_phone(phone_number)
    
    if existing_user:
        context.user_data['user_id'] = existing_user.id
        
        lang = existing_user.language or "en"
        msg = get_text("found_account", lang, phone=phone_number)
        
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return AUTH_PASSWORD
    else:
        # Request Name
        # Lang defaults to EN for new user, or maybe TH if phone is Thai? 
        # Hard to guess. Stick to default EN or prompt?
        # Let's check phone prefix? +66 -> TH.
        lang = "th" if phone_number.startswith("66") else "en"
        context.user_data['register_lang'] = lang # Store for flow
        
        msg = get_text("new_account", lang, phone=phone_number)
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return REG_NAME

async def auth_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    phone_number = context.user_data.get('phone_number')
    try:
        await update.message.delete()
    except:
        pass

    user = BotService.verify_user_password(phone_number, password)
    if user:
        BotService.link_telegram_account(user.id, update.effective_chat.id)
        await update.message.reply_text("✅ Account Linked Successfully!\nYou can now use the bot.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Incorrect Password. Please try again or /cancel.")
        return AUTH_PASSWORD

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    lang = context.user_data.get('register_lang', 'en')
    
    msg = get_text("enter_dob", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")
    return REG_DOB

async def reg_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        dob = datetime.strptime(text, "%d/%m/%Y")
        context.user_data['date_of_birth'] = dob
    except ValueError:
        lang = context.user_data.get('register_lang', 'en')
        # Error msg not localized in dict yet, add simple fallback or extend dict later
        # I'll use hardcoded EN/TH based on lang for now or just generic.
        # Let's keep existing EN hardcoded for error to save time or basic dict.
        # Actually dict has "error".
        # I'll use simple hardcoded check.
        if lang == "th":
            err = "❌ รูปแบบผิด กรุณาใช้ DD/MM/YYYY (เช่น 31/01/1990):"
        else:
            err = "❌ Invalid format. Please use DD/MM/YYYY (e.g. 31/01/1990):"
        await update.message.reply_text(err)
        return REG_DOB

    lang = context.user_data.get('register_lang', 'en')
    msg = get_text("enter_gender", lang)
    
    keyboard = [['Male', 'Female', 'Other']] # Buttons hardcoded EN for data consistency?
    # Or translate buttons? If I translate buttons, I must map them back to data 'male','female'.
    # For now, keep buttons EN to simplify data mapping or map "ชาย" -> "male".
    # I'll keep buttons EN for simplicity as requested "Bilingual Support" usually implies UI text.
    # User requested "Support both", implied fully.
    # I'll leave buttons EN for now to avoid logic bugs in `reg_gender`.
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    return REG_GENDER

async def reg_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ['male', 'female', 'other']:
        await update.message.reply_text("Please select from the buttons.")
        return REG_GENDER
    context.user_data['gender'] = gender
    keyboard = [['Patient', 'Doctor']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    lang = context.user_data.get('register_lang', 'en')
    msg = get_text("role_select", lang)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    return REG_ROLE

async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = update.message.text.lower()
    if role not in ['patient', 'doctor']:
        await update.message.reply_text("Please select Patient or Doctor.")
        return REG_ROLE
    context.user_data['role'] = role
    
    lang = context.user_data.get('register_lang', 'en')
    msg = get_text("set_password", lang)
    
    await update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 8:
        lang = context.user_data.get('register_lang', 'en')
        err_msg = get_text("error_pwd_length", lang)
        
        await update.message.reply_text(err_msg)
        return REG_PASSWORD
    try:
        await update.message.delete()
    except:
        pass

    context.user_data['password'] = password
    await update.message.reply_text("⏳ Creating account...")
    new_user = await BotService.register_new_user(context.user_data, update.effective_chat.id)
    
    lang = context.user_data.get('register_lang', 'en')
    
    if new_user:
        # Also Update Language Preference!
        BotService.update_user_language(new_user.id, lang)
        
        msg = get_text("reg_success", lang)
        # Add License info if Doctor - keeping basic for now or simple append
        if new_user.role == 'doctor':
             if new_user.verification_status == 'verified':
                 msg += "\n✅ License Verified."
             else:
                 msg += "\n⚠️ License Verification Pending."
                 
        await update.message.reply_text(msg, parse_mode="Markdown")
        BotLogService.log(update.effective_chat.id, "OUT", "registration", "User Registered successfully", new_user.id)
    else:
        err = get_text("error", lang)
        await update.message.reply_text(err)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔️ Process cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_auth_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHARE_CONTACT: [MessageHandler(filters.CONTACT, handle_contact)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_password)],
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_dob)],
            REG_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_gender)],
            REG_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_role)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

# ============================================================================
# OCR / BP Record Flow
# ============================================================================

async def handle_photo_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for Photo: Process and ask for confirmation."""
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ Please /start and link your account first.")
        return ConversationHandler.END

    photo_file = None
    if update.message.document:
        photo_file = await update.message.document.get_file()
    elif update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
    else:
        await update.message.reply_text("❌ No image found.")
        return ConversationHandler.END

    processing_msg = await update.message.reply_text("🔍 Analyzing image...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        temp_path = temp_file.name
        
    try:
        ocr_result = read_blood_pressure_with_gemini(temp_path)
        os.unlink(temp_path)
        
        if ocr_result.error:
            await processing_msg.edit_text(f"❌ Read Error: {ocr_result.error}\nPlease try again.")
            return ConversationHandler.END
            
        if not (ocr_result.systolic and ocr_result.diastolic and ocr_result.pulse):
            await processing_msg.edit_text("⚠️ Could not clearly read numbers. Please try again.")
            return ConversationHandler.END

        # Store in context
        context.user_data['ocr_temp'] = {
            "sys": ocr_result.systolic,
            "dia": ocr_result.diastolic,
            "pulse": ocr_result.pulse,
            "date": ocr_result.measurement_date,
            "time": ocr_result.measurement_time,
            "raw_source": ocr_result.raw_response, # To show source in confirmation if needed
            "user_id": user.id
        }
        
        # Format Date/Time for display
        dt_display = "Unknown"
        date_warning = ""
        
        if ocr_result.measurement_date and ocr_result.measurement_time:
             dt_display = f"{ocr_result.measurement_date} {ocr_result.measurement_time}"
             
             # Check if it was a fallback for DATE specifically
             if "Date: Fallback" in ocr_result.raw_response:
                 date_warning = "\n⚠️ **Date not found in image**, using current date."

        # Ask for confirmation
        # Get language
        lang = user.language or "en"
        
        msg = get_text("ocr_confirm", lang,
            sys=ocr_result.systolic,
            dia=ocr_result.diastolic,
            pulse=ocr_result.pulse,
            date=ocr_result.measurement_date,
            time=ocr_result.measurement_time
        )
        if date_warning:
             msg += f"\n({date_warning})"
             
        btn_confirm_txt = get_text("btn_confirm", lang)
        btn_edit_txt = get_text("btn_edit", lang)
        
        keyboard = [
            [
                InlineKeyboardButton(btn_confirm_txt, callback_data="save_ocr"),
                InlineKeyboardButton(btn_edit_txt, callback_data="edit_ocr")
            ]
        ]
        
        await processing_msg.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return OCR_CONFIRM

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        await processing_msg.edit_text("❌ System error.")
        return ConversationHandler.END

async def ocr_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "save_ocr":
        ocr_data = context.user_data.get('ocr_temp')
        if not ocr_data:
            await query.edit_message_text("❌ Session expired. Please upload again.")
            return ConversationHandler.END
            
        # Parse date/time strings to objects if needed, or pass as is if BotService handles it
        # BotService.create_bp_record currently takes separate args, assumes current time if not provided
        # I need to update BotService to accept measurement_date/time OR handle it here.
        # Let's inspect BotService.create_bp_record first. Assuming it uses now_th().
        # I should probably update BotService first to accept explicit date/time.
        # But for now, let's look at `create_bp_record` definition.
        # It takes `systolic`, `diastolic`, `pulse`, `notes`.
        # I should update BotService to accept `measurement_date` and `measurement_time` in kwargs or args.
        
        # Wait, I cannot see BotService definition here. I viewed it earlier?
        # Yes, step 832. create_bp_record: (user_id, systolic, diastolic, pulse, notes)
        # It uses `now_th()` inside. I need to UPDATE `BotService` to accept date/time.
        
        # I'll update BotService in the next step. For now, let's write this handler code assuming BotService is updated.
        
        # Get user lang
        user = BotService.get_user_by_telegram_id(ocr_data['user_id'])
        lang = user.language or "en" if user else "en"
        
        record, is_new = BotService.create_bp_record(
            user_id=ocr_data['user_id'],
            systolic=ocr_data['sys'],
            diastolic=ocr_data['dia'],
            pulse=ocr_data['pulse'],
            notes=f"Bot OCR ({ocr_data.get('raw_source', 'Confirmed')})",
            measurement_date=ocr_data.get('date'),
            measurement_time=ocr_data.get('time')
        )
        
        if is_new:
             msg = get_text("save_success", lang, sys=ocr_data['sys'], dia=ocr_data['dia'], pulse=ocr_data['pulse'])
             await query.edit_message_text(msg, parse_mode="Markdown")
             BotLogService.log(ocr_data['user_id'], "OUT", "save_ocr", "OCR Record Saved", ocr_data['user_id'])
        else:
             msg = get_text("save_duplicate", lang)
             await query.edit_message_text(msg, parse_mode="Markdown")
             
        return ConversationHandler.END
        
    elif data == "edit_ocr":
        await query.edit_message_text(
            "Please type the values in this format:\n"
            "**SYS/DIA PULSE**\n"
            "Example: `120/80 72`",
            parse_mode="Markdown"
        )
        return OCR_EDIT

async def ocr_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Parse generic "120/80 72" or "120 80 72"
    try:
        # Normalize separators
        text = text.replace("/", " ").replace("-", " ").replace(",", " ")
        parts = text.split()
        
        if len(parts) >= 3:
            sys = int(parts[0])
            dia = int(parts[1])
            pulse = int(parts[2])
            
            ocr_data = context.user_data.get('ocr_temp')
            user_id = ocr_data['user_id'] if ocr_data else BotService.get_user_by_telegram_id(update.effective_chat.id).id
            
            # Use current time for manual edit, or keep OCR time? 
            # Usually manual edit implies correcting numbers. Time usually remains valid from image.
            # But let's use the OCR time if available.
            m_date = ocr_data.get('date') if ocr_data else None
            m_time = ocr_data.get('time') if ocr_data else None
            
            BotService.create_bp_record(
                user_id=user_id,
                systolic=sys,
                diastolic=dia,
                pulse=pulse,
                notes="Bot Manual Entry",
                measurement_date=m_date,
                measurement_time=m_time
            )
            await update.message.reply_text("✅ **Record Saved Successfully!**", parse_mode="Markdown")
            BotLogService.log(user_id, "OUT", "save_manual", "Manual Record Saved", user_id)
            return ConversationHandler.END
        else:
            await update.message.reply_text("⚠️ Invalid format. Try: 120/80 72")
            return OCR_EDIT
    except ValueError:
        await update.message.reply_text("⚠️ Numbers only please. Try: 120/80 72")
        return OCR_EDIT

def get_ocr_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_photo_entry)],
        states={
            OCR_CONFIRM: [CallbackQueryHandler(ocr_confirm_callback)],
            OCR_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ocr_edit_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

# ============================================================================
# Stats
# ============================================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show simple stats."""
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ Please /start and link your account first.")
        return

    data = BotService.get_user_stats(user.id)
    recent = data['recent']
    avg = data['average']
    
    avg_sys = int(avg.avg_sys) if avg.avg_sys else 0
    avg_dia = int(avg.avg_dia) if avg.avg_dia else 0
    avg_pulse = int(avg.avg_pulse) if avg.avg_pulse else 0
    
    lang = user.language or "en"
    
    msg = get_text(
        "stats_header", 
        lang, 
        sys=avg_sys, 
        dia=avg_dia, 
        pulse=avg_pulse
    )

    if not recent:
        msg += "\n" + get_text("no_records", lang)
    else:
        for r in recent:
            date_str = r.measurement_date.strftime("%d/%m/%Y")
            time_str = r.measurement_time if r.measurement_time else ""
            msg += f"\n- {date_str} {time_str}: **{r.systolic}/{r.diastolic}** ({r.pulse})"
            
    await update.message.reply_text(msg, parse_mode="Markdown")
    BotLogService.log(chat_id, "OUT", "stats", "Stats sent", user.id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = user.language if user else "en"
    
    msg = get_text("help_msg", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to unknown messages."""
    await update.message.reply_text(
        "🤔 I didn't understand that.\n"
        "Type /help to see what I can do, or send a photo to record BP!"
    )

def get_ocr_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_entry)],
        states={
            OCR_CONFIRM: [CallbackQueryHandler(ocr_confirm_callback)],
            OCR_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ocr_edit_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

# ... inside main setup in main.py, we need to register these ...
# Wait, I am editing handlers.py, I need to make sure these are EXPORTED or used.
# The `main.py` likely imports specific functions or a setup function.
# Let me verify `app/bot/main.py` next to see how handlers are attached.
# For now, I'll add the functions here.
