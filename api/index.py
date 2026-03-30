import sys

try:
    from app.main import app
except BaseException as e:
    # If import fails, create a minimal app that shows the error
    # Use BaseException to catch everything including RuntimeError from missing env vars
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    _error_msg = str(e)
    try:
        import traceback
        _error_tb = traceback.format_exc()
    except Exception:
        _error_tb = "Could not format traceback"

    @app.get("/{path:path}")
    async def import_error(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to import app.main",
                "detail": _error_msg,
                "traceback": _error_tb,
                "python_version": sys.version,
            },
        )

handler = app
