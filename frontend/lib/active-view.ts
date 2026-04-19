"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Generic per-browser "active view" preference for users who have access to
 * more than one view surface (e.g. a staff member who also wants to record
 * their own BP).
 *
 * Designed to be forward-compatible with v2 ORG roles: the stored value is a
 * free-form identifier, not tied to the v1 `role` column. New surfaces
 * (e.g. "asm", "rpsst_admin") can be added by widening ActiveView without
 * touching existing call sites.
 */
export type ActiveView = "admin" | "patient" | "doctor";

const STORAGE_KEY = "bp.active_view";

function read(): ActiveView | null {
    if (typeof window === "undefined") return null;
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw === "admin" || raw === "patient" || raw === "doctor") return raw;
    } catch {
        // localStorage disabled — fall back to default
    }
    return null;
}

function write(value: ActiveView | null) {
    if (typeof window === "undefined") return;
    try {
        if (value === null) {
            window.localStorage.removeItem(STORAGE_KEY);
        } else {
            window.localStorage.setItem(STORAGE_KEY, value);
        }
    } catch {
        // ignore quota / disabled storage
    }
    // Notify listeners in the same tab — `storage` event only fires cross-tab.
    if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("bp.active_view.change"));
    }
}

function subscribe(onChange: () => void): () => void {
    if (typeof window === "undefined") return () => {};
    window.addEventListener("storage", onChange);
    window.addEventListener("bp.active_view.change", onChange);
    return () => {
        window.removeEventListener("storage", onChange);
        window.removeEventListener("bp.active_view.change", onChange);
    };
}

export function useActiveView(fallback: ActiveView): [ActiveView, (v: ActiveView | null) => void] {
    const view = useSyncExternalStore<ActiveView>(
        subscribe,
        () => read() ?? fallback,
        () => fallback,
    );

    const update = useCallback((value: ActiveView | null) => {
        write(value);
    }, []);

    return [view, update];
}
