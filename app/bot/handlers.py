
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from app.bot.services import BotService
from app.bot.log_service import BotLogService
from app.utils.ocr_helper import read_blood_pressure_with_gemini
from .locales import get_text
from telegram.constants import ChatAction
from datetime import datetime
import logging
import tempfile
import os
import re
import asyncio

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
        await query.edit_message_text(get_text("not_linked", "en"))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
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
        await query.edit_message_text(get_text("not_linked", "en"))
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
        await query.edit_message_text(get_text("not_linked", "en"))

logger = logging.getLogger(__name__)

# --- Auth States ---
CHOOSE_LANG = 7
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

# --- Manual BP States ---
MANUAL_BP_CONFIRM = 20

# --- Profile States ---
PROFILE_VIEW = 30
PROFILE_EDIT = 31

# --- Delete States ---
DELETE_SELECT = 40
DELETE_CONFIRM = 41

# --- Deactivate States ---
DEACTIVATE_CONFIRM = 50
DEACTIVATE_TYPE = 51

# --- Password States ---
PW_CHOICE = 60
PW_CURRENT = 61
PW_NEW = 62
PW_CONFIRM = 63
PW_OTP = 64
PW_NEW_AFTER_OTP = 65
PW_CONFIRM_AFTER_OTP = 66

# --- Broadcast States ---
BROADCAST_MSG = 70
BROADCAST_CONFIRM = 71

# --- Edit States ---
EDIT_SELECT = 80
EDIT_INPUT = 81

# Regex for manual BP input: 130/90/65 or 130-90-65 or 130 90 65
BP_TEXT_PATTERN = re.compile(r'^(\d{2,3})[/\-\s](\d{2,3})[/\-\s](\d{2,3})$')

# ============================================================================
# Auth / Registration Flow
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: Bilingual welcome, then language choice or welcome back."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # 0. Check for Deep Link (verify_TOKEN)
    if context.args and context.args[0].startswith("verify_"):
        token = context.args[0].replace("verify_", "")
        linked_user = BotService.process_connection_token(token, chat_id)

        if linked_user:
            lang = linked_user.language or "en"
            await update.message.reply_text(
                get_text("account_connected", lang, name=linked_user.full_name),
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(get_text("link_invalid", "en"))

    # 1. Check if already linked
    linked_user = BotService.get_user_by_telegram_id(chat_id)

    if linked_user:
        # Show bilingual welcome back
        msg = get_text("welcome_back_bilingual", "en", name=linked_user.full_name)
        webapp_url = os.getenv("TELEGRAM_WEBAPP_URL")
        if webapp_url:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("btn_record_bp", linked_user.language or "th"), web_app=WebAppInfo(url=webapp_url))],
            ])
            await update.message.reply_text(msg, reply_markup=keyboard)
        else:
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        BotLogService.log(user.id, "OUT", "welcome", "Welcome back (bilingual)", linked_user.id)
        return ConversationHandler.END

    # 2. Not linked -> Show bilingual welcome + language selection
    msg = get_text("welcome_bilingual", "en")
    msg += "\n\n" + get_text("choose_lang_prompt", "en")

    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="start_lang_en")],
        [InlineKeyboardButton("🇹🇭 ไทย", callback_data="start_lang_th")]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSE_LANG

