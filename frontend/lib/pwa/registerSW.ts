// Service worker registration + D5 update flow helpers.
// The SW is served by app/serwist/[path]/route.ts (@serwist/turbopack)
// with Service-Worker-Allowed: / so scope "/" works from /serwist/.
export const SW_URL = "/serwist/sw.js";

export type WaitingCallback = (
    waiting: ServiceWorker,
    registration: ServiceWorkerRegistration,
) => void;

export async function registerServiceWorker(
    onWaiting?: WaitingCallback,
): Promise<ServiceWorkerRegistration | null> {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
        return null;
    }
    if (process.env.NODE_ENV !== "production") {
        return null;
    }

    try {
        const registration = await navigator.serviceWorker.register(SW_URL, {
            scope: "/",
        });

        // A new version was already waiting when the page loaded.
        // Only prompt when a controller exists — first-ever install
        // activates silently and needs no prompt (D5 targets updates).
        if (registration.waiting && navigator.serviceWorker.controller) {
            onWaiting?.(registration.waiting, registration);
        }

        registration.addEventListener("updatefound", () => {
            const installing = registration.installing;
            if (!installing) return;
            installing.addEventListener("statechange", () => {
                if (
                    installing.state === "installed" &&
                    navigator.serviceWorker.controller
                ) {
                    onWaiting?.(installing, registration);
                }
            });
        });

        return registration;
    } catch (error) {
        console.error("Service worker registration failed:", error);
        return null;
    }
}

/** D5 "update now": tell the waiting SW to activate, reload on takeover. */
export function applyUpdate(waiting: ServiceWorker) {
    let reloaded = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (reloaded) return;
        reloaded = true;
        window.location.reload();
    });
    waiting.postMessage({ type: "SKIP_WAITING" });
}
