
"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTelegramWebApp,
  telegramApi,
  setTelegramToken,
  type TelegramUser,
} from "@/lib/telegram";
import { buildLocalDateTimePayload, formatDateForInput, formatTimeForInput } from "@/lib/date-utils";
import { getApiErrorMessage, type ApiResponse } from "@/lib/api-helpers";
import type { BPRecord, BPStats, OCRResultPayload } from "@/lib/app-types";

// ── Classification colors ──

const classColors: Record<string, { bg: string; text: string; emoji: string }> = {
  normal: { bg: "bg-green-100", text: "text-green-800", emoji: "\uD83D\uDFE2" },
  elevated: { bg: "bg-yellow-100", text: "text-yellow-800", emoji: "\uD83D\uDFE1" },
  stage_1: { bg: "bg-orange-100", text: "text-orange-800", emoji: "\uD83D\uDFE0" },
  stage_2: { bg: "bg-red-100", text: "text-red-800", emoji: "\uD83D\uDD34" },
  hypertensive_crisis: { bg: "bg-red-200", text: "text-red-900", emoji: "\uD83D\uDEA8" },
};

export default function TelegramBPPage() {
  // ── State ──
  const [tgUser, setTgUser] = useState<TelegramUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPremium, setIsPremium] = useState(false);

  // Form
  const [systolic, setSystolic] = useState("");
  const [diastolic, setDiastolic] = useState("");
  const [pulse, setPulse] = useState("");
  const [measureDate, setMeasureDate] = useState("");
  const [measureTime, setMeasureTime] = useState("");
  const [saving, setSaving] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);

  // Data
  const [stats, setStats] = useState<BPStats | null>(null);
  const [records, setRecords] = useState<BPRecord[]>([]);

  // Edit modal
  const [editingRecord, setEditingRecord] = useState<BPRecord | null>(null);
  const [editSys, setEditSys] = useState("");
  const [editDia, setEditDia] = useState("");
  const [editPulse, setEditPulse] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editTime, setEditTime] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  // Theme
  const [isDark, setIsDark] = useState(false);

  // ── Init ──
  useEffect(() => {
    const tg = getTelegramWebApp();
    if (!tg) {
      setAuthError("Please open this page from Telegram");
      setLoading(false);
      return;
    }

    tg.ready();
    tg.expand();
    setIsDark(tg.colorScheme === "dark");

    const user = tg.initDataUnsafe.user;
    if (user) setTgUser(user);

    // Authenticate
    authenticate(tg.initData);
  }, []);

  async function authenticate(initData: string) {
    try {
      const res = await telegramApi.post<ApiResponse<{ access_token: string }>>("/auth/telegram/mini-app-auth", {
        init_data: initData,
      });
      const { access_token } = res.data.data;
      setTelegramToken(access_token);

      // Load data after auth
      await Promise.all([fetchStats(), fetchRecords()]);
    } catch (error: unknown) {
      setAuthError(getApiErrorMessage(error, "Authentication failed"));
    } finally {
      setLoading(false);
    }
  }

  // ── Data fetching ──

  const fetchStats = useCallback(async () => {
    try {
      const res = await telegramApi.get<ApiResponse<{ stats: BPStats; is_premium: boolean }>>("/stats/summary?days=30");
      const data = res.data.data;
      setStats(data.stats);
      setIsPremium(data.is_premium);
    } catch {
      // Stats not critical — ignore
    }
  }, []);

  const fetchRecords = useCallback(async () => {
    try {
      const res = await telegramApi.get<ApiResponse<{ records: BPRecord[] }>>("/bp-records?page=1&per_page=5");
      setRecords(res.data.data?.records || []);
    } catch {
      // ignore
    }
  }, []);

  // ── Save BP ──

  async function handleSave() {
    const sys = parseInt(systolic);
    const dia = parseInt(diastolic);
    const pul = parseInt(pulse);

    if (!sys || !dia || !pul) return;
    if (sys < 50 || sys > 300 || dia < 30 || dia > 200 || pul < 30 || pul > 200) {
      getTelegramWebApp()?.showAlert("Invalid values. Check your input.");
      return;
    }

    // Confirmation dialog
    const tg = getTelegramWebApp();
    if (tg) {
      tg.showConfirm(
        `Save ${sys}/${dia} (${pul})?`,
        (confirmed) => {
          if (confirmed) doSave(sys, dia, pul);
        }
      );
    } else {
      doSave(sys, dia, pul);
    }
  }

  async function doSave(sys: number, dia: number, pul: number) {
    setSaving(true);
    try {
      const now = new Date();
      const date = measureDate || formatDateForInput(now);
      const time = measureTime || formatTimeForInput(now);

      await telegramApi.post("/bp-records", {
        systolic: sys,
        diastolic: dia,
        pulse: pul,
        measurement_date: buildLocalDateTimePayload(date, time),
        measurement_time: time,
      });

      // Clear form
      setSystolic("");
      setDiastolic("");
      setPulse("");
      setMeasureDate("");
      setMeasureTime("");

      // Refresh data
      await Promise.all([fetchStats(), fetchRecords()]);

      getTelegramWebApp()?.showAlert("Saved!");
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, "Save failed");
      getTelegramWebApp()?.showAlert(`Save failed: ${detail}`);
    } finally {
      setSaving(false);
    }
  }

  // ── OCR Upload ──

  async function handleOCR(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setOcrLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await telegramApi.post<ApiResponse<{ ocr_result: OCRResultPayload }>>("/ocr/process-image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const ocr = res.data.data?.ocr_result;
      if (ocr?.systolic) setSystolic(String(ocr.systolic));
      if (ocr?.diastolic) setDiastolic(String(ocr.diastolic));
      if (ocr?.pulse) setPulse(String(ocr.pulse));
      if (ocr?.measurement_date) setMeasureDate(ocr.measurement_date);
      if (ocr?.measurement_time) setMeasureTime(ocr.measurement_time);

      // Same as web: fill form, let user verify & press Save
      const parts = [
        ocr?.systolic && ocr?.diastolic ? `${ocr.systolic}/${ocr.diastolic}` : null,
        ocr?.pulse ? `Pulse ${ocr.pulse}` : null,
        ocr?.measurement_date ? `${ocr.measurement_date} ${ocr.measurement_time || ""}`.trim() : null,
      ].filter(Boolean);
      getTelegramWebApp()?.showAlert(
        `Read: ${parts.join(", ")}\nPlease check and press Save.`
      );
    } catch (error: unknown) {
      getTelegramWebApp()?.showAlert(getApiErrorMessage(error, "Could not read photo. Please enter manually."));
    } finally {
      setOcrLoading(false);
      // Reset input so same file can be re-selected
      e.target.value = "";
    }
  }

  // ── Edit record ──

  const closeEditModal = useCallback(() => {
    setEditingRecord(null);
  }, []);

  function openEditModal(record: BPRecord) {
    setEditingRecord(record);
    setEditSys(String(record.systolic));
    setEditDia(String(record.diastolic));
    setEditPulse(String(record.pulse));
    setEditDate(formatDateForInput(new Date(record.measurement_date)));
    setEditTime(record.measurement_time || "");
  }

  async function handleEditSave() {
    if (!editingRecord) return;
    const sys = parseInt(editSys);
    const dia = parseInt(editDia);
    const pul = parseInt(editPulse);

    if (!sys || !dia || !pul) return;
    if (sys < 50 || sys > 300 || dia < 30 || dia > 200 || pul < 30 || pul > 200) {
      getTelegramWebApp()?.showAlert("Invalid values. Check your input.");
      return;
    }

    setEditSaving(true);
    try {
      await telegramApi.put(`/bp-records/${editingRecord.id}`, {
        systolic: sys,
        diastolic: dia,
        pulse: pul,
        measurement_date: buildLocalDateTimePayload(editDate, editTime),
        measurement_time: editTime,
      });
      await Promise.all([fetchStats(), fetchRecords()]);
      closeEditModal();
      getTelegramWebApp()?.showAlert("Updated!");
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, "Update failed");
      getTelegramWebApp()?.showAlert(`Update failed: ${detail}`);
    } finally {
      setEditSaving(false);
    }
  }

  // Wire Telegram BackButton to close the edit modal (mirrors native mobile back gesture).
  useEffect(() => {
    const tg = getTelegramWebApp();
    if (!tg) return;
    if (editingRecord) {
      tg.BackButton.show();
      tg.BackButton.onClick(closeEditModal);
      return () => {
        tg.BackButton.offClick(closeEditModal);
        tg.BackButton.hide();
      };
    }
  }, [editingRecord, closeEditModal]);

  // ── Render helpers ──

  const themeClass = isDark
    ? "bg-gray-900 text-gray-100"
    : "bg-gray-50 text-gray-900";
  const cardClass = isDark
    ? "bg-gray-800 border-gray-700"
    : "bg-white border-gray-200";
  const inputClass = isDark
    ? "bg-gray-700 border-gray-600 text-white placeholder-gray-400"
    : "bg-white border-gray-300 text-gray-900 placeholder-gray-400";

  // ── Loading / Error states ──

  if (loading) {
    return (
      <div className={`flex items-center justify-center min-h-screen ${themeClass}`}>
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm opacity-70">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (authError) {
    return (
      <div className={`flex items-center justify-center min-h-screen p-4 ${themeClass}`}>
        <div className={`rounded-xl border p-6 text-center max-w-sm ${cardClass}`}>
          <p className="text-4xl mb-3">{"⚠️"}</p>
          <p className="font-medium mb-2">Cannot authenticate</p>
          <p className="text-sm opacity-70 mb-4">{authError}</p>
          {authError.includes("not linked") && (
            <p className="text-xs opacity-50">
              Use <strong>/start</strong> in the bot to link your account first.
            </p>
          )}
        </div>
      </div>
    );
  }

  // ── Main UI ──

  return (
    <div className={`min-h-screen p-3 pb-6 ${themeClass}`}>
      {/* Header */}
      <div className="mb-4">
        <p className="text-lg font-semibold">
          {tgUser ? `Hello, ${tgUser.first_name}` : "Blood Pressure"}
        </p>
        <p className="text-xs opacity-60">Record your blood pressure</p>
      </div>

      {/* BP Input Form */}
      <div className={`rounded-xl border p-4 mb-4 ${cardClass}`}>
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">
              SYS
            </label>
            <input
              type="number"
              inputMode="numeric"
              placeholder="120"
              value={systolic}
              onChange={(e) => setSystolic(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">
              DIA
            </label>
            <input
              type="number"
              inputMode="numeric"
              placeholder="80"
              value={diastolic}
              onChange={(e) => setDiastolic(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">
              PULSE
            </label>
            <input
              type="number"
              inputMode="numeric"
              placeholder="72"
              value={pulse}
              onChange={(e) => setPulse(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
            />
          </div>
        </div>

        {/* Date/Time row — shown when OCR fills values or user can edit */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">
              DATE
            </label>
            <input
              type="date"
              value={measureDate}
              onChange={(e) => setMeasureDate(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 text-sm ${inputClass}`}
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">
              TIME
            </label>
            <input
              type="time"
              value={measureTime}
              onChange={(e) => setMeasureTime(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 text-sm ${inputClass}`}
            />
          </div>
        </div>

        <div className="flex gap-2">
          <label
            className={`flex items-center justify-center rounded-lg border px-4 py-2.5 font-medium cursor-pointer active:opacity-70 transition-opacity ${
              ocrLoading ? "opacity-40 pointer-events-none" : ""
            } ${isDark ? "border-gray-600 text-gray-300" : "border-gray-300 text-gray-700"}`}
          >
            {ocrLoading ? "..." : "\uD83D\uDCF7"}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleOCR}
              className="hidden"
            />
          </label>
          <button
            onClick={handleSave}
            disabled={saving || !systolic || !diastolic || !pulse}
            className="flex-1 rounded-lg bg-blue-600 text-white py-2.5 font-medium disabled:opacity-40 active:bg-blue-700 transition-colors"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {/* Stats Section */}
      {stats && (
        <div className={`rounded-xl border p-4 mb-4 ${cardClass}`}>
          <p className="text-xs font-medium opacity-50 mb-3">
            Stats ({stats.total_records_period} records)
          </p>

          {/* Average + Classification */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-2xl font-bold">
                {Math.round(stats.systolic.avg)}/{Math.round(stats.diastolic.avg)}
              </p>
              <p className="text-xs opacity-50">
                Pulse: {Math.round(stats.pulse.avg)} bpm
              </p>
            </div>
            {stats.classification && (
              <div
                className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                  classColors[stats.classification.level]?.bg || "bg-gray-100"
                } ${classColors[stats.classification.level]?.text || "text-gray-800"}`}
              >
                {classColors[stats.classification.level]?.emoji}{" "}
                {stats.classification.label_en}
              </div>
            )}
          </div>

          {/* Premium stats */}
          {isPremium && (
            <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
              {stats.systolic.sd !== undefined && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-40">
                    SD (variability)
                  </p>
                  <p className="text-sm font-medium">
                    {"\u00B1"}{stats.systolic.sd}/{stats.diastolic.sd}
                  </p>
                </div>
              )}
              {stats.pulse_pressure && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-40">
                    Pulse Pressure
                  </p>
                  <p className="text-sm font-medium">
                    {Math.round(stats.pulse_pressure.avg)} mmHg
                  </p>
                </div>
              )}
              {stats.map && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-40">
                    MAP
                  </p>
                  <p className="text-sm font-medium">
                    {Math.round(stats.map.avg)} mmHg
                  </p>
                </div>
              )}
              {stats.trend && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-40">
                    Trend
                  </p>
                  <p className="text-sm font-medium">
                    {stats.trend.direction === "increasing"
                      ? "\uD83D\uDCC8"
                      : stats.trend.direction === "decreasing"
                      ? "\uD83D\uDCC9"
                      : "\u27A1\uFE0F"}{" "}
                    {stats.trend.systolic_slope > 0 ? "+" : ""}
                    {stats.trend.systolic_slope.toFixed(1)} mmHg/day
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Free tier upgrade hint */}
          {!isPremium && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
              <p className="text-xs opacity-50 text-center">
                {"\uD83D\uDD12"} Unlock SD, Trend, Pulse Pressure, MAP with Premium
              </p>
            </div>
          )}
        </div>
      )}

      {/* Recent Records */}
      {records.length > 0 && (
        <div className={`rounded-xl border p-4 ${cardClass}`}>
          <p className="text-xs font-medium opacity-50 mb-3">
            Latest ({records.length})
          </p>
          <div className="space-y-2">
            {records.map((r) => {
              const d = new Date(r.measurement_date);
              const dateStr = `${d.getDate().toString().padStart(2, "0")}/${(
                d.getMonth() + 1
              )
                .toString()
                .padStart(2, "0")}`;
              const timeStr = r.measurement_time || d.toTimeString().slice(0, 5);
              return (
                <button
                  type="button"
                  key={r.id}
                  onClick={() => openEditModal(r)}
                  className={`w-full flex items-center justify-between py-1.5 px-1 -mx-1 rounded-md text-left transition-colors active:opacity-60 ${
                    isDark ? "hover:bg-gray-700/50" : "hover:bg-gray-100"
                  }`}
                  aria-label={`Edit ${dateStr} ${timeStr} record`}
                >
                  <span className="text-xs opacity-50 w-20">
                    {dateStr} {timeStr}
                  </span>
                  <span className="font-mono text-sm font-medium">
                    {r.systolic}/{r.diastolic}
                  </span>
                  <span className="text-xs opacity-50 flex items-center gap-1">
                    ({r.pulse})
                    <span aria-hidden className="opacity-40">{"\u203A"}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Edit Record Modal (full-screen bottom sheet for small viewports) */}
      {editingRecord && (
        <div
          className={`fixed inset-0 z-50 flex flex-col ${themeClass}`}
          role="dialog"
          aria-modal="true"
          aria-label="Edit record"
        >
          <div className={`flex items-center justify-between px-4 py-3 border-b ${isDark ? "border-gray-700" : "border-gray-200"}`}>
            <p className="font-semibold">Edit record</p>
            <button
              type="button"
              onClick={closeEditModal}
              className="text-sm opacity-60 active:opacity-40 px-2 py-1"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">SYS</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={editSys}
                  onChange={(e) => setEditSys(e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">DIA</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={editDia}
                  onChange={(e) => setEditDia(e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">PULSE</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={editPulse}
                  onChange={(e) => setEditPulse(e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2.5 text-center text-lg font-bold ${inputClass}`}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">DATE</label>
                <input
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2 text-sm ${inputClass}`}
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider opacity-50 mb-1 block">TIME</label>
                <input
                  type="time"
                  value={editTime}
                  onChange={(e) => setEditTime(e.target.value)}
                  className={`w-full rounded-lg border px-3 py-2 text-sm ${inputClass}`}
                />
              </div>
            </div>
          </div>

          <div className={`border-t p-3 flex gap-2 ${isDark ? "border-gray-700" : "border-gray-200"}`}>
            <button
              type="button"
              onClick={closeEditModal}
              disabled={editSaving}
              className={`flex-1 rounded-lg border px-4 py-3 font-medium active:opacity-70 ${isDark ? "border-gray-600 text-gray-300" : "border-gray-300 text-gray-700"}`}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleEditSave}
              disabled={editSaving}
              className="flex-1 rounded-lg bg-blue-500 text-white px-4 py-3 font-medium active:bg-blue-600 disabled:opacity-50"
            >
              {editSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
