
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
    const router = useRouter();
    const { t } = useLanguage();
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault();
        setIsLoading(true);

        try {
            // Determine if email or phone (simple check: contains @ is email)
            const isEmail = email.includes("@");

            const payload = {
                email: isEmail ? email : undefined,
                phone_number: !isEmail ? email : undefined,
                password: password,
            };

            const res = await api.post("/auth/login", payload);

            const { access_token, user } = res.data.data;

            // Save token
            Cookies.set("token", access_token, { expires: 7 }); // 7 days
            Cookies.set("user", JSON.stringify(user), { expires: 7 });

            toast.success(t('auth.login_success'));
            router.push("/dashboard");
            router.refresh();

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || t('common.error');
            toast.error(msg);
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 p-4 relative">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>

            <Card className="w-full max-w-md shadow-lg">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">{t('auth.login_title')}</CardTitle>
                    <CardDescription className="text-center">
                        {t('auth.login_desc')}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={onSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">{t('auth.email_or_phone')}</Label>
                            <Input
                                id="email"
                                placeholder={t('auth.email_placeholder')}
                                type="text"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                disabled={isLoading}
                            />
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="password">{t('settings.password_title')}</Label>
                                <Link
                                    href="/auth/forgot-password"
                                    className="text-sm text-blue-600 hover:text-blue-500"
                                >
                                    {t('auth.forgot_password')}
                                </Link>
                            </div>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                disabled={isLoading}
                            />
                        </div>
                        <Button className="w-full" type="submit" disabled={isLoading}>
                            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {t('auth.sign_in')}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="flex justify-center">
                    <div className="text-sm text-slate-500">
                        {t('auth.dont_have_account')}{" "}
                        <Link href="/auth/register" className="font-semibold text-blue-600 hover:text-blue-500">
                            {t('auth.sign_up')}
                        </Link>
                    </div>
                </CardFooter>
            </Card>
        </div>
    );
}
