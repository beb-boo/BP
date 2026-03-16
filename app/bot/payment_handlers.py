"""Telegram Payment Handler"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from app.bot.services import BotService
from app.config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT

logger = logging.getLogger(__name__)

# Conversation states
WAITING_SLIP = 1

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """แสดงแพลน subscription / Show plans"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /login first. (กรุณา Login ก่อน)")
        return ConversationHandler.END

    lang = user.language or "th"
    
    # Text Generation
    if lang == "en":
        text = "💎 *Upgrade to Premium*\n\n"
        text += "Benefits:\n"
        text += "✅ Unlimited BP Records\n"
        text += "✅ Full History Access\n"
        text += "✅ Unlimited Data Export\n\n"
        text += "📋 *Select Plan:*\n"
        cancel_text = "❌ Cancel"
    else:
        text = "💎 *อัพเกรดเป็น Premium*\n\n"
        text += "สิทธิประโยชน์:\n"
        text += "✅ บันทึกความดันได้ไม่จำกัด\n"
        text += "✅ ดูประวัติย้อนหลังทั้งหมด\n"
        text += "✅ Export ข้อมูลไม่จำกัด\n\n"
        text += "📋 *เลือกแพลน:*\n"
        cancel_text = "❌ ยกเลิก"

    keyboard = []
    for plan_type, plan in SUBSCRIPTION_PLANS.items():
        # Name
        p_name = plan['name_en'] if lang == "en" else plan['name']
        keyboard.append([
            InlineKeyboardButton(
                f"{p_name} - {plan['price']:.0f} THB",
                callback_data=f"pay_{plan_type}"
            )
        ])
    keyboard.append([InlineKeyboardButton(cancel_text, callback_data="pay_cancel")])

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

    if query.data == "pay_cancel":
        await query.edit_message_text("Cancelled. (ยกเลิกรายการ)")
        return ConversationHandler.END

    # Get User for Language
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    lang = user.language or "th" if user else "th"

    plan_type = query.data.replace("pay_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_type)

    if not plan:
        await query.edit_message_text("Error: Invalid Plan")
        return ConversationHandler.END

    context.user_data["selected_plan"] = plan_type
    
    # Bank Info
    bank_name = PAYMENT_ACCOUNT.get("bank_en" if lang == "en" else "bank", PAYMENT_ACCOUNT["bank"])

    if lang == "en":
        text = f"📝 *Selected Plan:* {plan['name_en']}\n"
        text += f"💰 *Price:* {plan['price']:.0f} THB\n\n"
        text += "🏦 *Transfer to:*\n"
        text += f"Bank: {bank_name}\n"
        text += f"Acc No.: {PAYMENT_ACCOUNT['account_number']}\n"
        text += f"Name: {PAYMENT_ACCOUNT['account_name']}\n\n"
        text += f"⚠️ *Please transfer exactly {plan['price']:.0f} THB and send the SLIP here.*\n"
        text += "(Type /cancel to cancel)"
    else:
        text = f"📝 *แพลนที่เลือก:* {plan['name']}\n"
        text += f"💰 *ราคา:* {plan['price']:.0f} บาท\n\n"
        text += "🏦 *โอนเงินมาที่:*\n"
        text += f"ธนาคาร: {bank_name}\n"
        text += f"เลขบัญชี: {PAYMENT_ACCOUNT['account_number']}\n"
        text += f"ชื่อบัญชี: {PAYMENT_ACCOUNT['account_name']}\n\n"
        text += f"⚠️ *กรุณาโอนเงิน {plan['price']:.0f} บาท แล้วส่งรูปสลิปมาที่นี่*\n"
        text += "(พิมพ์ /cancel เพื่อยกเลิก)"

    await query.edit_message_text(text, parse_mode="Markdown")
    return WAITING_SLIP


async def receive_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """รับรูปสลิปและตรวจสอบ"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /login first.")
        return ConversationHandler.END

    lang = user.language or "th"

    plan_type = context.user_data.get("selected_plan")
    if not plan_type:
        await update.message.reply_text("Session expired. Please use /upgrade again.")
        return ConversationHandler.END

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    # Wait Msg
    msg_txt = "🔄 Verifying slip..." if lang == "en" else "🔄 กำลังตรวจสอบสลิป..."
    checking_msg = await update.message.reply_text(msg_txt)

    try:
        # Check if Photo or Document
        if update.message.photo:
            file_obj = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith("image/"):
             file_obj = await update.message.document.get_file()
        else:
             err_txt = "Please send an image." if lang == "en" else "กรุณาส่งไฟล์รูปภาพ"
             await checking_msg.edit_text(f"❌ {err_txt}")
             return WAITING_SLIP

        # Download
        image_bytes = await file_obj.download_as_bytearray()

        # Verify
        result = BotService.verify_slip_payment(user.id, bytes(image_bytes), plan_type)

        if result["success"]:
            p_name = SUBSCRIPTION_PLANS[plan_type]['name_en' if lang == 'en' else 'name']
            
            if lang == "en":
                text = "✅ *Payment Successful!*\n\n"
                text += f"Plan: {p_name}\n"
                text += f"Amount: {result['amount']:.0f} THB\n"
                text += f"Expires: {result['expires_at']}\n\n"
                text += "🎉 You are now Premium!"
            else:
                text = "✅ *ชำระเงินสำเร็จ!*\n\n"
                text += f"แพลน: {p_name}\n"
                text += f"ยอด: {result['amount']:.0f} บาท\n"
                text += f"หมดอายุ: {result['expires_at']}\n\n"
                text += "🎉 คุณเป็น Premium แล้ว!"

            await checking_msg.edit_text(text, parse_mode="Markdown")
        else:
            await checking_msg.edit_text(f"❌ {result['error']}")
            return WAITING_SLIP  # Allow retry

    except Exception as e:
        logger.error(f"Slip verification error: {e}")
        err_txt = "System Error. Try again." if lang == "en" else "เกิดข้อผิดพลาด กรุณาลองใหม่"
        await checking_msg.edit_text(f"❌ {err_txt}")
        return WAITING_SLIP

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ยกเลิกการชำระเงิน"""
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดูสถานะ subscription"""
    user = BotService.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please /login first.")
        return

    status = BotService.get_subscription_status(user.id)
    if not status: # User not found or error
         await update.message.reply_text("Error retrieving status.")
         return

    lang = status.get("language", "th")

    if status["is_active"]:
        if lang == "en":
            text = "💎 *Premium Member*\n\n"
            text += f"Expires: {status['expires_at']}\n"
            text += f"Remaining: {status['days_remaining']} days"
        else:
            text = "💎 *Premium Member*\n\n"
            text += f"หมดอายุ: {status['expires_at']}\n"
            text += f"เหลืออีก: {status['days_remaining']} วัน"
    else:
        if lang == "en":
            text = "📦 *Free Member*\n\n"
            text += "Limited to 30 latest records.\n"
            text += "Type /upgrade to unlock Premium."
        else:
            text = "📦 *Free Member*\n\n"
            text += "จำกัด 30 รายการล่าสุด\n"
            text += "พิมพ์ /upgrade เพื่ออัพเกรดเป็น Premium"

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
        per_message=False
    )
