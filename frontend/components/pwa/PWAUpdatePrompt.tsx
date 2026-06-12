"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { applyUpdate, registerServiceWorker } from "@/lib/pwa/registerSW";

/**
 * Registers the service worker and, when a new version is waiting,
 * asks the user before activating it (D5) — a persistent toast with
 * "update now" / "later". "Later" lets the normal SW lifecycle apply
 * the update once all tabs close.
 */
export default function PWAUpdatePrompt() {
    const { t } = useLanguage();
    const promptedRef = useRef(false);
    const tRef = useRef(t);

    useEffect(() => {
        tRef.current = t;
    }, [t]);

    useEffect(() => {
        registerServiceWorker((waiting) => {
            if (promptedRef.current) return;
            promptedRef.current = true;
            toast(tRef.current("pwa.update.available"), {
                duration: Infinity,
                action: {
                    label: tRef.current("pwa.update.now"),
                    onClick: () => applyUpdate(waiting),
                },
                cancel: {
                    label: tRef.current("pwa.update.later"),
                    onClick: () => {
                        promptedRef.current = false;
                    },
                },
            });
        });
    }, []);

    return null;
}