async def choose_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language choice during /start flow."""
    query = update.callback_query
    await query.answer()

    data = query.data  # "start_lang_en" or "start_lang_th"
    lang = "en" if data == "start_lang_en" else "th"

    # Store chosen language for registration flow
    context.user_data['register_lang'] = lang

    # Confirm language choice
    msg = get_text("lang_chosen", lang)
    await query.edit_message_text(msg)

    # Send contact request as a new message (can't mix inline keyboard edit with reply keyboard)
    contact_btn_text = get_text("share_contact_btn", lang)
    contact_keyboard = KeyboardButton(text=contact_btn_text, request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_keyboard]], one_time_keyboard=True, resize_keyboard=True)

    welcome_msg = get_text("welcome_new", lang, name=update.effective_user.first_name)
    await query.message.reply_text(welcome_msg, reply_markup=reply_markup)

    return SHARE_CONTACT


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    lang = context.user_data.get('register_lang', 'en')
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text(get_text("wrong_contact", lang))
        return SHARE_CONTACT

    phone_number = contact.phone_number
    if phone_number.startswith("+"):
        phone_number = phone_number[1:]

    context.user_data['phone_number'] = phone_number
    existing_user = BotService.get_user_by_phone(phone_number)

    if existing_user:
        context.user_data['user_id'] = existing_user.id

        # Use language chosen at CHOOSE_LANG step (not from DB)
        msg = get_text("found_account", lang, phone=phone_number)

        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        context.user_data['_auth_state'] = 'auth_password'  # Next input: password
        return AUTH_PASSWORD
    else:
        # Use language chosen at /start (CHOOSE_LANG step)
        lang = context.user_data.get('register_lang', 'en')

        msg = get_text("new_account", lang, phone=phone_number)
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        context.user_data['_auth_state'] = 'reg_name'  # Next input: full name
        return REG_NAME

async def auth_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    phone_number = context.user_data.get('phone_number')
    lang = context.user_data.get('register_lang', 'en')
    try:
        await update.message.delete()
    except:
        pass

    user = BotService.verify_user_password(phone_number, password)
    if user:
        BotService.link_telegram_account(user.id, update.effective_chat.id)
        # Save language choice to DB
        BotService.update_user_language(user.id, lang)
        await update.message.reply_text(get_text("link_success", lang))
        context.user_data.pop('_auth_state', None)  # Clear auth state
        return ConversationHandler.END
    else:
        await update.message.reply_text(get_text("link_fail_password", lang))
        context.user_data['_auth_state'] = 'auth_password'  # Still expecting password
        return AUTH_PASSWORD

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    lang = context.user_data.get('register_lang', 'en')

    msg = get_text("enter_dob", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")
    context.user_data['_auth_state'] = 'reg_dob'  # Next input: date of birth
    return REG_DOB

async def reg_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get('register_lang', 'en')
    try:
        dob = datetime.strptime(text, "%d/%m/%Y")
        context.user_data['date_of_birth'] = dob
    except ValueError:
        await update.message.reply_text(get_text("dob_invalid", lang))
        context.user_data['_auth_state'] = 'reg_dob'  # Still expecting DOB
        return REG_DOB

    msg = get_text("enter_gender", lang)

    # Localized gender buttons
    gender_labels = [
        get_text("gender_male", lang),
        get_text("gender_female", lang),
        get_text("gender_other", lang)
    ]
    keyboard = [gender_labels]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data['_auth_state'] = 'reg_gender'  # Next input: gender selection
    return REG_GENDER

async def reg_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender_text = update.message.text.strip()
    lang = context.user_data.get('register_lang', 'en')

    # Reverse map: localized label -> standardized EN value
    gender_map = {
        get_text("gender_male", lang).lower(): "male",
        get_text("gender_female", lang).lower(): "female",
        get_text("gender_other", lang).lower(): "other",
        # Also accept raw EN values
        "male": "male", "female": "female", "other": "other",
    }

    gender = gender_map.get(gender_text.lower())
    if not gender:
        await update.message.reply_text(get_text("gender_invalid", lang))
        return REG_GENDER

    context.user_data['gender'] = gender

    # Localized role buttons
    role_labels = [get_text("role_patient", lang), get_text("role_doctor", lang)]
    keyboard = [role_labels]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    msg = get_text("role_select", lang)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data['_auth_state'] = 'reg_role'  # Next input: role selection
    return REG_ROLE

async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role_text = update.message.text.strip()
    lang = context.user_data.get('register_lang', 'en')

    # Reverse map: localized label -> standardized EN value
    role_map = {
        get_text("role_patient", lang).lower(): "patient",
        get_text("role_doctor", lang).lower(): "doctor",
        # Also accept raw EN values
        "patient": "patient", "doctor": "doctor",
    }

    role = role_map.get(role_text.lower())
    if not role:
        await update.message.reply_text(get_text("role_invalid", lang))
        return REG_ROLE

    context.user_data['role'] = role

    msg = get_text("set_password", lang)

    await update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    context.user_data['_auth_state'] = 'reg_password'  # Next input: password
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 8:
        lang = context.user_data.get('register_lang', 'en')
        err_msg = get_text("error_pwd_length", lang)

        await update.message.reply_text(err_msg)
        context.user_data['_auth_state'] = 'reg_password'  # Still expecting password
        return REG_PASSWORD
    try:
        await update.message.delete()
    except:
        pass

    context.user_data['password'] = password
    lang = context.user_data.get('register_lang', 'en')

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    await update.message.reply_text(get_text("creating_account", lang))
    new_user = await BotService.register_new_user(context.user_data, update.effective_chat.id)
    
    lang = context.user_data.get('register_lang', 'en')
    
    if new_user:
        # Also Update Language Preference!
        BotService.update_user_language(new_user.id, lang)
        
        msg = get_text("reg_success", lang)
        # Add License info if Doctor - keeping basic for now or simple append
        if new_user.role == 'doctor':
             if new_user.verification_status == 'verified':
                 msg += get_text("license_verified", lang)
             else:
                 msg += get_text("license_pending", lang)
                 
        await update.message.reply_text(msg, parse_mode="Markdown")
        BotLogService.log(update.effective_chat.id, "OUT", "registration", "User Registered successfully", new_user.id)
    else:
        err = get_text("error", lang)
        await update.message.reply_text(err)
    context.user_data.pop('_auth_state', None)  # Clear auth state
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('_auth_state', None)  # Clear auth state
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"
    await update.message.reply_text(get_text("cancelled", lang), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_auth_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_LANG: [CallbackQueryHandler(choose_lang_callback, pattern='^start_lang_')],
            SHARE_CONTACT: [MessageHandler(filters.CONTACT, handle_contact)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_password)],
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_dob)],
            REG_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_gender)],
            REG_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_role)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,  # 5 minutes
        allow_reentry=True,  # Allow /start to restart if stuck
    )

# ============================================================================
# OCR / BP Record Flow
# ============================================================================

async def handle_photo_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for Photo: Process and ask for confirmation."""
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    photo_file = None
    file_ext = ".jpg"  # default for photos sent as photo (Telegram converts to JPEG)

    if update.message.document:
        doc = update.message.document
        # Validate MIME type
        if doc.mime_type and not doc.mime_type.startswith("image/"):
            await update.message.reply_text(get_text("invalid_image", lang))
            return ConversationHandler.END

        # Extract correct file extension from original filename or MIME type
        if doc.file_name:
            _, ext = os.path.splitext(doc.file_name)
            if ext:
                file_ext = ext.lower()
        elif doc.mime_type:
            mime_ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png",
                "image/webp": ".webp", "image/gif": ".gif",
                "image/bmp": ".bmp", "image/tiff": ".tiff",
                "image/heic": ".heic", "image/heif": ".heif",
            }
            file_ext = mime_ext_map.get(doc.mime_type, ".jpg")

        photo_file = await doc.get_file()
    elif update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
    else:
        await update.message.reply_text(get_text("no_image", lang))
        return ConversationHandler.END

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    processing_msg = await update.message.reply_text(get_text("analyzing_image", lang))

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        temp_path = temp_file.name

    # Convert HEIC/HEIF to JPEG if needed (PIL doesn't support HEIC natively)
    if file_ext.lower() in (".heic", ".heif"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            # If pillow-heif not installed, try converting with subprocess (sips on macOS)
            try:
                import subprocess
                converted_path = temp_path.rsplit(".", 1)[0] + ".jpg"
                subprocess.run(["sips", "-s", "format", "jpeg", temp_path, "--out", converted_path],
                              capture_output=True, timeout=10)
                if os.path.exists(converted_path):
                    os.unlink(temp_path)
                    temp_path = converted_path
            except Exception:
                os.unlink(temp_path)
                await processing_msg.edit_text(get_text("heic_not_supported", lang))
                return ConversationHandler.END

    try:
        ocr_result = read_blood_pressure_with_gemini(temp_path)
        os.unlink(temp_path)

        if ocr_result.error:
            await processing_msg.edit_text(get_text("ocr_read_error", lang, error=ocr_result.error))
            return ConversationHandler.END

        if not (ocr_result.systolic and ocr_result.diastolic and ocr_result.pulse):
            await processing_msg.edit_text(get_text("ocr_no_values", lang))
            return ConversationHandler.END

        # Store in context
        context.user_data['ocr_temp'] = {
            "sys": ocr_result.systolic,
            "dia": ocr_result.diastolic,
            "pulse": ocr_result.pulse,
            "date": ocr_result.measurement_date,
            "time": ocr_result.measurement_time,
            "raw_source": ocr_result.raw_response,
            "user_id": user.id
        }

        # Format Date/Time for display
        date_warning = ""
        if ocr_result.measurement_date and ocr_result.measurement_time:
             # Check if it was a fallback for DATE specifically
             if "Date: Fallback" in ocr_result.raw_response:
                 date_warning = get_text("ocr_date_fallback", lang)

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

        # Schedule auto-save job (2 min) — Approach C
        if context.job_queue:
            job_name = f"ocr_autosave_{chat_id}"
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()

            context.job_queue.run_once(
                ocr_auto_save_job,
                when=120,
                chat_id=chat_id,
                name=job_name,
                data={
                    "ocr_data": context.user_data['ocr_temp'].copy(),
                    "lang": lang,
                }
            )

        return OCR_CONFIRM

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        await processing_msg.edit_text(get_text("error", lang))
        return ConversationHandler.END

async def ocr_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Cancel auto-save job since user responded
    if context.job_queue:
        job_name = f"ocr_autosave_{update.effective_chat.id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()

    data = query.data
    
    if data == "save_ocr":
        ocr_data = context.user_data.get('ocr_temp')
        if not ocr_data:
            user = BotService.get_user_by_telegram_id(update.effective_user.id)
            lang = (user.language or "en") if user else "en"
            await query.edit_message_text(get_text("session_expired", lang))
            return ConversationHandler.END

        # Get user lang via telegram_id (not DB user_id)
        user = BotService.get_user_by_telegram_id(update.effective_user.id)
        lang = (user.language or "en") if user else "en"
        
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
        user = BotService.get_user_by_telegram_id(update.effective_user.id)
        lang = (user.language or "en") if user else "en"
        await query.edit_message_text(
            get_text("ocr_edit_prompt", lang),
            parse_mode="Markdown"
        )
        return OCR_EDIT

async def ocr_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Cancel auto-save job since user is editing
    if context.job_queue:
        job_name = f"ocr_autosave_{update.effective_chat.id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()

    text = update.message.text.strip()
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    try:
        # Normalize separators
        text = text.replace("/", " ").replace("-", " ").replace(",", " ")
        parts = text.split()

        if len(parts) >= 3:
            sys_val = int(parts[0])
            dia_val = int(parts[1])
            pulse_val = int(parts[2])

            ocr_data = context.user_data.get('ocr_temp')
            user_id = ocr_data['user_id'] if ocr_data else user.id

            m_date = ocr_data.get('date') if ocr_data else None
            m_time = ocr_data.get('time') if ocr_data else None

            record, is_new = BotService.create_bp_record(
                user_id=user_id,
                systolic=sys_val,
                diastolic=dia_val,
                pulse=pulse_val,
                notes="Bot OCR Edit",
                measurement_date=m_date,
                measurement_time=m_time
            )
            if is_new:
                msg = get_text("save_success", lang, sys=sys_val, dia=dia_val, pulse=pulse_val)
            else:
                msg = get_text("save_duplicate", lang)
            await update.message.reply_text(msg, parse_mode="Markdown")
            BotLogService.log(user_id, "OUT", "save_ocr_edit", f"OCR Edit: {sys_val}/{dia_val}/{pulse_val}", user_id)
            return ConversationHandler.END
        else:
            await update.message.reply_text(get_text("ocr_edit_invalid", lang))
            return OCR_EDIT
    except ValueError:
        await update.message.reply_text(get_text("ocr_edit_invalid", lang))
        return OCR_EDIT

# ============================================================================
# OCR Auto-Save Job (Approach C)
# ============================================================================

async def ocr_auto_save_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-save OCR data when user doesn't confirm within timeout."""
    job = context.job
    ocr_data = job.data['ocr_data']
    lang = job.data['lang']
    chat_id = job.chat_id

    try:
        record, is_new = BotService.create_bp_record(
            user_id=ocr_data['user_id'],
            systolic=ocr_data['sys'],
            diastolic=ocr_data['dia'],
            pulse=ocr_data['pulse'],
            notes=f"Bot OCR Auto-save (timeout)",
            measurement_date=ocr_data.get('date'),
            measurement_time=ocr_data.get('time')
        )

        if is_new:
            msg = get_text("ocr_auto_saved", lang,
                sys=ocr_data['sys'], dia=ocr_data['dia'], pulse=ocr_data['pulse'])
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

        BotLogService.log(ocr_data['user_id'], "OUT", "auto_save_ocr",
            f"OCR Auto-saved: {ocr_data['sys']}/{ocr_data['dia']}/{ocr_data['pulse']}",
            ocr_data['user_id'])
    except Exception as e:
        logger.error(f"OCR auto-save error: {e}")


# ============================================================================
# Stats
# ============================================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show simple stats + BP trend chart image."""
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    data = BotService.get_user_stats(user.id)
    recent = data['recent']
    avg = data['average']

    if not avg:
        lang = user.language or "en"
        await update.message.reply_text(get_text("no_records", lang))
        BotLogService.log(chat_id, "OUT", "stats", "No records", user.id)
        return

    import math
    # Use math.floor(x + 0.5) for half-up rounding (matches JavaScript Math.round)
    avg_sys = math.floor(avg.avg_sys + 0.5) if avg.avg_sys else 0
    avg_dia = math.floor(avg.avg_dia + 0.5) if avg.avg_dia else 0
    avg_pulse = math.floor(avg.avg_pulse + 0.5) if avg.avg_pulse else 0

    lang = user.language or "en"

    total_records = len(recent) if recent else 0

    msg = get_text(
        "stats_header",
        lang,
        sys=avg_sys,
        dia=avg_dia,
        pulse=avg_pulse,
        n=total_records
    )

    # BP Classification (Free + Premium)
    classification = data.get("classification")
    if classification:
        label = classification["label_th"] if lang == "th" else classification["label_en"]
        level = classification["level"]
        emoji = {"normal": "🟢", "elevated": "🟡", "stage_1": "🟠", "stage_2": "🔴", "hypertensive_crisis": "🚨"}.get(level, "⚪")
        msg += f"\n{emoji} {get_text('stats_classification', lang)}: **{label}**"

    # Advanced stats (Premium only)
    advanced = data.get("advanced")
    if advanced:
        sd_sys = advanced["sd_sys"]
        sd_dia = advanced["sd_dia"]
        pp = advanced["pulse_pressure"]
        map_val = advanced["map"]
        trend = advanced["trend"]

        trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(trend["direction"], "➡️")
        trend_label = get_text(f"stats_trend_{trend['direction']}", lang)

        msg += f"\n\n{get_text('stats_advanced_header', lang)}"
        msg += f"\n• SD: {avg_sys} ± {sd_sys} / {avg_dia} ± {sd_dia} mmHg"
        msg += f"\n• Pulse Pressure: {pp} mmHg"
        msg += f"\n• MAP: {map_val} mmHg"
        msg += f"\n• {get_text('stats_trend', lang)}: {trend_emoji} {trend_label} ({trend['systolic_slope']:+.1f} mmHg/{get_text('stats_per_day', lang)})"
    elif not data.get("is_premium"):
        msg += f"\n\n🔒 {get_text('stats_premium_hint', lang)}"

    if recent:
        display_limit = 10
        shown = min(len(recent), display_limit)
        msg += f"\n\n{get_text('stats_latest', lang)} ({shown}/{total_records})"
        for r in recent[:display_limit]:
            date_str = r.measurement_date.strftime("%d/%m/%Y")
            time_str = r.measurement_time if r.measurement_time else ""
            msg += f"\n- {date_str} {time_str}: **{r.systolic}/{r.diastolic}** ({r.pulse})"

        # Hint for viewing more (only when truncated)
        if total_records > display_limit:
            dashboard_url = os.getenv("WEB_DASHBOARD_URL", "")
            if dashboard_url:
                msg += f"\n\n{get_text('stats_view_more', lang, url=dashboard_url)}"
            else:
                msg += f"\n\n{get_text('stats_view_more_no_url', lang)}"

    # Always show Mini App button + Dashboard link
    webapp_url = os.getenv("TELEGRAM_WEBAPP_URL")
    dashboard_url = os.getenv("WEB_DASHBOARD_URL", "")

    buttons = []
    if webapp_url:
        buttons.append([InlineKeyboardButton(get_text("btn_record_bp", lang), web_app=WebAppInfo(url=webapp_url))])
    if dashboard_url:
        buttons.append([InlineKeyboardButton("🌐 Dashboard", url=dashboard_url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

    # Send BP trend chart image (if ≥ 2 records)
    if recent and len(recent) >= 2:
        try:
            await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        except Exception:
            pass
        try:
            from app.utils.chart_generator import generate_bp_chart
            chart_buffer = generate_bp_chart(recent, lang=lang)
            caption = "📊 Blood Pressure Trends" if lang == "en" else "📊 กราฟความดันโลหิต"
            await update.message.reply_photo(photo=chart_buffer, caption=caption)
        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            # Don't fail the whole command — text stats were already sent

    BotLogService.log(chat_id, "OUT", "stats", "Stats sent", user.id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = user.language if user else "en"
    
    msg = get_text("help_msg", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def bp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open BP recording Mini App via WebApp button."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return

    lang = user.language or "en"
    webapp_url = os.getenv("TELEGRAM_WEBAPP_URL")

    if not webapp_url:
        await update.message.reply_text(get_text("bp_webapp_unavailable", lang))
        return

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


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to unknown messages."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = user.language if user else "en"
    await update.message.reply_text(get_text("unknown_msg", lang), parse_mode="Markdown")

# ============================================================================
# Manual BP Text Input (e.g., 130/90/65 or 130-90-65 or 130 90 65)
# ============================================================================

async def manual_bp_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse text like 130/90/65 or 130 90 65 and show confirmation with inline buttons."""
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)

    if not user:
        return ConversationHandler.END

    lang = user.language or "en"
    text = update.message.text.strip()

    match = BP_TEXT_PATTERN.match(text)
    if not match:
        await update.message.reply_text(get_text("manual_bp_invalid_format", lang), parse_mode="Markdown")
        return ConversationHandler.END

    sys_val = int(match.group(1))
    dia_val = int(match.group(2))
    pulse_val = int(match.group(3))

    # Validate ranges
    if not (50 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pulse_val <= 200):
        await update.message.reply_text(get_text("manual_bp_out_of_range", lang))
        return ConversationHandler.END

    # Use message timestamp as measurement date/time (convert to user timezone)
    import pytz
    msg_date = update.message.date  # UTC datetime
    user_tz = pytz.timezone(user.timezone or "Asia/Bangkok")
    local_dt = msg_date.astimezone(user_tz)

    date_str = local_dt.strftime("%Y-%m-%d")
    time_str = local_dt.strftime("%H:%M")
    date_display = local_dt.strftime("%d/%m/%Y")

    # Store in context for confirmation
    context.user_data['manual_bp_temp'] = {
        "sys": sys_val,
        "dia": dia_val,
        "pulse": pulse_val,
        "date": date_str,
        "time": time_str,
        "user_id": user.id
    }

    msg = get_text("manual_bp_confirm", lang,
        sys=sys_val, dia=dia_val, pulse=pulse_val,
        date=date_display, time=time_str
    )

    btn_confirm = get_text("btn_confirm", lang)
    btn_cancel = get_text("btn_cancel", lang)

    keyboard = [
        [
            InlineKeyboardButton(btn_confirm, callback_data="manual_bp_save"),
            InlineKeyboardButton(btn_cancel, callback_data="manual_bp_cancel")
        ]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MANUAL_BP_CONFIRM


async def manual_bp_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirm/cancel for manual BP entry."""
    query = update.callback_query
    await query.answer()

    data = query.data
    bp_data = context.user_data.get('manual_bp_temp')

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if not bp_data:
        await query.edit_message_text(get_text("session_expired", lang))
        return ConversationHandler.END

    if data == "manual_bp_save":
        try:
            await query.message.chat.send_action(ChatAction.TYPING)
        except Exception:
            pass

        record, is_new = BotService.create_bp_record(
            user_id=bp_data['user_id'],
            systolic=bp_data['sys'],
            diastolic=bp_data['dia'],
            pulse=bp_data['pulse'],
            notes="Bot Manual Text Entry",
            measurement_date=bp_data.get('date'),
            measurement_time=bp_data.get('time')
        )

        if is_new:
            msg = get_text("manual_bp_saved", lang,
                sys=bp_data['sys'], dia=bp_data['dia'], pulse=bp_data['pulse'])
        else:
            msg = get_text("save_duplicate", lang)

        await query.edit_message_text(msg, parse_mode="Markdown")
        BotLogService.log(bp_data['user_id'], "OUT", "save_manual_text",
                         f"Manual BP: {bp_data['sys']}/{bp_data['dia']}/{bp_data['pulse']}", bp_data['user_id'])

    elif data == "manual_bp_cancel":
        msg = get_text("manual_bp_cancelled", lang)
        await query.edit_message_text(msg)

    # Clean up
    context.user_data.pop('manual_bp_temp', None)
    return ConversationHandler.END


def get_manual_bp_handler():
    """ConversationHandler for manual text-based BP input."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(BP_TEXT_PATTERN) & ~filters.COMMAND,
                manual_bp_entry
            )
        ],
        states={
            MANUAL_BP_CONFIRM: [
                CallbackQueryHandler(manual_bp_confirm_callback, pattern='^manual_bp_')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        conversation_timeout=120,  # 2 minutes
    )


def get_ocr_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_entry)],
        states={
            OCR_CONFIRM: [CallbackQueryHandler(ocr_confirm_callback)],
            OCR_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ocr_edit_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        conversation_timeout=180,  # 3 minutes
    )


# ============================================================================
# /profile — View / Edit Profile
# ============================================================================

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with edit buttons."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    profile = BotService.get_user_profile(user.id)
    if not profile:
        await update.message.reply_text(get_text("error", lang))
        return ConversationHandler.END

    msg = get_text("profile_title", lang) + "\n\n"
    msg += get_text("profile_info", lang,
        name=profile["name"], phone=profile["phone"], email=profile["email"],
        gender=profile["gender"], dob=profile["dob"], role=profile["role"],
        tz=profile["timezone"], sub=profile["subscription"]
    )

    keyboard = [
        [
            InlineKeyboardButton(get_text("btn_edit_name", lang), callback_data="profile_edit_name"),
            InlineKeyboardButton(get_text("btn_edit_email", lang), callback_data="profile_edit_email"),
        ],
        [InlineKeyboardButton(get_text("btn_close", lang), callback_data="profile_edit_close")]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return PROFILE_VIEW


async def profile_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile edit button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await query.edit_message_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"

    if data == "profile_edit_close":
        await query.edit_message_text(get_text("profile_no_change", lang))
        return ConversationHandler.END

    if data == "profile_edit_name":
        context.user_data['profile_edit_field'] = 'name'
        context.user_data['profile_user_id'] = user.id
        await query.edit_message_text(get_text("profile_edit_name", lang), parse_mode="Markdown")
        return PROFILE_EDIT

    if data == "profile_edit_email":
        context.user_data['profile_edit_field'] = 'email'
        context.user_data['profile_user_id'] = user.id
        await query.edit_message_text(get_text("profile_edit_email", lang), parse_mode="Markdown")
        return PROFILE_EDIT

    return ConversationHandler.END


async def profile_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for profile editing."""
    text = update.message.text.strip()
    field = context.user_data.get('profile_edit_field')
    user_id = context.user_data.get('profile_user_id')

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    if field == 'name':
        success = BotService.update_user_name(user_id, text)
        if success:
            await update.message.reply_text(get_text("profile_updated", lang))
        else:
            await update.message.reply_text(get_text("error", lang))
        return ConversationHandler.END

    if field == 'email':
        success = BotService.update_user_email(user_id, text)
        if success:
            await update.message.reply_text(get_text("profile_updated", lang))
        else:
            await update.message.reply_text(get_text("profile_invalid_email", lang))
            return PROFILE_EDIT

    return ConversationHandler.END


def get_profile_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("profile", profile_command)],
        states={
            PROFILE_VIEW: [CallbackQueryHandler(profile_edit_callback, pattern='^profile_edit_')],
            PROFILE_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_edit_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=120,
        allow_reentry=True,
    )


# ============================================================================
# /delete — Delete BP Records
# ============================================================================

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent records for deletion."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    records = BotService.get_recent_records(user.id, limit=10)

    if not records:
        await update.message.reply_text(get_text("delete_no_records", lang))
        return ConversationHandler.END

    context.user_data['delete_user_id'] = user.id

    msg = get_text("delete_title", lang)
    keyboard = []
    for r in records:
        label = f"{r['date']} {r['time']} — {r['sys']}/{r['dia']} ({r['pulse']})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"del_select_{r['id']}")])

    keyboard.append([InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="del_select_cancel")])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return DELETE_SELECT


async def delete_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle record selection for deletion."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if data == "del_select_cancel":
        await query.edit_message_text(get_text("delete_cancelled", lang))
        return ConversationHandler.END

    record_id = int(data.replace("del_select_", ""))
    context.user_data['delete_record_id'] = record_id

    # Fetch record details for confirmation
    records = BotService.get_recent_records(context.user_data.get('delete_user_id', 0))
    record = next((r for r in records if r['id'] == record_id), None)

    if not record:
        await query.edit_message_text(get_text("error", lang))
        return ConversationHandler.END

    msg = get_text("delete_confirm", lang,
        date=record['date'], time=record['time'],
        sys=record['sys'], dia=record['dia'], pulse=record['pulse']
    )

    keyboard = [
        [
            InlineKeyboardButton("🗑 " + (get_text("btn_confirm", lang)), callback_data="del_confirm_yes"),
            InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="del_confirm_no")
        ]
    ]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return DELETE_CONFIRM


async def delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deletion confirmation."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if data == "del_confirm_yes":
        record_id = context.user_data.get('delete_record_id')
        user_id = context.user_data.get('delete_user_id')
        result = BotService.delete_bp_record(user_id, record_id)
        if result:
            await query.edit_message_text(get_text("delete_success", lang))
        else:
            await query.edit_message_text(get_text("error", lang))
    else:
        await query.edit_message_text(get_text("delete_cancelled", lang))

    context.user_data.pop('delete_record_id', None)
    context.user_data.pop('delete_user_id', None)
    return ConversationHandler.END


def get_delete_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("delete", delete_command)],
        states={
            DELETE_SELECT: [CallbackQueryHandler(delete_select_callback, pattern='^del_select_')],
            DELETE_CONFIRM: [CallbackQueryHandler(delete_confirm_callback, pattern='^del_confirm_')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=120,
        allow_reentry=True,
    )


# ============================================================================
# /edit — Edit BP Record
# ============================================================================

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent records for editing."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    records = BotService.get_recent_records(user.id, limit=10)

    if not records:
        await update.message.reply_text(get_text("edit_no_records", lang))
        return ConversationHandler.END

    context.user_data['edit_user_id'] = user.id

    msg = get_text("edit_title", lang)
    keyboard = []
    for r in records:
        label = f"{r['date']} {r['time']} — {r['sys']}/{r['dia']} ({r['pulse']})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_select_{r['id']}")])

    keyboard.append([InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="edit_select_cancel")])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EDIT_SELECT


