"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Cookies from "js-cookie";
import { Download, Share, SquarePlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { useLanguage } from "@/contexts/LanguageContext";

interface BeforeInstallPromptEvent extends Event {
    prompt(): Promise<void>;
    userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "pwa-install-dismissed-at";
const DISMISS_DAYS = 14;

function isDismissed(): boolean {
    try {
        const at = localStorage.getItem(DISMISS_KEY);
        if (!at) return false;
        return Date.now() - Number(at) < DISMISS_DAYS * 24 * 60 * 60 * 1000;
    } catch {
        return false;
    }
}

function isStandalone(): boolean {
    return (
        window.matchMedia("(display-mode: standalone)").matches ||
        // iOS Safari legacy flag
        (navigator as Navigator & { standalone?: boolean }).standalone === true
    );
}

function isIOS(): boolean {
    return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

/**
 * Custom install UI. Android/Chrome: captures beforeinstallprompt and
 * shows a banner only after the user is logged in (engagement signal,
 * not on first landing). iOS: instruction modal (Share → Add to Home
 * Screen). Dismissal is remembered for 14 days via localStorage.
 */
export default function PWAInstallPrompt() {
    const { t } = useLanguage();
    const pathname = usePathname();
    // Never show inside the Telegram Mini App (its WebView is not installable).
    const inTelegram = pathname?.startsWith("/telegram") ?? false;
    const [installEvent, setInstallEvent] =
        useState<BeforeInstallPromptEvent | null>(null);
    const [showBanner, setShowBanner] = useState(false);
    const [showIOSGuide, setShowIOSGuide] = useState(false);
    const [iosBanner, setIOSBanner] = useState(false);

    useEffect(() => {
        if (inTelegram || isStandalone() || isDismissed()) return;
        const loggedIn = !!Cookies.get("token");
        if (!loggedIn) return;

        if (isIOS()) {
            // Delay so the banner doesn't flash the moment the page opens.
            const timer = setTimeout(() => setIOSBanner(true), 3000);
            return () => clearTimeout(timer);
        }

        const onBeforeInstallPrompt = (e: Event) => {
            e.preventDefault();
            setInstallEvent(e as BeforeInstallPromptEvent);
            setShowBanner(true);
        };
        window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
        return () =>
            window.removeEventListener(
                "beforeinstallprompt",
                onBeforeInstallPrompt,
            );
    }, []);

    const dismiss = () => {
        try {
            localStorage.setItem(DISMISS_KEY, String(Date.now()));
        } catch {
            // localStorage unavailable — banner just reappears next visit
        }
        setShowBanner(false);
        setIOSBanner(false);
    };

    const install = async () => {
        if (!installEvent) return;
        setShowBanner(false);
        await installEvent.prompt();
        const choice = await installEvent.userChoice;
        if (choice.outcome === "dismissed") {
            dismiss();
        }
        setInstallEvent(null);
    };

    if (!showBanner && !iosBanner) return null;

    return (
        <>
            <div className="fixed inset-x-4 bottom-4 z-50 mx-auto flex max-w-md items-center gap-3 rounded-lg border bg-background p-4 shadow-lg">
                <Download className="h-6 w-6 shrink-0 text-blue-600" />
                <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{t("pwa.install.title")}</p>
                    <p className="text-xs text-muted-foreground">
                        {t("pwa.install.message")}
                    </p>
                </div>
                <Button
                    size="sm"
                    onClick={iosBanner ? () => setShowIOSGuide(true) : install}
                >
                    {t("pwa.install.action")}
                </Button>
                <button
                    type="button"
                    aria-label={t("pwa.install.dismiss")}
                    onClick={dismiss}
                    className="shrink-0 text-muted-foreground hover:text-foreground"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            <Dialog open={showIOSGuide} onOpenChange={setShowIOSGuide}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t("pwa.install.ios_title")}</DialogTitle>
                        <DialogDescription>
                            {t("pwa.install.ios_intro")}
                        </DialogDescription>
                    </DialogHeader>
                    <ol className="space-y-3 text-sm">
                        <li className="flex items-center gap-3">
                            <Share className="h-5 w-5 shrink-0 text-blue-600" />
                            <span>{t("pwa.install.ios_step1")}</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <SquarePlus className="h-5 w-5 shrink-0 text-blue-600" />
                            <span>{t("pwa.install.ios_step2")}</span>
                        </li>
                    </ol>
                </DialogContent>
            </Dialog>
        </>
    );
}
