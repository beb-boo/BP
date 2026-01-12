from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from app.core.config import settings
from app.core.bot_services import BotService
from app.core.ai_agent import ai_agent

# Stages
LOGIN_USER, LOGIN_PASS, CONFIRM_LOGOUT = range(3)
CHANGE_PWD_OLD, CHANGE_PWD_NEW = range(3, 5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if user is linked
    linked_user = BotService.get_user_by_telegram_id(chat_id)
    
    if linked_user:
        await update.message.reply_html(
            rf"Hi {linked_user.full_name}! Welcome back to Pimtong Work Manager.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! You are not linked to the system yet. Please use /link to connect your account.",
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
    Available Commands:
    /start - Check status
    /today - Jobs for Today
    /tomorrow - Jobs for Tomorrow (Day after)
    /thisweek - Jobs for This Week (Mon-Sun)
    /nextweek - Jobs for Next Week
    /lastweek - Jobs for Last Week
    /projects - List All Projects
    /link - Connect account
    /logout - Disconnect account
    
    You can also chat normally (e.g. "my jobs today").
    """
    await update.message.reply_text(help_text)

# --- Helper ---
def _format_jobs(jobs):
    if not jobs:
        return "No jobs found matching your criteria."
    msg = ""
    for job in jobs:
        # Status Icon
        status_icon = "✅" if job.status == 'completed' else "⏳"
        if job.status == 'in_progress': status_icon = "🔧"
        elif job.status == 'cancelled': status_icon = "❌"
        
        # Google Maps Link
        map_link = ""
        if job.location_lat and job.location_long:
            map_link = f" | <a href='https://www.google.com/maps/search/?api=1&query={job.location_lat},{job.location_long}'>📍 Map</a>"
        
        # Product Info
        product_info = ""
        if job.product_type or job.model:
            product_info = f"\n📦 <b>Product:</b> {job.product_type or '-'} {job.model or ''}"
        
        # Assignments
        assign_str = "Pending"
        if job.assignments:
            techs = [a.technician.full_name for a in job.assignments if a.technician]
            if techs:
                assign_str = ", ".join(techs)
        
        time_str = job.scheduled_time or "Anytime"
        
        msg += f"<b>{status_icon} Job #{job.id} - {job.title}</b>\n"
        msg += f"📅 <b>Date:</b> {job.scheduled_date} @ {time_str}\n"
        msg += f"📝 <b>Desc:</b> {job.description or '-'}\n"
        msg += f"📊 <b>Status:</b> {job.status.upper()}\n"
        msg += f"👷 <b>Tech:</b> {assign_str}\n"
        msg += f"👤 <b>Customer:</b> {job.customer_name} ({job.customer_phone or '-'}){map_link}\n"
        msg += f"🏠 <b>Addr:</b> {job.customer_address or '-'}"
        msg += product_info
        msg += f"\n-----------------------------\n\n"
        
    return msg

async def _get_auth_user(update):
    chat_id = update.effective_chat.id
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text("Please /link your account first.")
        return None
    return user

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update)
    if not user: return
    jobs = BotService.get_jobs(user.id, {'date': 'today'})
    await update.message.reply_html(_format_jobs(jobs))

async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update)
    if not user: return
    jobs = BotService.get_jobs(user.id, {'date': 'tomorrow'})
    await update.message.reply_html(_format_jobs(jobs))

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update)
    if not user: return
    jobs = BotService.get_jobs(user.id, {'period': 'week'})
    await update.message.reply_html(_format_jobs(jobs))

async def cmd_nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update)
    if not user: return
    jobs = BotService.get_jobs(user.id, {'period': 'next_week'})
    await update.message.reply_html(_format_jobs(jobs))

async def cmd_lastweek(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update)
    if not user: return
    jobs = BotService.get_jobs(user.id, {'period': 'last_week'})
    await update.message.reply_html(_format_jobs(jobs))

async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _get_auth_user(update) # Auth check
    if not user: return
    
    projects = BotService.get_projects({})
    if projects:
        response = "<b>Found Projects:</b>\n\n"
        for p in projects:
             response += f"- <b>{p.name}</b> (ID: {p.id})\n"
             response += f"   Status: {p.status}\n\n"
    else:
        response = "No projects found."
    await update.message.reply_html(response)

# --- Login Flow ---
async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    if BotService.get_user_by_telegram_id(chat_id):
        await update.message.reply_text("You are already linked!")
        return ConversationHandler.END

    await update.message.reply_text("Please enter your *Username*:", parse_mode='Markdown')
    return LOGIN_USER

async def login_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Please enter your *Password*:", parse_mode='Markdown')
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = update.message.text
    
    # Try to delete password message for security
    try:
        await update.message.delete()
    except:
        pass # Admin rights might be missing

    user = BotService.verify_user_login(username, password)
    
    if user:
        BotService.link_telegram_id(username, update.effective_chat.id)
        await update.message.reply_text("Login Successful! Your account is now linked.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid Credentials. /link to try again.")
        return ConversationHandler.END

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Login cancelled.")
    return ConversationHandler.END

# --- AI Message Handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    
    # 1. Check Auth (Lazy check)
    user = BotService.get_user_by_telegram_id(chat_id)
    if not user:
        await update.message.reply_text("Please /link your account first.")
        return

    # 2. Analyze Intent
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    result = ai_agent.analyze_intent(text)
    print(f"DEBUG: User Text = '{text}'")
    print(f"DEBUG: AI Result = {result}")
    
    intent = result.get('intent')
    # AI might return 'params' or 'parameters'
    params = result.get('params') or result.get('parameters', {})
    
    # 3. Execute
    if intent == "QUERY_JOBS":
        jobs = BotService.get_jobs(user.id, params)
        if not jobs:
             await update.message.reply_text("No jobs found matching your criteria.")
        else:
            msg = _format_jobs(jobs)
            await update.message.reply_html(msg)

    elif intent == "QUERY_PROJECTS":
        # Check if looking for specific project details
        keyword = params.get('keyword') or params.get('customer_name')
        
        # If specific keyword provided, try to get details of single project
        if keyword:
             details = BotService.get_project_details(project_name=keyword)
             if details:
                 # Rich Project Detail View
                 msg = f"<b>{details['name']}</b>\n"
                 msg += f"Customer: {details['customer'] or '-'}\n"
                 msg += f"Desc: {details['description'] or '-'}\n\n"
                 
                 # Progress Bar
                 progress = details['progress']
                 bar_length = 10
                 filled = int(progress / 10)
                 bar = "█" * filled + "░" * (bar_length - filled)
                 
                 msg += f"Progress: {progress}% [{bar}]\n"
                 msg += f"Jobs: {details['total_jobs']} tasks\n"
                 msg += f"Start: {details['start_date']}  End: {details['end_date']}\n\n"
                 
                 if details['job_list']:
                     msg += "<b>Job List:</b>\n"
                     for job_title in details['job_list']:
                         msg += f"- {job_title}\n"
                 
                 await update.message.reply_html(msg)
                 return

        # Fallback to list view
        projects = BotService.get_projects(params)
        if projects:
            response = "<b>Found Projects:</b>\n\n"
            for p in projects:
                response += f"- <b>{p.name}</b> (ID: {p.id})\n"
                response += f"   Status: {p.status}\n\n"
        else:
            response = "No projects found matching your criteria."
            
        await update.message.reply_html(response)

    elif intent == "GET_JOB_DETAILS":
        job_id = params.get('job_id')
        job = BotService.get_job_details(job_id, user.id)
        if job:
            # Re-use the rich format for consistency, just for one job
            msg = _format_jobs([job])
            await update.message.reply_html(msg)
        else:
            await update.message.reply_text("Job not found or access denied.")

    elif intent == "UPDATE_JOB":
        job_id = params.get('job_id')
        status = params.get('status')
        note = params.get('note')
        
        success, msg = BotService.update_job_status(job_id, user.id, status, note)
        status_label = "Success:" if success else "Failed:"
        await update.message.reply_text(f"{status_label} {msg}")

    elif intent == "PROFILE_PASSWORD":
        await update.message.reply_text("To change password, please visit the Web App for now (Implementing secure flow soon).")

    else:
        # OTHER_CHAT
        reply = params.get('reply', "I didn't quite catch that.")
        await update.message.reply_text(reply)

def create_app():
    """Create and configure the bot application."""
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Telegram Token not set, skipping bot setup.")
        return None
    
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Conversation Handler for Login
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("link", link_command)],
        states={
            LOGIN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_user)],
            LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pass)],
        },
        fallbacks=[CommandHandler("cancel", cancel_login)],
    )

    application.add_handler(login_conv)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # New Fallback Commands
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    application.add_handler(CommandHandler("week", cmd_week))
    application.add_handler(CommandHandler("thisweek", cmd_week)) # Alias
    application.add_handler(CommandHandler("nextweek", cmd_nextweek))
    application.add_handler(CommandHandler("lastweek", cmd_lastweek))
    application.add_handler(CommandHandler("projects", cmd_projects))
    
    # Generic Message Handler for AI
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application

async def process_webhook_update(application: Application, data: dict):
    """Process a single update from a webhook."""
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