async def edit_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle record selection for editing."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if data == "edit_select_cancel":
        await query.edit_message_text(get_text("edit_cancelled", lang))
        return ConversationHandler.END

    record_id = int(data.replace("edit_select_", ""))
    context.user_data['edit_record_id'] = record_id

    # Show current values and ask for new ones
    records = BotService.get_recent_records(context.user_data.get('edit_user_id', 0))
    record = next((r for r in records if r['id'] == record_id), None)

    if not record:
        await query.edit_message_text(get_text("error", lang))
        return ConversationHandler.END

    msg = get_text("edit_prompt", lang,
        date=record['date'], time=record['time'],
        sys=record['sys'], dia=record['dia'], pulse=record['pulse']
    )

    await query.edit_message_text(msg, parse_mode="Markdown")
    return EDIT_INPUT


async def edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new values input for editing."""
    text = update.message.text.strip()
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    try:
        # Normalize separators (accept / - space ,)
        text = text.replace("/", " ").replace("-", " ").replace(",", " ")
        parts = text.split()

        if len(parts) >= 3:
            sys_val = int(parts[0])
            dia_val = int(parts[1])
            pulse_val = int(parts[2])

            # Validate ranges
            if not (50 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pulse_val <= 200):
                await update.message.reply_text(get_text("manual_bp_out_of_range", lang))
                return EDIT_INPUT

            record_id = context.user_data.get('edit_record_id')
            user_id = context.user_data.get('edit_user_id')

            success = BotService.update_bp_record(user_id, record_id, sys_val, dia_val, pulse_val)
            if success:
                msg = get_text("edit_success", lang, sys=sys_val, dia=dia_val, pulse=pulse_val)
                await update.message.reply_text(msg, parse_mode="Markdown")
                BotLogService.log(user_id, "OUT", "edit_record",
                    f"Edit #{record_id}: {sys_val}/{dia_val}/{pulse_val}", user_id)
            else:
                await update.message.reply_text(get_text("error", lang))

            context.user_data.pop('edit_record_id', None)
            context.user_data.pop('edit_user_id', None)
            return ConversationHandler.END
        else:
            await update.message.reply_text(get_text("edit_invalid_format", lang))
            return EDIT_INPUT
    except ValueError:
        await update.message.reply_text(get_text("edit_invalid_format", lang))
        return EDIT_INPUT


def get_edit_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("edit", edit_command)],
        states={
            EDIT_SELECT: [CallbackQueryHandler(edit_select_callback, pattern='^edit_select_')],
            EDIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=120,
        allow_reentry=True,
    )


# ============================================================================
# /password — Change / Reset Password
# ============================================================================

async def password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show password management options."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    context.user_data['pw_user_id'] = user.id

    msg = get_text("password_title", lang)
    keyboard = [
        [InlineKeyboardButton(get_text("btn_change_pw", lang), callback_data="pw_change")],
        [InlineKeyboardButton(get_text("btn_forgot_pw", lang), callback_data="pw_forgot")],
        [InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="pw_cancel")]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return PW_CHOICE


async def password_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle password action choice."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if data == "pw_cancel":
        await query.edit_message_text(get_text("cancel", lang))
        return ConversationHandler.END

    if data == "pw_change":
        context.user_data['_auth_state'] = 'password'
        await query.edit_message_text(get_text("password_enter_current", lang), parse_mode="Markdown")
        return PW_CURRENT

    if data == "pw_forgot":
        # Send OTP to user's registered contact
        user_id = context.user_data.get('pw_user_id')
        contact = BotService.get_user_contact_for_otp(user_id)
        if contact:
            try:
                from app.otp_service import otp_service
                target = contact['email'] or contact['phone']
                if target:
                    purpose = "password_reset"
                    otp_service.generate_and_send(target, purpose)
                    context.user_data['pw_otp_target'] = target
                    await query.edit_message_text(get_text("password_otp_sent", lang))
                    context.user_data['_auth_state'] = 'password'
                    return PW_OTP
            except Exception as e:
                logger.error(f"OTP send error: {e}")
        await query.edit_message_text(get_text("error", lang))
        return ConversationHandler.END

    return ConversationHandler.END


async def password_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify current password."""
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    # Verify current password
    from app.utils.security import verify_password
    from app.database import SessionLocal
    from app.models import User

    user_id = context.user_data.get('pw_user_id')
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user and verify_password(password, db_user.password_hash):
            await update.message.reply_text(get_text("password_enter_new", lang), parse_mode="Markdown")
            return PW_NEW
        else:
            await update.message.reply_text(get_text("password_wrong_current", lang))
            return PW_CURRENT


