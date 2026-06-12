// Logout hygiene (PWA_SPEC §4.1 warning + §7.4): the offline queue and
// runtime caches hold PHI on the device — wipe both so shared machines
// don't leak the previous user's data.
import { clearAll } from "./offlineQueue";

export async function clearOfflineData(): Promise<void> {
    try {
        await clearAll();
    } catch {
        // idb unavailable (SSR/private mode) — nothing stored anyway
    }
    try {
        if (typeof caches !== "undefined") {
            const names = await caches.keys();
            await Promise.all(names.map((name) => caches.delete(name)));
        }
    } catch {
        // CacheStorage unavailable — nothing cached
    }
}
