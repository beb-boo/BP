import api from "@/lib/api";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || "";

export type PushState =
    | "unsupported"   // browser lacks Push API / no active SW (e.g. dev mode)
    | "denied"        // user blocked notifications in browser settings
    | "unsubscribed"
    | "subscribed";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i++) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function getReadyRegistration(): Promise<ServiceWorkerRegistration | null> {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        return null;
    }
    const registration = await navigator.serviceWorker.getRegistration("/");
    if (!registration?.active) return null;
    return registration;
}

export async function getSubscriptionState(): Promise<PushState> {
    if (typeof window === "undefined") return "unsupported";
    if (!("Notification" in window)) return "unsupported";
    const registration = await getReadyRegistration();
    if (!registration) return "unsupported";
    if (Notification.permission === "denied") return "denied";
    const subscription = await registration.pushManager.getSubscription();
    return subscription ? "subscribed" : "unsubscribed";
}

/** Must be called from a user gesture (Notification.requestPermission rule). */
export async function subscribeToPush(): Promise<void> {
    if (!VAPID_PUBLIC_KEY) {
        throw new Error("NEXT_PUBLIC_VAPID_PUBLIC_KEY is not configured");
    }
    const registration = await getReadyRegistration();
    if (!registration) {
        throw new Error("Service worker not active");
    }

    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        throw new Error("permission_denied");
    }

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY) as BufferSource,
    });

    const json = subscription.toJSON();
    await api.post("/push/subscribe", {
        endpoint: subscription.endpoint,
        keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
    });
}

export async function unsubscribeFromPush(): Promise<void> {
    const registration = await getReadyRegistration();
    const subscription = await registration?.pushManager.getSubscription();
    if (!subscription) return;

    const endpoint = subscription.endpoint;
    await subscription.unsubscribe();
    // Backend unsubscribe is idempotent; don't fail the UI if it errors.
    try {
        await api.delete("/push/subscribe", { data: { endpoint } });
    } catch {
        // subscription is already gone locally — backend row stays
        // inactive-able via 410 handling on next send
    }
}

export async function sendTestNotification(): Promise<boolean> {
    const res = await api.post("/push/test");
    return res.data?.data?.delivered === true;
}