async def password_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive new password."""
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    if len(password) < 8:
        await update.message.reply_text(get_text("password_too_short", lang))
        return PW_NEW

    context.user_data['pw_new'] = password
    await update.message.reply_text(get_text("password_confirm_new", lang), parse_mode="Markdown")
    return PW_CONFIRM


async def password_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm new password and save."""
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    new_pw = context.user_data.get('pw_new')
    if password != new_pw:
        await update.message.reply_text(get_text("password_mismatch", lang))
        return PW_NEW

    user_id = context.user_data.get('pw_user_id')
    # Use change_password with the verified current password path
    # Since we already verified, use reset_password_direct
    success = BotService.reset_password_direct(user_id, new_pw)
    if success:
        await update.message.reply_text(get_text("password_success", lang))
    else:
        await update.message.reply_text(get_text("error", lang))

    context.user_data.pop('pw_new', None)
    context.user_data.pop('_auth_state', None)
    return ConversationHandler.END


async def password_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify OTP for password reset."""
    otp_code = update.message.text.strip()

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    try:
        from app.otp_service import otp_service
        target = context.user_data.get('pw_otp_target')
        if target and otp_service.verify(target, otp_code, "password_reset"):
            await update.message.reply_text(get_text("password_enter_new", lang), parse_mode="Markdown")
            return PW_NEW_AFTER_OTP
    except Exception as e:
        logger.error(f"OTP verify error: {e}")

    await update.message.reply_text(get_text("password_otp_invalid", lang))
    return PW_OTP


async def password_new_after_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """New password after OTP verification."""
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    if len(password) < 8:
        await update.message.reply_text(get_text("password_too_short", lang))
        return PW_NEW_AFTER_OTP

    context.user_data['pw_new'] = password
    await update.message.reply_text(get_text("password_confirm_new", lang), parse_mode="Markdown")
    return PW_CONFIRM_AFTER_OTP


async def password_confirm_after_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm new password after OTP reset."""
    password = update.message.text
    try:
        await update.message.delete()
    except Exception:
        pass

    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    new_pw = context.user_data.get('pw_new')
    if password != new_pw:
        await update.message.reply_text(get_text("password_mismatch", lang))
        return PW_NEW_AFTER_OTP

    user_id = context.user_data.get('pw_user_id')
    success = BotService.reset_password_direct(user_id, new_pw)
    if success:
        await update.message.reply_text(get_text("password_success", lang))
    else:
        await update.message.reply_text(get_text("error", lang))

    context.user_data.pop('pw_new', None)
    context.user_data.pop('_auth_state', None)
    return ConversationHandler.END


