"use client";

import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";

export default function OfflinePage() {
    const { t } = useLanguage();

    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
            <WifiOff className="h-16 w-16 text-muted-foreground" />
            <h1 className="text-2xl font-semibold">{t("pwa.offline.title")}</h1>
            <p className="text-muted-foreground">{t("pwa.offline.message")}</p>
            <Button onClick={() => window.location.reload()}>
                {t("pwa.offline.retry")}
            </Button>
        </div>
    );
}
