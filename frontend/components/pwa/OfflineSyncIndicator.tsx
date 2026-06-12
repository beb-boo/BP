"use client";

import { useCallback, useEffect, useState } from "react";
import { CloudOff, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";
import {
    getAll,
    remove,
    type QueuedBPRecord,
} from "@/lib/pwa/offlineQueue";
import {
    installSyncTriggers,
    onQueueChanged,
    retryFailed,
    syncQueue,
} from "@/lib/pwa/syncEngine";

/**
 * Banner shown while BP records are waiting to sync (PWA_SPEC §7.4):
 * pending count, manual sync, and per-item retry/delete for failures.
 * Mounted on authenticated pages only.
 */
export default function OfflineSyncIndicator() {
    const { t } = useLanguage();
    const [items, setItems] = useState<QueuedBPRecord[]>([]);
    const [syncing, setSyncing] = useState(false);

    const refresh = useCallback(() => {
        getAll().then(setItems).catch(() => setItems([]));
    }, []);

    useEffect(() => {
        installSyncTriggers();
        refresh();
        const unsubscribe = onQueueChanged(refresh);
        // Sync on mount (app open/foreground trigger — covers iOS).
        if (navigator.onLine) {
            void syncQueue();
        }
        return unsubscribe;
    }, [refresh]);

    const handleSyncNow = async () => {
        setSyncing(true);
        try {
            const result = await syncQueue();
            if (result.synced > 0) {
                toast.success(
                    t("pwa.sync.synced").replace("{n}", String(result.synced)),
                );
            } else if (result.remaining > 0) {
                toast.info(t("pwa.sync.stillOffline"));
            }
        } finally {
            setSyncing(false);
            refresh();
        }
    };

    if (items.length === 0) return null;

    const failed = items.filter((i) => i.status === "failed");
    const pendingCount = items.length - failed.length;

    return (
        <div className="fixed inset-x-4 top-4 z-50 mx-auto max-w-md rounded-lg border border-amber-300 bg-amber-50 p-3 shadow-md dark:border-amber-700 dark:bg-amber-950">
            <div className="flex items-center gap-3">
                <CloudOff className="h-5 w-5 shrink-0 text-amber-600" />
                <p className="flex-1 text-sm text-amber-800 dark:text-amber-200">
                    {t("pwa.sync.pending").replace("{n}", String(items.length))}
                </p>
                <Button size="sm" variant="outline" onClick={handleSyncNow} disabled={syncing}>
                    {syncing ? (
                        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                    ) : (
                        <RefreshCw className="mr-1 h-4 w-4" />
                    )}
                    {t("pwa.sync.syncNow")}
                </Button>
            </div>

            {failed.length > 0 && (
                <ul className="mt-2 space-y-1 border-t border-amber-200 pt-2">
                    {failed.map((item) => (
                        <li key={item.id} className="flex items-center gap-2 text-xs text-amber-800 dark:text-amber-200">
                            <span className="flex-1">
                                {item.payload.systolic}/{item.payload.diastolic} ({item.payload.pulse})
                                {" — "}
                                {t("pwa.sync.failedItem")}
                            </span>
                            <button
                                type="button"
                                aria-label={t("pwa.sync.retry")}
                                className="text-amber-700 hover:text-amber-900"
                                onClick={() => retryFailed(item.id).then(() => syncQueue())}
                            >
                                <RefreshCw className="h-3.5 w-3.5" />
                            </button>
                            <button
                                type="button"
                                aria-label={t("common.delete")}
                                className="text-amber-700 hover:text-amber-900"
                                onClick={() => remove(item.id).then(refresh)}
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