def get_password_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("password", password_command)],
        states={
            PW_CHOICE: [CallbackQueryHandler(password_choice_callback, pattern='^pw_')],
            PW_CURRENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_current)],
            PW_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_new)],
            PW_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_confirm)],
            PW_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_otp)],
            PW_NEW_AFTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_new_after_otp)],
            PW_CONFIRM_AFTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_confirm_after_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )


# ============================================================================
# /deactivate — Account Deactivation
# ============================================================================

async def deactivate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deactivation warning."""
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "en"
    context.user_data['deactivate_user_id'] = user.id
    context.user_data['deactivate_lang'] = lang

    msg = get_text("deactivate_warning", lang)
    keyboard = [
        [InlineKeyboardButton(get_text("btn_confirm_deactivate", lang), callback_data="deactivate_yes")],
        [InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="deactivate_no")]
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return DEACTIVATE_CONFIRM


async def deactivate_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle first confirmation button."""
    query = update.callback_query
    await query.answer()
    data = query.data

    lang = context.user_data.get('deactivate_lang', 'en')

    if data == "deactivate_no":
        await query.edit_message_text(get_text("deactivate_cancelled", lang))
        return ConversationHandler.END

    if data == "deactivate_yes":
        await query.edit_message_text(get_text("deactivate_confirm_type", lang), parse_mode="Markdown")
        return DEACTIVATE_TYPE

    return ConversationHandler.END


