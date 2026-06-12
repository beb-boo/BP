// Sync engine for the offline BP queue (PWA_SPEC §7.2).
//
// Triggers (all client-side): window "online" event, app mount, and the
// manual button in OfflineSyncIndicator — these cover iOS, which has no
// Background Sync. The SW additionally forwards Background Sync events
// here via a SYNC_BP_QUEUE message when a window is open (enhancement,
// not load-bearing). Running sync in the client keeps it testable and
// reuses the axios instance (auth headers, 401 handling) instead of
// duplicating that logic inside the service worker.
import axios from "axios";
import api from "@/lib/api";
import { getAll, remove, update, type QueuedBPRecord } from "./offlineQueue";

const MAX_RETRIES = 5;

export interface SyncResult {
    synced: number;
    failed: number;
    remaining: number;
}

let syncing = false;
const listeners = new Set<() => void>();

/** Subscribe to queue-changed events (indicator refresh). */
export function onQueueChanged(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

export function notifyQueueChanged(): void {
    listeners.forEach((fn) => fn());
}

async function syncOne(item: QueuedBPRecord): Promise<"synced" | "retry" | "failed"> {
    try {
        await api.post("/bp-records", item.payload);
        return "synced";
    } catch (error) {
        if (axios.isAxiosError(error) && error.response) {
            const status = error.response.status;
            // 409 = server already has it (legacy duplicate check) — done.
            if (status === 409) return "synced";
            // Other 4xx = permanently rejected (validation/auth) — no point retrying.
            if (status >= 400 && status < 500) return "failed";
        }
        // Network-level failure — retry later.
        return "retry";
    }
}

export async function syncQueue(): Promise<SyncResult> {
    if (syncing) return { synced: 0, failed: 0, remaining: await countPending() };
    syncing = true;
    let synced = 0;
    let failed = 0;
    try {
        const items = (await getAll()).filter((i) => i.status !== "syncing");
        for (const item of items) {
            if (item.status === "failed") continue; // user must retry/delete explicitly
            await update({ ...item, status: "syncing" });
            const outcome = await syncOne(item);
            if (outcome === "synced") {
                await remove(item.id);
                synced++;
            } else {
                const retryCount = item.retryCount + 1;
                const exhausted = outcome === "failed" || retryCount >= MAX_RETRIES;
                await update({
                    ...item,
                    retryCount,
                    status: exhausted ? "failed" : "pending",
                    lastError: outcome,
                });
                if (exhausted) failed++;
            }
        }
    } finally {
        syncing = false;
        notifyQueueChanged();
    }
    const remaining = await countPending();
    return { synced, failed, remaining };
}

async function countPending(): Promise<number> {
    return (await getAll()).length;
}

/** Reset a failed item so the next sync attempt picks it up again. */
export async function retryFailed(id: string): Promise<void> {
    const item = (await getAll()).find((i) => i.id === id);
    if (item) {
        await update({ ...item, status: "pending", retryCount: 0 });
        notifyQueueChanged();
    }
}

let triggersInstalled = false;

/** Install global sync triggers once (online event + SW message). */
export function installSyncTriggers(): void {
    if (triggersInstalled || typeof window === "undefined") return;
    triggersInstalled = true;

    window.addEventListener("online", () => {
        void syncQueue();
    });

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.addEventListener("message", (event) => {
            if (event.data?.type === "SYNC_BP_QUEUE") {
                void syncQueue();
            }
        });
    }
}

/** Best-effort Background Sync registration (Android Chrome). */
export async function registerBackgroundSync(): Promise<void> {
    try {
        const registration = await navigator.serviceWorker?.getRegistration("/");
        const syncManager = (registration as unknown as { sync?: { register(tag: string): Promise<void> } })?.sync;
        await syncManager?.register("bp-sync");
    } catch {
        // unsupported (iOS/Firefox) — client triggers cover it
    }
}
