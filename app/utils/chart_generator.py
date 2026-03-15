"""
BP Chart Generator — สร้างกราฟ Blood Pressure เป็นรูป PNG
รองรับ 2 renderers:
  - nodejs: Chart.js ผ่าน Node.js subprocess (สวยกว่า, ต้องมี Node.js)
  - quickchart: QuickChart.io API (ทำงานได้ทุก platform รวม Vercel)

ควบคุมด้วย ENV: CHART_RENDERER = auto | nodejs | quickchart
  - auto (default): ใช้ Node.js ถ้าพร้อม, ไม่งั้นใช้ QuickChart.io
"""

import json
import os
import shutil
import subprocess
from io import BytesIO
from datetime import datetime
from typing import List, Any
import logging

import httpx

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════

CHART_RENDERER = os.getenv("CHART_RENDERER", "auto").lower()

# Node.js renderer paths
_CHART_RENDERER_DIR = os.path.join(os.path.dirname(__file__), '..', 'chart-renderer')
_RENDER_SCRIPT = os.path.join(_CHART_RENDERER_DIR, 'render.js')
_NODE_BIN = shutil.which('node')
_NODE_MODULES = os.path.join(_CHART_RENDERER_DIR, 'node_modules')

_NODE_READY = bool(
    _NODE_BIN
    and os.path.isfile(_RENDER_SCRIPT)
    and os.path.isdir(_NODE_MODULES)
)

# QuickChart.io
QUICKCHART_URL = os.getenv("QUICKCHART_URL", "https://quickchart.io/chart")

# Log readiness
if _NODE_READY:
    logger.info(f"Chart generator: Node.js ready ({_NODE_BIN})")
else:
    missing = []
    if not _NODE_BIN:
        missing.append("Node.js not found")
    if not os.path.isfile(_RENDER_SCRIPT):
        missing.append("render.js not found")
    if not os.path.isdir(_NODE_MODULES):
        missing.append("node_modules not found")
    logger.warning(f"Chart generator: Node.js NOT ready — {'; '.join(missing)}")

logger.info(f"Chart generator: CHART_RENDERER={CHART_RENDERER}, QuickChart.io available as fallback")

# Colors (matching render.js)
_COLORS = {
    "sys": "#ef4444",
    "dia": "#3b82f6",
    "pulse": "#10b981",
    "sysZone": "rgba(239, 68, 68, 0.07)",
    "diaZone": "rgba(6, 182, 212, 0.07)",
    "sysRef": "rgba(239, 68, 68, 0.4)",
    "diaRef": "rgba(6, 182, 212, 0.4)",
    "grid": "rgba(148, 163, 184, 0.15)",
    "textLight": "#64748b",
    "title": "#1e293b",
}

BP_SYS_MAX = 140
BP_DIA_MAX = 90


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

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
        RuntimeError: If no renderer is available or rendering fails
    """
    # Sort records old → new
    sorted_records = sorted(records, key=lambda r: _get_datetime(r))

    # Extract data
    dates = [_get_datetime(r) for r in sorted_records]
    sys_vals = [_get_attr(r, 'systolic') for r in sorted_records]
    dia_vals = [_get_attr(r, 'diastolic') for r in sorted_records]
    pulse_vals = [_get_attr(r, 'pulse') for r in sorted_records]

    # Format date labels (DD/MM)
    labels = [d.strftime('%d/%m') for d in dates]

    # Choose renderer
    if CHART_RENDERER == "nodejs":
        if not _NODE_READY:
            raise RuntimeError("CHART_RENDERER=nodejs but Node.js is not available")
        return _render_chart_nodejs(labels, sys_vals, dia_vals, pulse_vals, lang)

    elif CHART_RENDERER == "quickchart":
        return _render_chart_quickchart(labels, sys_vals, dia_vals, pulse_vals, lang)

    else:  # auto
        if _NODE_READY:
            return _render_chart_nodejs(labels, sys_vals, dia_vals, pulse_vals, lang)
        return _render_chart_quickchart(labels, sys_vals, dia_vals, pulse_vals, lang)


# ═══════════════════════════════════════════════════════════════════
# Node.js renderer (existing)
# ═══════════════════════════════════════════════════════════════════

def _render_chart_nodejs(
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

    return BytesIO(result.stdout)


# ═══════════════════════════════════════════════════════════════════
# QuickChart.io renderer
# ═══════════════════════════════════════════════════════════════════

def _render_chart_quickchart(
    labels: list, sys_vals: list, dia_vals: list, pulse_vals: list, lang: str
) -> BytesIO:
    """Render chart via QuickChart.io API."""
    all_vals = [v for v in sys_vals + dia_vals + pulse_vals if v is not None]

    if all_vals:
        data_max = max(all_vals)
        data_min = min(all_vals)
        y_max = max(data_max + 20, BP_SYS_MAX + 25)
        y_min = max(0, min(data_min - 10, 40))
    else:
        y_max = 200
        y_min = 40

    sys_label = "ความดันบน (Sys)" if lang == "th" else "Systolic"
    dia_label = "ความดันล่าง (Dia)" if lang == "th" else "Diastolic"
    pulse_label = "ชีพจร" if lang == "th" else "Pulse"
    title_text = "กราฟความดันโลหิต" if lang == "th" else "Blood Pressure Trends"
    high_dia_label = "ความดันล่างสูง" if lang == "th" else "High Dia"
    high_sys_label = "ความดันสูง" if lang == "th" else "High Sys & Dia"

    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": sys_label,
                    "data": sys_vals,
                    "borderColor": _COLORS["sys"],
                    "backgroundColor": _COLORS["sys"],
                    "borderWidth": 2.5,
                    "pointRadius": 5,
                    "pointBackgroundColor": _COLORS["sys"],
                    "pointBorderColor": "#fff",
                    "pointBorderWidth": 1.5,
                    "lineTension": 0.3,
                    "fill": False,
                    "datalabels": {
                        "display": True,
                        "align": "top",
                        "anchor": "end",
                        "color": _COLORS["sys"],
                        "font": {"weight": "bold", "size": 10},
                        "formatter": "__SYSTOLIC_FORMATTER__",
                    },
                },
                {
                    "label": dia_label,
                    "data": dia_vals,
                    "borderColor": _COLORS["dia"],
                    "backgroundColor": _COLORS["dia"],
                    "borderWidth": 2.5,
                    "pointRadius": 5,
                    "pointBackgroundColor": _COLORS["dia"],
                    "pointBorderColor": "#fff",
                    "pointBorderWidth": 1.5,
                    "lineTension": 0.3,
                    "fill": False,
                    "datalabels": {
                        "display": True,
                        "align": "bottom",
                        "anchor": "start",
                        "color": _COLORS["dia"],
                        "font": {"weight": "bold", "size": 10},
                    },
                },
                {
                    "label": pulse_label,
                    "data": pulse_vals,
                    "borderColor": _COLORS["pulse"],
                    "backgroundColor": _COLORS["pulse"],
                    "borderWidth": 2,
                    "pointRadius": 3.5,
                    "pointBackgroundColor": _COLORS["pulse"],
                    "pointBorderColor": "#fff",
                    "pointBorderWidth": 1,
                    "borderDash": [6, 3],
                    "lineTension": 0.3,
                    "fill": False,
                    "datalabels": {
                        "display": True,
                        "align": "bottom",
                        "anchor": "start",
                        "color": _COLORS["pulse"],
                        "font": {"size": 9},
                        "formatter": "__PULSE_FORMATTER__",
                    },
                },
            ],
        },
        "options": {
            "responsive": False,
            "layout": {
                "padding": {"top": 25, "right": 20, "bottom": 10, "left": 10},
            },
            "scales": {
                "yAxes": [{
                    "ticks": {
                        "min": y_min,
                        "max": y_max,
                        "fontColor": _COLORS["textLight"],
                        "fontSize": 11,
                        "padding": 8,
                    },
                    "gridLines": {"color": _COLORS["grid"]},
                }],
                "xAxes": [{
                    "ticks": {
                        "fontColor": _COLORS["textLight"],
                        "fontSize": 10,
                        "maxRotation": 0,
                        "autoSkip": True,
                        "maxTicksLimit": 15,
                        "padding": 8,
                    },
                    "gridLines": {"display": False},
                }],
            },
            "title": {
                "display": True,
                "text": title_text,
                "fontSize": 16,
                "fontStyle": "bold",
                "fontColor": _COLORS["title"],
                "padding": 20,
            },
            "legend": {
                "position": "bottom",
                "labels": {
                    "usePointStyle": True,
                    "padding": 20,
                    "fontSize": 12,
                    "fontColor": "#475569",
                },
            },
            "annotation": {
                "annotations": [
                    {
                        "type": "box",
                        "yScaleID": "y-axis-0",
                        "yMin": BP_DIA_MAX,
                        "yMax": BP_SYS_MAX,
                        "backgroundColor": _COLORS["diaZone"],
                        "borderWidth": 0,
                        "label": {
                            "enabled": True,
                            "content": high_dia_label,
                            "position": "start",
                            "fontSize": 10,
                            "fontColor": "#0891b2",
                        },
                    },
                    {
                        "type": "box",
                        "yScaleID": "y-axis-0",
                        "yMin": BP_SYS_MAX,
                        "yMax": y_max,
                        "backgroundColor": _COLORS["sysZone"],
                        "borderWidth": 0,
                        "label": {
                            "enabled": True,
                            "content": high_sys_label,
                            "position": "start",
                            "fontSize": 10,
                            "fontColor": "#ef4444",
                        },
                    },
                    {
                        "type": "line",
                        "mode": "horizontal",
                        "scaleID": "y-axis-0",
                        "value": BP_SYS_MAX,
                        "borderColor": _COLORS["sysRef"],
                        "borderWidth": 1,
                        "borderDash": [6, 4],
                    },
                    {
                        "type": "line",
                        "mode": "horizontal",
                        "scaleID": "y-axis-0",
                        "value": BP_DIA_MAX,
                        "borderColor": _COLORS["diaRef"],
                        "borderWidth": 1,
                        "borderDash": [6, 4],
                    },
                ],
            },
            "plugins": {
                "datalabels": {
                    "display": True,
                },
            },
        },
    }

    # Convert to JSON string, then inject JavaScript formatters
    chart_json = json.dumps(chart_config)

    # Replace formatter placeholders with JS functions
    # Systolic formatter: show "SYS/DIA" format
    sys_formatter_js = (
        "(val, ctx) => { "
        f"const dia = {json.dumps(dia_vals)}; "
        "return val + '/' + dia[ctx.dataIndex]; }"
    )
    pulse_formatter_js = "(val) => { return 'P:' + val; }"

    chart_json = chart_json.replace('"__SYSTOLIC_FORMATTER__"', sys_formatter_js)
    chart_json = chart_json.replace('"__PULSE_FORMATTER__"', pulse_formatter_js)

    # QuickChart.io request — send chart as string so JS functions are evaluated
    request_body = json.dumps({
        "version": "2",
        "width": 1200,
        "height": 600,
        "backgroundColor": "white",
        "chart": chart_json,
    })

    try:
        response = httpx.post(
            QUICKCHART_URL,
            content=request_body,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"QuickChart.io API error: {e.response.status_code} — {e.response.text[:200]}")
    except httpx.RequestError as e:
        raise RuntimeError(f"QuickChart.io request failed: {e}")

    if len(response.content) < 100:
        raise RuntimeError("QuickChart.io returned too little data (likely not a valid PNG)")

    return BytesIO(response.content)


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