async def deactivate_type_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify typed confirmation text."""
    text = update.message.text.strip()
    lang = context.user_data.get('deactivate_lang', 'en')

    expected = "DELETE" if lang == "en" else "ลบบัญชี"

    if text != expected:
        await update.message.reply_text(get_text("deactivate_type_mismatch", lang), parse_mode="Markdown")
        return DEACTIVATE_TYPE

    user_id = context.user_data.get('deactivate_user_id')

    # Send final message before deactivation (telegram will be unlinked)
    success = BotService.deactivate_account(user_id)
    if success:
        await update.message.reply_text(get_text("deactivate_success", lang))
    else:
        await update.message.reply_text(get_text("error", lang))

    return ConversationHandler.END


def get_deactivate_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("deactivate", deactivate_command)],
        states={
            DEACTIVATE_CONFIRM: [CallbackQueryHandler(deactivate_confirm_callback, pattern='^deactivate_')],
            DEACTIVATE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, deactivate_type_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=120,
        allow_reentry=True,
    )


# ============================================================================
# /broadcast — Admin Broadcast
# ============================================================================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /broadcast — Admin only."""
    chat_id = update.effective_chat.id

    # Admin check via env var
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    admin_ids = []
    for x in admin_ids_str.split(","):
        x = x.strip()
        if x:
            try:
                admin_ids.append(int(x))
            except ValueError:
                pass

    if chat_id not in admin_ids:
        user = BotService.get_user_by_telegram_id(chat_id)
        lang = (user.language or "en") if user else "en"
        await update.message.reply_text(get_text("broadcast_not_admin", lang))
        return ConversationHandler.END

    user = BotService.get_user_by_telegram_id(chat_id)
    lang = (user.language or "en") if user else "en"

    await update.message.reply_text(get_text("broadcast_enter_msg", lang), parse_mode="Markdown")
    return BROADCAST_MSG


