"""Telegram Bot Webhook Handler for serverless deployment."""

import os
import logging
import secrets
from fastapi import APIRouter, HTTPException, Request, Query
from telegram import Update

logger = logging.getLogger(__name__)

# Configurable webhook path — use a hard-to-guess path in production
# Example: WEBHOOK_PATH=bot-a1b2c3d4e5f6 → endpoint becomes /bot-a1b2c3d4e5f6/webhook
_webhook_path = os.getenv("WEBHOOK_PATH", "")
if not _webhook_path:
    # Generate a random path for this session (won't persist across restarts)
    _webhook_path = f"bot-{secrets.token_hex(16)}"
    logger.warning(
        f"WEBHOOK_PATH not set. Generated random path: /{_webhook_path}/webhook "
        f"(Set WEBHOOK_PATH in .env for a stable, hard-to-guess webhook URL)"
    )
else:
    logger.info(f"Telegram webhook path configured: /{_webhook_path}/webhook")

router = APIRouter(prefix=f"/{_webhook_path}", tags=["telegram bot"])

# Lazy-initialized application instance
_application = None


def get_application():
    """Get or create the bot application (singleton for webhook mode)."""
    global _application
    if _application is None:
        from .main import build_application
        _application = build_application()
    return _application


@router.on_event("startup")
async def startup_webhook():
    """Initialize the bot application on FastAPI startup."""
    try:
        app = get_application()
        await app.initialize()
        # Start the application to enable JobQueue (needed for conversation_timeout)
        await app.start()
        logger.info("Telegram Bot webhook application initialized and started")
    except Exception as e:
        logger.error(f"Failed to initialize bot application: {e}")


@router.on_event("shutdown")
async def shutdown_webhook():
    """Shutdown the bot application on FastAPI shutdown."""
    global _application
    if _application:
        try:
            await _application.stop()
            await _application.shutdown()
            logger.info("Telegram Bot webhook application shut down")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram updates via webhook."""
    webhook_secret = os.getenv("WEBHOOK_SECRET", "")

    # Verify secret token header if configured
    if webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        app = get_application()
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/set-webhook")
async def set_webhook(secret: str = Query(..., description="Admin secret to authorize this action")):
    """Utility endpoint to set the Telegram webhook URL (call once during setup)."""
    admin_secret = os.getenv("WEBHOOK_SECRET", "")
    if not admin_secret or secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    webhook_url = os.getenv("WEBHOOK_URL", "")
    if not webhook_url:
        raise HTTPException(status_code=500, detail="WEBHOOK_URL not configured")

    full_url = f"{webhook_url.rstrip('/')}/{_webhook_path}/webhook"

    try:
        app = get_application()
        await app.bot.set_webhook(
            url=full_url,
            secret_token=admin_secret
        )
        logger.info(f"Webhook set to: {full_url}")
        return {"ok": True, "webhook_url": full_url}
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remove-webhook")
async def remove_webhook(secret: str = Query(..., description="Admin secret to authorize this action")):
    """Remove the Telegram webhook (switch back to polling mode)."""
    admin_secret = os.getenv("WEBHOOK_SECRET", "")
    if not admin_secret or secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    try:
        app = get_application()
        await app.bot.delete_webhook()
        logger.info("Webhook removed")
        return {"ok": True, "message": "Webhook removed. You can now use polling mode."}
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
