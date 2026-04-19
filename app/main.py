
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load environment variables before importing modules that read required env vars.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Import database setup
from .database import engine, Base

# Import centralized rate limiter
from .utils.rate_limiter import limiter

# Import routers
from .routers import auth, users, bp_records, ocr, doctor, export, payment, telegram_auth, admin, admin_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables (controlled by ENV)
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
if AUTO_CREATE_TABLES:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.warning(f"Auto-create tables skipped (tables may already exist): {e}")

# Create App
app = FastAPI(
    title="Blood Pressure Monitor API",
    description="API for tracking blood pressure and doctor-patient data sharing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Attach limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if _allowed_origins_env:
    # Explicit origins configured — use them as-is (production)
    origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    logger.info(f"CORS: Using configured origins ({len(origins)} entries)")
else:
    # No explicit origins — dev mode: allow all + localhost
    origins = ["http://localhost:3000", "http://localhost:3001"]
    logger.warning(
        "ALLOWED_ORIGINS not set, defaulting to localhost only. "
        "Set ALLOWED_ORIGINS for production."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(bp_records.router)
app.include_router(bp_records.stats_router)
app.include_router(ocr.router)
app.include_router(doctor.router)
app.include_router(export.router)
app.include_router(payment.router)
app.include_router(telegram_auth.router)
app.include_router(admin.router)
app.include_router(admin_system.router)

# Telegram Bot Webhook (conditional)
BOT_MODE = os.getenv("BOT_MODE", "polling")
if BOT_MODE == "webhook":
    try:
        from .bot.webhook import router as bot_webhook_router, _webhook_path
        app.include_router(bot_webhook_router)
        logger.info(f"Telegram Bot: Webhook mode enabled at /{_webhook_path}/webhook")
    except Exception as e:
        logger.error(f"Failed to load bot webhook: {e}")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Blood Pressure Monitor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Exception Handlers


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        errors.append({"field": field, "message": msg})

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": errors
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