async def broadcast_msg_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast message text."""
    text = update.message.text.strip()
    user = BotService.get_user_by_telegram_id(update.effective_chat.id)
    lang = (user.language or "en") if user else "en"

    if not text:
        await update.message.reply_text(get_text("broadcast_empty", lang))
        return BROADCAST_MSG

    context.user_data['broadcast_msg'] = text

    msg = get_text("broadcast_preview", lang, message=text)
    keyboard = [
        [
            InlineKeyboardButton(get_text("btn_confirm", lang), callback_data="broadcast_send"),
            InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="broadcast_cancel")
        ]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return BROADCAST_CONFIRM


async def broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirm/cancel."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "en") if user else "en"

    if data == "broadcast_cancel":
        await query.edit_message_text(get_text("broadcast_cancelled", lang))
        context.user_data.pop('broadcast_msg', None)
        return ConversationHandler.END

    if data == "broadcast_send":
        msg_text = context.user_data.get('broadcast_msg')
        if not msg_text:
            await query.edit_message_text(get_text("session_expired", lang))
            return ConversationHandler.END

        await query.edit_message_text(get_text("broadcast_sending", lang))

        # Get all users with linked Telegram
        users = BotService.get_all_broadcast_chat_ids()
        success = 0
        fail = 0

        broadcast_text = f"📢 *ประกาศ / Announcement*\n\n{msg_text}"

        for u in users:
            try:
                await context.bot.send_message(
                    chat_id=u['telegram_id'],
                    text=broadcast_text,
                    parse_mode="Markdown"
                )
                success += 1
                await asyncio.sleep(0.05)  # Rate limit: ~20 msg/sec
            except Exception as e:
                fail += 1
                logger.warning(f"Broadcast fail to user {u['user_id']}: {e}")

        report = get_text("broadcast_report", lang,
            success=success, fail=fail, total=len(users))
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=report, parse_mode="Markdown")

        context.user_data.pop('broadcast_msg', None)
        BotLogService.log(update.effective_chat.id, "OUT", "broadcast",
            f"Broadcast sent: {success}/{len(users)}")
        return ConversationHandler.END

    return ConversationHandler.END


def get_broadcast_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command)],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg_input)],
            BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_confirm_callback, pattern='^broadcast_')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )
