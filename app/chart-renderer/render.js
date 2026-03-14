#!/usr/bin/env node
/**
 * BP Chart Renderer — Server-side Chart.js + @napi-rs/canvas → PNG
 *
 * Usage: echo '{"labels":[...],"systolic":[...],...}' | node render.js
 * Outputs: PNG image bytes to stdout
 */
'use strict';

const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const { Chart, registerables } = require('chart.js');
const annotationPlugin = require('chartjs-plugin-annotation');

// Register Chart.js components + annotation plugin
Chart.register(...registerables, annotationPlugin);

// ── Colors (same as frontend bp-chart.tsx) ──────────────────────
const COLORS = {
    sys:       '#ef4444',
    dia:       '#3b82f6',
    pulse:     '#10b981',
    sysZone:   'rgba(239, 68, 68, 0.07)',
    diaZone:   'rgba(6, 182, 212, 0.07)',
    sysRef:    'rgba(239, 68, 68, 0.4)',
    diaRef:    'rgba(6, 182, 212, 0.4)',
    grid:      'rgba(148, 163, 184, 0.15)',
    text:      '#374151',
    textLight: '#64748b',
    title:     '#1e293b',
    labelBg:   'rgba(255, 255, 255, 0.9)',
    labelBdr:  '#d1d5db',
};

const BP_SYS_MAX = 140;
const BP_DIA_MAX = 90;

// ── Try to register Thai font (if available on system) ──────────
const THAI_FONT_PATHS = [
    '/Users/seal/Library/Fonts/Sarabun-Regular.ttf',
    '/System/Library/Fonts/Supplemental/Thonburi.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf',   // Linux
    '/usr/share/fonts/truetype/tlwg/Sarabun.ttf',                // Linux alt
];
for (const fp of THAI_FONT_PATHS) {
    try {
        GlobalFonts.registerFromPath(fp, 'ThaiFont');
        break;
    } catch (_) { /* skip */ }
}

// ── Read JSON from stdin ────────────────────────────────────────
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', async () => {
    try {
        const data = JSON.parse(input);
        const buffer = await renderBPChart(data);
        process.stdout.write(Buffer.from(buffer));
    } catch (err) {
        process.stderr.write(`Chart render error: ${err.message}\n`);
        process.exit(1);
    }
});

// ── Main render function ────────────────────────────────────────
async function renderBPChart(data) {
    const {
        labels,
        systolic,
        diastolic,
        pulse,
        lang = 'en',
        width = 1200,
        height = 600,
    } = data;

    // Y-axis bounds
    const allVals = [...systolic, ...diastolic, ...pulse];
    const dataMax = Math.max(...allVals);
    const dataMin = Math.min(...allVals);
    const yMax = Math.max(dataMax + 20, BP_SYS_MAX + 25);
    const yMin = Math.max(0, Math.min(dataMin - 10, 40));

    // Show data labels on every point
    const n = labels.length;

    // Font family
    const fontFamily = lang === 'th' ? 'ThaiFont, sans-serif' : 'sans-serif';

    // ── Create canvas ───────────────────────────────────────────
    const canvas = createCanvas(width, height);

    // Chart.js needs canvas.style to exist
    if (!canvas.style) canvas.style = {};

    const ctx = canvas.getContext('2d');

    // Fill white background
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, width, height);

    // ── Chart.js config ─────────────────────────────────────────
    const configuration = {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: lang === 'th' ? 'ความดันบน (Sys)' : 'Systolic',
                    data: systolic,
                    borderColor: COLORS.sys,
                    backgroundColor: COLORS.sys,
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointBackgroundColor: COLORS.sys,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1.5,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: lang === 'th' ? 'ความดันล่าง (Dia)' : 'Diastolic',
                    data: diastolic,
                    borderColor: COLORS.dia,
                    backgroundColor: COLORS.dia,
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointBackgroundColor: COLORS.dia,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1.5,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: lang === 'th' ? 'ชีพจร' : 'Pulse',
                    data: pulse,
                    borderColor: COLORS.pulse,
                    backgroundColor: COLORS.pulse,
                    borderWidth: 2,
                    pointRadius: 3.5,
                    pointBackgroundColor: COLORS.pulse,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1,
                    borderDash: [6, 3],
                    tension: 0.3,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: false,
            animation: false,
            layout: {
                padding: { top: 25, right: 20, bottom: 10, left: 10 },
            },
            scales: {
                y: {
                    min: yMin,
                    max: yMax,
                    grid: { color: COLORS.grid },
                    ticks: {
                        font: { size: 11, family: fontFamily },
                        color: COLORS.textLight,
                        padding: 8,
                    },
                    border: { display: false },
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 10, family: fontFamily },
                        color: COLORS.textLight,
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 15,
                        padding: 8,
                    },
                    border: { display: false },
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 20,
                        font: { size: 12, family: fontFamily },
                        color: '#475569',
                    },
                },
                title: {
                    display: true,
                    text: lang === 'th' ? 'กราฟความดันโลหิต' : 'Blood Pressure Trends',
                    font: { size: 16, weight: 'bold', family: fontFamily },
                    color: COLORS.title,
                    padding: { bottom: 20 },
                },
                tooltip: { enabled: false },
                annotation: {
                    annotations: {
                        highDiaZone: {
                            type: 'box',
                            yMin: BP_DIA_MAX,
                            yMax: BP_SYS_MAX,
                            backgroundColor: COLORS.diaZone,
                            borderWidth: 0,
                            label: {
                                display: true,
                                content: lang === 'th' ? 'ความดันล่างสูง' : 'High Dia',
                                position: { x: 'start', y: 'start' },
                                font: { size: 10, family: fontFamily },
                                color: '#0891b2',
                            },
                        },
                        highSysZone: {
                            type: 'box',
                            yMin: BP_SYS_MAX,
                            yMax: yMax,
                            backgroundColor: COLORS.sysZone,
                            borderWidth: 0,
                            label: {
                                display: true,
                                content: lang === 'th' ? 'ความดันสูง' : 'High Sys & Dia',
                                position: { x: 'start', y: 'start' },
                                font: { size: 10, family: fontFamily },
                                color: '#ef4444',
                            },
                        },
                        sysRefLine: {
                            type: 'line',
                            yMin: BP_SYS_MAX,
                            yMax: BP_SYS_MAX,
                            borderColor: COLORS.sysRef,
                            borderWidth: 1,
                            borderDash: [6, 4],
                        },
                        diaRefLine: {
                            type: 'line',
                            yMin: BP_DIA_MAX,
                            yMax: BP_DIA_MAX,
                            borderColor: COLORS.diaRef,
                            borderWidth: 1,
                            borderDash: [6, 4],
                        },
                    },
                },
            },
        },
        // ── Custom plugin: draw SYS/DIA & Pulse data labels ─────
        plugins: [
            {
                id: 'bpDataLabels',
                afterDatasetsDraw(chart) {
                    const ctx = chart.ctx;
                    const sysMeta = chart.getDatasetMeta(0);
                    const pulseMeta = chart.getDatasetMeta(2);

                    // ── SYS/DIA labels above systolic points ────
                    sysMeta.data.forEach((point, i) => {
                        const text = `${systolic[i]}/${diastolic[i]}`;
                        ctx.save();
                        ctx.font = `bold 11px ${fontFamily}`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';

                        const tm = ctx.measureText(text);
                        const pad = 5;
                        const bw = tm.width + pad * 2;
                        const bh = 16;
                        const bx = point.x - bw / 2;
                        const by = point.y - bh - 8;
                        const r = 4;

                        // Rounded-rect background
                        ctx.fillStyle = COLORS.labelBg;
                        ctx.strokeStyle = COLORS.labelBdr;
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(bx + r, by);
                        ctx.lineTo(bx + bw - r, by);
                        ctx.arcTo(bx + bw, by, bx + bw, by + r, r);
                        ctx.lineTo(bx + bw, by + bh - r);
                        ctx.arcTo(bx + bw, by + bh, bx + bw - r, by + bh, r);
                        ctx.lineTo(bx + r, by + bh);
                        ctx.arcTo(bx, by + bh, bx, by + bh - r, r);
                        ctx.lineTo(bx, by + r);
                        ctx.arcTo(bx, by, bx + r, by, r);
                        ctx.closePath();
                        ctx.fill();
                        ctx.stroke();

                        // Text
                        ctx.fillStyle = COLORS.text;
                        ctx.fillText(text, point.x, point.y - 10);
                        ctx.restore();
                    });

                    // ── Pulse labels below pulse points ─────────
                    pulseMeta.data.forEach((point, i) => {
                        ctx.save();
                        ctx.font = `bold 10px ${fontFamily}`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'top';
                        ctx.fillStyle = COLORS.pulse;
                        ctx.fillText(`P:${pulse[i]}`, point.x, point.y + 8);
                        ctx.restore();
                    });
                },
            },
        ],
    };

    // ── Create chart on canvas ──────────────────────────────────
    new Chart(ctx, configuration);

    // ── Export to PNG buffer ─────────────────────────────────────
    return canvas.toBuffer('image/png');
}
