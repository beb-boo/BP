"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

function VerifyContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { t } = useLanguage();

    const [email, setEmail] = useState("");
    const [otp, setOtp] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const emailParam = searchParams.get("email");
        if (emailParam) {
            setEmail(emailParam);
        } else {
            // If no email in params, redirect back to login or register
            toast.error("Email not found. Please register again.");
            router.push("/auth/register");
        }
    }, [searchParams, router]);

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!otp || otp.length !== 4) {
            toast.error(t('auth.verify_failed')); // Reuse generic fail or add specific
            return;
        }

        setIsLoading(true);

        try {
            await api.post("/auth/verify-email", {
                email: email,
                otp_code: otp,
                purpose: "email_verification"
            });

            toast.success(t('auth.verify_success'));
            router.push("/auth/login");

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || t('auth.verify_failed');
            toast.error(msg);
        } finally {
            setIsLoading(false);
        }
    };

    const handleResend = async () => {
        // Implement resend logic if needed (call /request-otp)
        toast.info("Resend feature coming soon");
    };

    return (
        <Card className="w-full max-w-md shadow-lg my-8">
            <CardHeader className="space-y-1 items-center">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mb-2">
                    <Mail className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <CardTitle className="text-2xl font-bold text-center">{t('auth.verify_email_title')}</CardTitle>
                <CardDescription className="text-center">
                    {t('auth.verify_email_desc')} <br />
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{email}</span>
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleVerify} className="space-y-4">
                    <div className="space-y-2">
                        <Input
                            className="text-center text-2xl tracking-widest"
                            placeholder="0000"
                            maxLength={4}
                            value={otp}
                            onChange={(e) => setOtp(e.target.value.replace(/[^0-9]/g, ''))}
                        />
                    </div>
                    <Button className="w-full" type="submit" disabled={isLoading || otp.length !== 4}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {t('auth.verify_btn')}
                    </Button>
                </form>
            </CardContent>
            <CardFooter className="flex justify-center">
                <Button variant="link" onClick={handleResend} className="text-sm text-slate-500">
                    {t('auth.resend_otp')}
                </Button>
            </CardFooter>
        </Card>
    );
}

export default function VerifyOtpPage() {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 p-4 relative">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>
            <Suspense fallback={<Loader2 className="h-8 w-8 animate-spin text-primary" />}>
                <VerifyContent />
            </Suspense>
        </div>
    );
}
