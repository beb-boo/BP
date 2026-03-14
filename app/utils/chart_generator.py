"""
BP Chart Generator — สร้างกราฟ Blood Pressure เป็นรูป PNG
ใช้ Chart.js ผ่าน Node.js subprocess (@napi-rs/canvas)
"""

import json
import os
import shutil
import subprocess
from io import BytesIO
from datetime import datetime
from typing import List, Any
import logging

logger = logging.getLogger(__name__)

# Path to Node.js chart renderer
_CHART_RENDERER_DIR = os.path.join(os.path.dirname(__file__), '..', 'chart-renderer')
_RENDER_SCRIPT = os.path.join(_CHART_RENDERER_DIR, 'render.js')
_NODE_BIN = shutil.which('node')
_NODE_MODULES = os.path.join(_CHART_RENDERER_DIR, 'node_modules')

# Verify Node.js renderer availability at import time
_NODE_READY = bool(
    _NODE_BIN
    and os.path.isfile(_RENDER_SCRIPT)
    and os.path.isdir(_NODE_MODULES)
)

if _NODE_READY:
    logger.info(f"Chart generator: Chart.js ready (Node.js at {_NODE_BIN})")
else:
    missing = []
    if not _NODE_BIN:
        missing.append("Node.js not found in PATH")
    if not os.path.isfile(_RENDER_SCRIPT):
        missing.append(f"render.js not found at {_RENDER_SCRIPT}")
    if not os.path.isdir(_NODE_MODULES):
        missing.append(f"node_modules not found (run 'npm install' in {_CHART_RENDERER_DIR})")
    logger.warning(f"Chart generator: NOT ready — {'; '.join(missing)}")


def generate_bp_chart(records: List[Any], lang: str = "en") -> BytesIO:
    """
    Generate a BP trend chart as PNG image.

    Args:
        records: List of BP records (SQLAlchemy objects or dicts)
                 Must have: systolic, diastolic, pulse, measurement_date, measurement_time
        lang: "en" or "th" for labels

    Returns:
        BytesIO buffer containing PNG image

    Raises:
        RuntimeError: If Node.js renderer is not available or rendering fails
    """
    if not _NODE_READY:
        raise RuntimeError(
            "Chart generator requires Node.js. "
            "Install Node.js and run 'npm install' in app/chart-renderer/"
        )

    # Sort records old → new
    sorted_records = sorted(records, key=lambda r: _get_datetime(r))

    # Extract data
    dates = [_get_datetime(r) for r in sorted_records]
    sys_vals = [_get_attr(r, 'systolic') for r in sorted_records]
    dia_vals = [_get_attr(r, 'diastolic') for r in sorted_records]
    pulse_vals = [_get_attr(r, 'pulse') for r in sorted_records]

    if len(dates) < 1:
        return _render_empty_chart(lang)

    # Format date labels for chart (DD/MM)
    labels = [d.strftime('%d/%m') for d in dates]

    return _render_chart(labels, sys_vals, dia_vals, pulse_vals, lang)


# ═══════════════════════════════════════════════════════════════════
# Chart.js (Node.js) renderer
# ═══════════════════════════════════════════════════════════════════

def _render_chart(
    labels: list, sys_vals: list, dia_vals: list, pulse_vals: list, lang: str
) -> BytesIO:
    """Render chart via Node.js Chart.js subprocess."""
    payload = json.dumps({
        "labels": labels,
        "systolic": sys_vals,
        "diastolic": dia_vals,
        "pulse": pulse_vals,
        "lang": lang,
        "width": 1200,
        "height": 600,
    })

    result = subprocess.run(
        [_NODE_BIN, _RENDER_SCRIPT],
        input=payload.encode('utf-8'),
        capture_output=True,
        timeout=15,
        cwd=_CHART_RENDERER_DIR,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        raise RuntimeError(f"Chart render failed (exit {result.returncode}): {stderr}")

    if len(result.stdout) < 100:
        raise RuntimeError("Chart render returned too little data (likely not a valid PNG)")

    buf = BytesIO(result.stdout)
    return buf


def _render_empty_chart(lang: str) -> BytesIO:
    """Generate an empty chart when no data is available."""
    return _render_chart([], [], [], [], lang)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _get_datetime(record) -> datetime:
    """Extract datetime from record (supports both ORM objects and dicts)."""
    if isinstance(record, dict):
        date_val = record.get('measurement_date')
        time_val = record.get('measurement_time', '00:00')
    else:
        date_val = record.measurement_date
        time_val = record.measurement_time or '00:00'

    if isinstance(date_val, str):
        date_part = date_val.split('T')[0]
        return datetime.strptime(f"{date_part} {time_val}", "%Y-%m-%d %H:%M")
    elif isinstance(date_val, datetime):
        return date_val
    else:
        # date object
        return datetime.combine(date_val, datetime.strptime(time_val, "%H:%M").time())


def _get_attr(record, attr: str):
    """Get attribute from record (supports both ORM objects and dicts)."""
    if isinstance(record, dict):
        return record.get(attr)
    return getattr(record, attr)
