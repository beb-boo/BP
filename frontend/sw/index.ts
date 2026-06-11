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

self.addEventListener("message", (event) => {
    // D5: activation only happens when the user confirms in PWAUpdatePrompt.
    if (event.data?.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

serwist.addEventListeners();
