import { defaultCache } from "@serwist/turbopack/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import {
    CacheFirst,
    ExpirationPlugin,
    NetworkFirst,
    NetworkOnly,
    Serwist,
    StaleWhileRevalidate,
} from "serwist";

declare global {
    interface WorkerGlobalScope extends SerwistGlobalConfig {
        __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
    }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
    precacheEntries: self.__SW_MANIFEST,
    // D5: never auto-activate a new SW — PWAUpdatePrompt asks the user first.
    skipWaiting: false,
    clientsClaim: true,
    navigationPreload: true,
    runtimeCaching: [
        // Order matters: first match wins. Custom rules must precede
        // defaultCache, whose generic /api NetworkFirst entry would
        // otherwise cache credential flows and PII responses.
        {
            // Credential flows must never be cached.
            matcher: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/api/v1/auth"),
            handler: new NetworkOnly(),
        },
        {
            // OCR must reach Gemini; nothing cacheable about it.
            matcher: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/api/v1/ocr"),
            handler: new NetworkOnly(),
        },
        {
            // Telegram Mini App routes: keep the SW hands-off so cached
            // shells can never break initData auth inside Telegram.
            matcher: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/telegram"),
            handler: new NetworkOnly(),
        },
        {
            // BP history readable offline.
            matcher: ({ url, sameOrigin, request }) =>
                sameOrigin &&
                request.method === "GET" &&
                url.pathname.startsWith("/api/v1/bp-records"),
            handler: new NetworkFirst({
                cacheName: "bp-records",
                networkTimeoutSeconds: 5,
                plugins: [
                    new ExpirationPlugin({
                        maxEntries: 32,
                        maxAgeSeconds: 24 * 60 * 60,
                    }),
                ],
            }),
        },
        {
            // Stats: show stale immediately, refresh in background.
            matcher: ({ url, sameOrigin, request }) =>
                sameOrigin &&
                request.method === "GET" &&
                url.pathname.startsWith("/api/v1/stats"),
            handler: new StaleWhileRevalidate({
                cacheName: "bp-stats",
                plugins: [
                    new ExpirationPlugin({
                        maxEntries: 16,
                        maxAgeSeconds: 24 * 60 * 60,
                    }),
                ],
            }),
        },
        {
            // Everything else under /api/v1: network only. Blocks
            // defaultCache's generic /api NetworkFirst from caching
            // doctor/admin/user PII. (Non-GET requests never match
            // runtime caching anyway — they always hit the network.)
            matcher: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/api/v1"),
            handler: new NetworkOnly(),
        },
        {
            // App icons: immutable placeholder assets.
            matcher: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/icons/"),
            handler: new CacheFirst({
                cacheName: "app-icons",
                plugins: [
                    new ExpirationPlugin({
                        maxEntries: 8,
                        maxAgeSeconds: 365 * 24 * 60 * 60,
                    }),
                ],
            }),
        },
        ...defaultCache,
    ],
    fallbacks: {
        entries: [
            {
                url: "/~offline",
                matcher({ request }) {
                    return request.destination === "document";
                },
            },
        ],
    },
});

self.addEventListener("push", (event) => {
    const data = (() => {
        try {
            return event.data?.json() ?? {};
        } catch {
            return { body: event.data?.text() };
        }
    })();
    event.waitUntil(
        self.registration.showNotification(data.title ?? "BP Monitor", {
            body: data.body,
            icon: "/icons/icon-192.png",
            badge: "/icons/icon-192.png",
            tag: data.tag,
            data: { url: data.url ?? "/" },
        }),
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const url = event.notification.data?.url ?? "/";
    event.waitUntil(
        (async () => {
            const clientList = await self.clients.matchAll({
                type: "window",
                includeUncontrolled: true,
            });
            for (const client of clientList) {
                if (new URL(client.url).origin === self.location.origin) {
                    await client.focus();
                    if ("navigate" in client) {
                        await client.navigate(url);
                    }
                    return;
                }
            }
            await self.clients.openWindow(url);
        })(),
    );
});

self.addEventListener("message", (event) => {
    // D5: activation only happens when the user confirms in PWAUpdatePrompt.
    if (event.data?.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

// Background Sync (Android Chrome): the offline queue lives in the
// client (idb + axios auth), so the SW just wakes any open window to
// run the sync. Client-side triggers (online/mount/manual) remain the
// primary mechanism — they also cover iOS, which lacks Background Sync.
self.addEventListener("sync", (event) => {
    const syncEvent = event as Event & { tag?: string; waitUntil(p: Promise<unknown>): void };
    if (syncEvent.tag !== "bp-sync") return;
    syncEvent.waitUntil(
        (async () => {
            const clientList = await self.clients.matchAll({ type: "window" });
            for (const client of clientList) {
                client.postMessage({ type: "SYNC_BP_QUEUE" });
            }
        })(),
    );
});

serwist.addEventListeners();
