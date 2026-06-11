"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, BellOff, Loader2, Plus, Send, X } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { getApiErrorMessage, type ApiResponse } from "@/lib/api-helpers";
import {
    getSubscriptionState,
    sendTestNotification,
    subscribeToPush,
    unsubscribeFromPush,
    type PushState,
} from "@/lib/pwa/pushSubscription";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLanguage } from "@/contexts/LanguageContext";

interface NotificationPreferences {
    channels: string[] | null;
    show_details_in_push: boolean;
    reminder_enabled: boolean;
    reminder_times: string[];
}

const MAX_REMINDER_TIMES = 6;

export default function PushNotificationSettings() {
    const { t } = useLanguage();
    const [pushState, setPushState] = useState<PushState>("unsupported");
    const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
    const [busy, setBusy] = useState(false);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        getSubscriptionState().then(setPushState);
        api.get<ApiResponse<{ preferences: NotificationPreferences }>>(
            "/users/me/notification-preferences",
        )
            .then((res) => setPrefs(res.data.data.preferences))
            .catch(() => setPrefs(null));
    }, []);

    const patchPrefs = useCallback(
        async (patch: Partial<NotificationPreferences>) => {
            try {
                const res = await api.patch<
                    ApiResponse<{ preferences: NotificationPreferences }>
                >("/users/me/notification-preferences", patch);
                setPrefs(res.data.data.preferences);
            } catch (error) {
                toast.error(getApiErrorMessage(error, t("common.error")));
            }
        },
        [t],
    );

    const handleToggle = async () => {
        setBusy(true);
        try {
            if (pushState === "subscribed") {
                await unsubscribeFromPush();
                toast.success(t("pwa.push.disabled_toast"));
            } else {
                await subscribeToPush();
                toast.success(t("pwa.push.enabled_toast"));
            }
            setPushState(await getSubscriptionState());
        } catch (error) {
            if (error instanceof Error && error.message === "permission_denied") {
                setPushState("denied");
            } else {
                toast.error(getApiErrorMessage(error, t("pwa.push.subscribe_failed")));
            }
        } finally {
            setBusy(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        try {
            const delivered = await sendTestNotification();
            if (delivered) {
                toast.success(t("pwa.push.test_sent"));
            } else {
                toast.error(t("pwa.push.test_failed"));
            }
        } catch (error) {
            toast.error(getApiErrorMessage(error, t("pwa.push.test_failed")));
        } finally {
            setTesting(false);
        }
    };

    const updateReminderTime = (index: number, value: string) => {
        if (!prefs) return;
        const times = [...prefs.reminder_times];
        times[index] = value;
        setPrefs({ ...prefs, reminder_times: times });
    };

    const commitReminderTimes = () => {
        if (!prefs) return;
        const valid = prefs.reminder_times.filter((v) =>
            /^([01]\d|2[0-3]):[0-5]\d$/.test(v),
        );
        patchPrefs({ reminder_times: valid });
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{t("pwa.push.title")}</CardTitle>
                <CardDescription>{t("pwa.push.desc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {pushState === "unsupported" && (
                    <p className="text-sm text-muted-foreground">
                        {t("pwa.push.unsupported")}
                    </p>
                )}

                {pushState === "denied" && (
                    <p className="text-sm text-amber-600">
                        {t("pwa.push.permission_denied")}
                    </p>
                )}

                {(pushState === "subscribed" || pushState === "unsubscribed") && (
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2">
                            {pushState === "subscribed" ? (
                                <Bell className="h-5 w-5 text-blue-600" />
                            ) : (
                                <BellOff className="h-5 w-5 text-muted-foreground" />
                            )}
                            <span className="text-sm font-medium">
                                {pushState === "subscribed"
                                    ? t("pwa.push.status_on")
                                    : t("pwa.push.status_off")}
                            </span>
                        </div>
                        <Button onClick={handleToggle} disabled={busy} variant={pushState === "subscribed" ? "outline" : "default"}>
                            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {pushState === "subscribed"
                                ? t("pwa.push.disable")
                                : t("pwa.push.enable")}
                        </Button>
                    </div>
                )}

                {pushState === "subscribed" && prefs && (
                    <>
                        {/* D4: lock-screen detail opt-in */}
                        <div className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                id="show-details"
                                className="mt-1 h-4 w-4"
                                checked={prefs.show_details_in_push}
                                onChange={(e) =>
                                    patchPrefs({ show_details_in_push: e.target.checked })
                                }
                            />
                            <div>
                                <Label htmlFor="show-details">
                                    {t("pwa.push.show_details")}
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    {t("pwa.push.show_details_desc")}
                                </p>
                            </div>
                        </div>

                        <Button
                            variant="outline"
                            onClick={handleTest}
                            disabled={testing}
                        >
                            {testing ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="mr-2 h-4 w-4" />
                            )}
                            {t("pwa.push.test")}
                        </Button>
                    </>
                )}

                {prefs && (
                    <div className="space-y-3 border-t pt-4">
                        <div className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                id="reminder-enabled"
                                className="mt-1 h-4 w-4"
                                checked={prefs.reminder_enabled}
                                onChange={(e) =>
                                    patchPrefs({ reminder_enabled: e.target.checked })
                                }
                            />
                            <div>
                                <Label htmlFor="reminder-enabled">
                                    {t("pwa.push.reminder")}
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    {t("pwa.push.reminder_desc")}
                                </p>
                            </div>
                        </div>

                        {prefs.reminder_enabled && (
                            <div className="space-y-2 pl-7">
                                {prefs.reminder_times.map((time, i) => (
                                    <div key={i} className="flex items-center gap-2">
                                        <Input
                                            type="time"
                                            value={time}
                                            className="w-32"
                                            onChange={(e) =>
                                                updateReminderTime(i, e.target.value)
                                            }
                                            onBlur={commitReminderTimes}
                                        />
                                        <button
                                            type="button"
                                            aria-label={t("common.delete")}
                                            className="text-muted-foreground hover:text-foreground"
                                            onClick={() =>
                                                patchPrefs({
                                                    reminder_times:
                                                        prefs.reminder_times.filter(
                                                            (_, j) => j !== i,
                                                        ),
                                                })
                                            }
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                ))}
                                {prefs.reminder_times.length < MAX_REMINDER_TIMES && (
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={() =>
                                            patchPrefs({
                                                reminder_times: [
                                                    ...prefs.reminder_times,
                                                    "08:00",
                                                ],
                                            })
                                        }
                                    >
                                        <Plus className="mr-1 h-4 w-4" />
                                        {t("pwa.push.reminder_add_time")}
                                    </Button>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
