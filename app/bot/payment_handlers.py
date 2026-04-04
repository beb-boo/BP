
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.constants import ChatAction

from app.bot.services import BotService
from app.config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT
from .locales import get_text

logger = logging.getLogger(__name__)

# Conversation states
WAITING_SLIP = 1

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """แสดงแพลน subscription / Show plans"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "th"

    text = get_text("upgrade_title", lang)

    keyboard = []
    for plan_type, plan in SUBSCRIPTION_PLANS.items():
        p_name = plan['name_en'] if lang == "en" else plan['name']
        keyboard.append([
            InlineKeyboardButton(
                f"{p_name} - {plan['price']:.0f} THB",
                callback_data=f"pay_{plan_type}"
            )
        ])
    keyboard.append([InlineKeyboardButton(get_text("btn_cancel", lang), callback_data="pay_cancel")])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_SLIP


async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """เมื่อเลือกแพลน - แสดงข้อมูลการโอนเงิน"""
    query = update.callback_query
    await query.answer()

    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "th") if user else "th"

    if query.data == "pay_cancel":
        await query.edit_message_text(get_text("pay_cancelled", lang))
        return ConversationHandler.END

    plan_type = query.data.replace("pay_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_type)

    if not plan:
        await query.edit_message_text(get_text("pay_invalid_plan", lang))
        return ConversationHandler.END

    context.user_data["selected_plan"] = plan_type

    bank_name = PAYMENT_ACCOUNT.get("bank_en" if lang == "en" else "bank", PAYMENT_ACCOUNT["bank"])
    p_name = plan['name_en'] if lang == "en" else plan['name']

    text = get_text("pay_transfer_info", lang,
        plan_name=p_name,
        price=plan['price'],
        bank=bank_name,
        account=PAYMENT_ACCOUNT['account_number'],
        name=PAYMENT_ACCOUNT['account_name']
    )

    await query.edit_message_text(text, parse_mode="Markdown")
    return WAITING_SLIP


async def receive_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """รับรูปสลิปและตรวจสอบ"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return ConversationHandler.END

    lang = user.language or "th"

    plan_type = context.user_data.get("selected_plan")
    if not plan_type:
        await update.message.reply_text(get_text("pay_session_expired", lang))
        return ConversationHandler.END

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    checking_msg = await update.message.reply_text(get_text("pay_verifying", lang))

    try:
        # Check if Photo or Document
        if update.message.photo:
            file_obj = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith("image/"):
            file_obj = await update.message.document.get_file()
        else:
            await checking_msg.edit_text(get_text("pay_send_image", lang))
            return WAITING_SLIP

        # Download
        image_bytes = await file_obj.download_as_bytearray()

        # Verify
        result = BotService.verify_slip_payment(user.id, bytes(image_bytes), plan_type)

        if result["success"]:
            p_name = SUBSCRIPTION_PLANS[plan_type]['name_en' if lang == 'en' else 'name']
            text = get_text("pay_success", lang,
                plan_name=p_name,
                amount=result['amount'],
                expires=result['expires_at']
            )
            await checking_msg.edit_text(text, parse_mode="Markdown")
        else:
            await checking_msg.edit_text(f"❌ {result['error']}")
            return WAITING_SLIP  # Allow retry

    except Exception as e:
        logger.error(f"Slip verification error: {e}")
        await checking_msg.edit_text(get_text("pay_system_error", lang))
        return WAITING_SLIP

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ยกเลิกการชำระเงิน"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = (user.language or "th") if user else "th"
    context.user_data.clear()
    await update.message.reply_text(get_text("pay_cancelled", lang))
    return ConversationHandler.END


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดูสถานะ subscription"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(get_text("not_linked", "en"))
        return

    status = BotService.get_subscription_status(user.id)
    if not status:
        await update.message.reply_text(get_text("error", user.language or "th"))
        return

    lang = status.get("language", "th")

    if status["is_active"]:
        text = get_text("sub_premium", lang,
            expires=status['expires_at'],
            days=status['days_remaining']
        )
    else:
        text = get_text("sub_free", lang)

    await update.message.reply_text(text, parse_mode="Markdown")


def get_payment_handler():
    """สร้าง ConversationHandler สำหรับ payment"""
    return ConversationHandler(
        entry_points=[CommandHandler("upgrade", upgrade_command)],
        states={
            WAITING_SLIP: [
                CallbackQueryHandler(plan_selected, pattern="^pay_"),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_slip),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=False,
        conversation_timeout=300,  # 5 minutes
    )
