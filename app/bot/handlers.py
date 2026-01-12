
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from app.bot.services import BotService
from app.utils.ocr_helper import read_blood_pressure_with_gemini
from datetime import datetime
import logging
import tempfile
import os

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
    
    if linked_user:
        await update.message.reply_text(
            f"Welcome back, {linked_user.full_name}! ✅\n"
            "You are already linked to the system.\n"
            "Use /stats to see your blood pressure trends or just send a photo to record.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # 2. Not linked -> Request Contact
    contact_keyboard = KeyboardButton(text="📱 Share Contact", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_keyboard]], one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n"
        "To start using the Blood Pressure Monitor Bot, please share your phone number to verify your identity.",
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
        await update.message.reply_text(
            f"✅ Found account for {phone_number}!\n"
            "Please enter your **Web Password** to confirm linking:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return AUTH_PASSWORD
    else:
        await update.message.reply_text(
            f"🆕 Phone {phone_number} not registered.\n"
            "Let's create a new account.\n\n"
            "Please enter your **Full Name** (e.g. Somchai Jaidee):",
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
    await update.message.reply_text("Please enter your **Date of Birth** (DD/MM/YYYY):", parse_mode="Markdown")
    return REG_DOB

async def reg_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        dob = datetime.strptime(text, "%d/%m/%Y")
        context.user_data['date_of_birth'] = dob
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Please use DD/MM/YYYY (e.g. 31/01/1990):")
        return REG_DOB

    keyboard = [['Male', 'Female', 'Other']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Please select your **Gender**:", reply_markup=reply_markup, parse_mode="Markdown")
    return REG_GENDER

async def reg_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ['male', 'female', 'other']:
        await update.message.reply_text("Please select from the buttons.")
        return REG_GENDER
    context.user_data['gender'] = gender
    keyboard = [['Patient', 'Doctor']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Are you a **Patient** or a **Doctor**?", reply_markup=reply_markup, parse_mode="Markdown")
    return REG_ROLE

async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = update.message.text.lower()
    if role not in ['patient', 'doctor']:
        await update.message.reply_text("Please select Patient or Doctor.")
        return REG_ROLE
    context.user_data['role'] = role
    await update.message.reply_text(
        "Almost done! Please set a **Password** for logging into the website:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 8:
        await update.message.reply_text("⚠️ Password must be at least 8 characters. Please try again:")
        return REG_PASSWORD
    try:
        await update.message.delete()
    except:
        pass

    context.user_data['password'] = password
    await update.message.reply_text("⏳ Creating account...")
    new_user = await BotService.register_new_user(context.user_data, update.effective_chat.id)
    if new_user:
        msg = f"✅ **Registration Complete!**\n\nWelcome, {new_user.full_name}."
        if new_user.role == 'doctor':
            if new_user.verification_status == 'verified':
                msg += "\n✅ **Doctor License Verified** (Auto-Check Passed)."
            else:
                msg += "\n⚠️ **License Verification Pending**."
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Registration failed due to a server error. Please try again later.")
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
        msg = f"**Read Result:**\n" \
              f"❤️ SYS: **{ocr_result.systolic}**\n" \
              f"💙 DIA: **{ocr_result.diastolic}**\n" \
              f"💓 PULSE: **{ocr_result.pulse}**\n" \
              f"📅 Time: **{dt_display}** {date_warning}\n\n" \
              f"Is this correct?"
              
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Save", callback_data="save_ocr"),
                InlineKeyboardButton("✏️ Edit", callback_data="edit_ocr")
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
             await query.edit_message_text("✅ **Record Saved Successfully!**", parse_mode="Markdown")
        else:
             await query.edit_message_text("⚠️ **Record already exists!** (Duplicate ignored)", parse_mode="Markdown")
             
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
    
    msg = f"**Your BP Profile**\n" \
          f"**Average** (Last 30 Records):\n" \
          f"{avg_sys}/{avg_dia} mmHg (Pulse {avg_pulse})\n\n" \
          f"**Latest Entries** (Log):\n"
          
    if not recent:
        msg += "- No records found."
    else:
        for r in recent:
            date_str = r.measurement_date.strftime("%d/%m/%Y")
            time_str = r.measurement_time if r.measurement_time else ""
            msg += f"- {date_str} {time_str}: **{r.systolic}/{r.diastolic}** ({r.pulse})\n"
            
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    msg = (
        "**Need Help?**\n\n"
        "Here are the commands I know:\n"
        "/start - Register or Connect Account\n"
        "/stats - View your Blood Pressure trends\n"
        "/help - Show this message\n\n"
        "**To Record BP**: Just send me a photo of your monitor!\n"
        "**To Typo**: Send a photo, then click 'Edit' if numbers differ."
    )
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
    )

# ... inside main setup in main.py, we need to register these ...
# Wait, I am editing handlers.py, I need to make sure these are EXPORTED or used.
# The `main.py` likely imports specific functions or a setup function.
# Let me verify `app/bot/main.py` next to see how handlers are attached.
# For now, I'll add the functions here.
