"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function ForgotPasswordPage() {
    const router = useRouter();
    const { t } = useLanguage();
    const [isLoading, setIsLoading] = useState(false);

    // Step 1: Request OTP
    // Step 2: Reset Password
    const [step, setStep] = useState(1);

    const [emailOrPhone, setEmailOrPhone] = useState("");
    const [otp, setOtp] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    // Detect type (email or phone)
    const isEmail = (input: string) => input.includes("@");

    async function onRequestOtp(e: React.FormEvent) {
        e.preventDefault();
        setIsLoading(true);

        try {
            const isMail = isEmail(emailOrPhone);
            const payload = {
                email: isMail ? emailOrPhone : undefined,
                phone_number: !isMail ? emailOrPhone : undefined,
                purpose: "password_reset"
            };

            await api.post("/auth/request-otp", payload);

            toast.success("OTP sent! Please check your " + (isMail ? "email" : "phone"));
            setStep(2);

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || "Failed to send OTP";
            toast.error(msg);
        } finally {
            setIsLoading(false);
        }
    }

    async function onResetPassword(e: React.FormEvent) {
        e.preventDefault();

        if (newPassword !== confirmPassword) {
            toast.error(t('settings.passwords_mismatch', 'Passwords do not match'));
            return;
        }

        if (newPassword.length < 8) {
            toast.error(t('auth.password_min_length', 'Password must be at least 8 characters'));
            return;
        }

        setIsLoading(true);

        try {
            const isMail = isEmail(emailOrPhone);
            const payload = {
                email: isMail ? emailOrPhone : undefined,
                phone_number: !isMail ? emailOrPhone : undefined,
                otp_code: otp,
                new_password: newPassword,
                confirm_new_password: confirmPassword
            };

            await api.post("/auth/reset-password", payload);

            toast.success("Password reset successfully! Please login.");
            router.push("/auth/login");

        } catch (error: any) {
            console.error(error);
            let msg = error.response?.data?.detail || "Failed to reset password";

            // Handle validation errors (422) which return array of objects
            if (Array.isArray(msg)) {
                msg = msg.map((err: any) => err.msg).join(", ");
            }

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
                    <CardTitle className="text-2xl font-bold text-center">
                        {step === 1 ? "Forgot Password" : "Reset Password"}
                    </CardTitle>
                    <CardDescription className="text-center">
                        {step === 1
                            ? "Enter your email or phone number to reset your password"
                            : "Enter the OTP sent to you and your new password"}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {step === 1 ? (
                        <form onSubmit={onRequestOtp} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="emailOrPhone">{t('auth.email_or_phone', 'Email or Phone')}</Label>
                                <Input
                                    id="emailOrPhone"
                                    placeholder={t('auth.email_placeholder', 'name@example.com or 0812345678')}
                                    type="text"
                                    value={emailOrPhone}
                                    onChange={(e) => setEmailOrPhone(e.target.value)}
                                    required
                                    disabled={isLoading}
                                    autoFocus
                                />
                            </div>
                            <Button className="w-full" type="submit" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {t('auth.request_otp', 'Request OTP')}
                            </Button>
                        </form>
                    ) : (
                        <form onSubmit={onResetPassword} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="otp">OTP Code</Label>
                                <Input
                                    id="otp"
                                    placeholder="Enter 4-digit code"
                                    type="text"
                                    maxLength={4}
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value)}
                                    required
                                    disabled={isLoading}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="newpass">{t('settings.new_password', 'New Password')}</Label>
                                <Input
                                    id="newpass"
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    required
                                    disabled={isLoading}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="confirmpass">{t('settings.confirm_new_password', 'Confirm New Password')}</Label>
                                <Input
                                    id="confirmpass"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    disabled={isLoading}
                                />
                            </div>
                            <Button className="w-full" type="submit" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {t('common.save', 'Save Password')}
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                className="w-full"
                                onClick={() => setStep(1)}
                                disabled={isLoading}
                            >
                                <ArrowLeft className="mr-2 h-4 w-4" /> Back
                            </Button>
                        </form>
                    )}
                </CardContent>
                <CardFooter className="flex justify-center">
                    <Link href="/auth/login" className="flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Login
                    </Link>
                </CardFooter>
            </Card>
        </div>
    );
}
