"use client";

// Submit hook with offline fallback (PWA_SPEC §7.2).
// Online + success → "saved". Offline / network error → queued locally
// → "queued". 4xx (validation etc.) is rethrown — invalid data must
// never enter the queue.
import { useCallback } from "react";
import axios from "axios";
import api from "@/lib/api";
import { enqueue, type BPRecordCreatePayload } from "./offlineQueue";
import { notifyQueueChanged, registerBackgroundSync } from "./syncEngine";

export type SubmitOutcome = "saved" | "queued";

export interface BPRecordInput {
    systolic: number;
    diastolic: number;
    pulse: number;
    measurement_date: string;
    measurement_time?: string | null;
    notes?: string | null;
}

// Mirrors backend BloodPressureRecordCreate ranges (app/schemas.py) so
// invalid values fail immediately even when offline — they must never
// enter the queue (they would only 422 on sync).
function validateRanges(input: BPRecordInput): void {
    const checks: Array<[number, number, number]> = [
        [input.systolic, 50, 300],
        [input.diastolic, 30, 200],
        [input.pulse, 30, 200],
    ];
    for (const [value, min, max] of checks) {
        if (!Number.isFinite(value) || value < min || value > max) {
            throw new Error("out_of_range");
        }
    }
}

export function useBPRecordSubmit() {
    const submitRecord = useCallback(
        async (input: BPRecordInput): Promise<SubmitOutcome> => {
            validateRanges(input);
            const payload: BPRecordCreatePayload = {
                ...input,
                client_record_id: crypto.randomUUID(),
            };

            try {
                await api.post("/bp-records", payload);
                return "saved";
            } catch (error) {
                const isNetworkFailure =
                    !navigator.onLine ||
                    (axios.isAxiosError(error) && !error.response);
                if (!isNetworkFailure) {
                    throw error; // validation/4xx/5xx with a response → normal error UX
                }
                await enqueue(payload);
                notifyQueueChanged();
                void registerBackgroundSync();
                return "queued";
            }
        },
        [],
    );

    return { submitRecord };
}
