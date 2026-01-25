"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { Lock, Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useLanguage } from "@/contexts/LanguageContext";
import { TIMEZONE_CHOICES } from "@/lib/date-utils";

export default function SettingsPage() {
    const { t, language } = useLanguage();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState<any>(null);
    const [activeTab, setActiveTab] = useState("profile");

    // Profile Form State
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [phone, setPhone] = useState("");
    const [citizenId, setCitizenId] = useState("");
    const [medicalLicense, setMedicalLicense] = useState("");

    // Extended Profile Fields
    const [dob, setDob] = useState("");
    const [gender, setGender] = useState("");
    const [bloodType, setBloodType] = useState("");
    const [height, setHeight] = useState("");
    const [weight, setWeight] = useState("");
    const [timezone, setTimezone] = useState("Asia/Bangkok");

    const [isSaving, setIsSaving] = useState(false);

    // Password Form State
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isChangingPwd, setIsChangingPwd] = useState(false);
    const [isGeneratingLink, setIsGeneratingLink] = useState(false);

    // Security Confirmation
    // Security Confirmation
    const [confirmCurrentPassword, setConfirmCurrentPassword] = useState("");
    const [otpCode, setOtpCode] = useState("");
    const [otpTimer, setOtpTimer] = useState(0);

    // Email Verification State
    const [isVerifyingEmail, setIsVerifyingEmail] = useState(false);
    const [emailOtp, setEmailOtp] = useState("");
    const [emailOtpTimer, setEmailOtpTimer] = useState(0);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const res = await api.get("/users/me");
                const profile = res.data.data.profile;
                setUser(profile);

                // Init fields
                setFullName(profile.full_name || "");
                setEmail(profile.email || "");
                setPhone(profile.phone_number || "");
                setCitizenId(profile.citizen_id || "");
                setMedicalLicense(profile.medical_license || "");

                // Parse date for input (YYYY-MM-DD) - Use Local Time to avoid Timezone shift
                if (profile.date_of_birth) {
                    const d = new Date(profile.date_of_birth);
                    const localIso = d.getFullYear() + '-' +
                        String(d.getMonth() + 1).padStart(2, '0') + '-' +
                        String(d.getDate()).padStart(2, '0');
                    setDob(localIso);
                }
                setGender(profile.gender || "");
                setBloodType(profile.blood_type || "");
                setHeight(profile.height ? String(profile.height) : "");
                setWeight(profile.weight ? String(profile.weight) : "");
                setTimezone(profile.timezone || "Asia/Bangkok");

            } catch (error) {
                console.error("Failed to fetch profile", error);
                router.push("/auth/login");
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, [router]);

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            const payload: any = {
                full_name: fullName,
                email: email || "", // Send empty string if cleared
                phone_number: phone || "",
                citizen_id: citizenId || "",
                // Send raw YYYY-MM-DD string, let backend parse it
                date_of_birth: dob || null,
                gender: gender || null,
                blood_type: bloodType || null,
                height: height ? parseFloat(height) : null,
                weight: weight ? parseFloat(weight) : null,
                timezone: timezone || null,

                current_password: confirmCurrentPassword || null,
                otp_code: otpCode || null
            };

            // Only send medical license if user is a doctor
            if (user.role === 'doctor') {
                payload.medical_license = medicalLicense;
            }

            await api.put("/users/me", payload);
            toast.success(t('common.success', "Profile updated successfully"));

            // Refresh cookie if needed (optional, but good for consistency)
            const cookieUser = JSON.parse(Cookies.get("user") || "{}");
            Cookies.set("user", JSON.stringify({ ...cookieUser, full_name: fullName }));
            router.refresh();

        } catch (error: any) {
            toast.error(error.response?.data?.detail || t('common.error'));
            console.error(error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleRequestOtp = async () => {
        if (!user?.email) return;
        try {
            await api.post("/auth/request-otp", {
                email: user.email,
                purpose: "update_profile"
            });
            toast.success("OTP sent to your email!");
            setOtpTimer(300); // 5 minutes
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to send OTP");
        }
    };

    // Email Verification Logic
    const handleStartEmailVerification = async () => {
        if (!user?.email) return;
        setIsVerifyingEmail(true);
        try {
            await api.post("/auth/request-otp", {
                email: user.email,
                purpose: "email_verification"
            });
            toast.success("Verification OTP sent to your email!");
            setEmailOtpTimer(300); // 5 minutes
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to send OTP");
            setIsVerifyingEmail(false);
        }
    };

    const handleConfirmEmailVerification = async () => {
        try {
            await api.post("/auth/verify-contact", {
                email: user.email,
                otp_code: emailOtp,
                purpose: "email_verification"
            });
            toast.success("Email verified successfully!");
            setIsVerifyingEmail(false);
            setUser({ ...user, is_email_verified: true });
            router.refresh();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to verify OTP");
        }
    };

    // Timer Effects
    useEffect(() => {
        if (otpTimer > 0) {
            const timer = setTimeout(() => setOtpTimer(otpTimer - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [otpTimer]);

    useEffect(() => {
        if (emailOtpTimer > 0) {
            const timer = setTimeout(() => setEmailOtpTimer(emailOtpTimer - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [emailOtpTimer]);

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            toast.error(t('settings.passwords_mismatch'));
            return;
        }

        if (newPassword.length < 8) {
            toast.error(t('auth.password_min_length', 'Password must be at least 8 characters'));
            return;
        }

        setIsChangingPwd(true);
        try {
            await api.post("/auth/change-password", {
                current_password: currentPassword,
                new_password: newPassword
            });
            toast.success(t('settings.password_changed'));

            // Clear fields
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
        } catch (error: any) {
            let msg = error.response?.data?.detail || t('common.error');
            // Handle validation errors (422)
            if (Array.isArray(msg)) {
                msg = msg.map((err: any) => err.msg).join(", ");
            }
            toast.error(msg);
        } finally {
            setIsChangingPwd(false);
        }
    };

    const handleConnectTelegram = async () => {
        setIsGeneratingLink(true);
        try {
            const res = await api.post("/auth/telegram/generate-link");
            const link = res.data.data.link;
            window.open(link, '_blank');
            toast.success("Opening Telegram to verify...");
        } catch (error: any) {
            toast.error("Failed to generate link");
        } finally {
            setIsGeneratingLink(false);
        }
    };

    if (loading) {
        return <div className="p-8 flex items-center justify-center">{t('common.loading')}</div>;
    }

    return (
        <div className="p-6 md:p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard')}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t('settings.title')}</h1>
                    <p className="text-slate-500">{t('settings.desc')}</p>
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                <TabsList>
                    <TabsTrigger value="profile">{t('settings.profile')}</TabsTrigger>
                    <TabsTrigger value="security">{t('settings.security')}</TabsTrigger>
                </TabsList>

                <TabsContent value="profile">
                    <Card>
                        <CardHeader>
                            <CardTitle>{t('settings.profile_info')}</CardTitle>
                            <CardDescription>
                                {t('settings.profile_desc')}
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleUpdateProfile}>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="fullName">{t('settings.full_name')}</Label>
                                        <Input
                                            id="fullName"
                                            value={fullName}
                                            onChange={e => setFullName(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="role">{t('settings.role')}</Label>
                                        <Input id="role" value={user?.role} disabled className="bg-slate-100" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="email">{t('settings.email')}</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            value={email}
                                            onChange={e => setEmail(e.target.value)}
                                        />

                                        {/* Email Verification UI */}
                                        {user?.email && !user?.is_email_verified && email === user?.email && (
                                            <div className="mt-2 text-sm text-amber-600 bg-amber-50 p-2 rounded-md border border-amber-200">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <AlertCircle className="w-4 h-4" />
                                                    <span>{t('settings.email_not_verified')}</span>
                                                    {!isVerifyingEmail && (
                                                        <Button
                                                            variant="link"
                                                            className="h-auto p-0 text-amber-700 font-bold underline ml-auto"
                                                            type="button"
                                                            onClick={handleStartEmailVerification}
                                                        >
                                                            {t('settings.verify_now')}
                                                        </Button>
                                                    )}
                                                </div>

                                                {isVerifyingEmail && (
                                                    <div className="flex gap-2 animate-in fade-in slide-in-from-top-1">
                                                        <Input
                                                            placeholder="OTP"
                                                            value={emailOtp}
                                                            onChange={e => setEmailOtp(e.target.value)}
                                                            className="h-8 bg-white"
                                                            maxLength={4}
                                                        />
                                                        <Button type="button" size="sm" onClick={handleConfirmEmailVerification}>
                                                            {t('common.confirm')}
                                                        </Button>
                                                        <Button
                                                            type="button"
                                                            size="sm"
                                                            variant="ghost"
                                                            disabled={emailOtpTimer > 0}
                                                            onClick={handleStartEmailVerification}
                                                        >
                                                            {emailOtpTimer > 0 ? `${emailOtpTimer}s` : t('common.resend', 'Resend')}
                                                        </Button>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        {user?.is_email_verified && (
                                            <div className="mt-1 text-xs text-green-600 flex items-center gap-1">
                                                ✓ {t('settings.verified')}
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="phone">{t('settings.phone')}</Label>
                                        <Input
                                            id="phone"
                                            value={phone}
                                            onChange={e => setPhone(e.target.value)}
                                            placeholder="0812345678"
                                        />
                                        {phone !== user?.phone_number && (
                                            <div className="text-xs text-amber-600 mt-1">
                                                {t('settings.changing_phone_warning')}
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-2">
                                            <Label htmlFor="citizenId">{t('settings.citizen_id')}</Label>
                                            <Lock className="w-3 h-3 text-slate-400" />
                                        </div>
                                        <Input
                                            id="citizenId"
                                            value={citizenId}
                                            onChange={e => setCitizenId(e.target.value)}
                                            placeholder={t('settings.encrypted_storage')}
                                        />
                                        <p className="text-xs text-slate-500">{t('settings.visible_to_auth')}</p>
                                    </div>

                                    {user?.role === 'doctor' && (
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <Label htmlFor="license">{t('settings.medical_license')}</Label>
                                                <Lock className="w-3 h-3 text-slate-400" />
                                            </div>
                                            <Input
                                                id="license"
                                                value={medicalLicense}
                                                onChange={e => setMedicalLicense(e.target.value)}
                                            />
                                        </div>
                                    )}

                                    <div className="space-y-2">
                                        <Label htmlFor="dob">{t('settings.dob')}</Label>
                                        <Input
                                            id="dob"
                                            type="date"
                                            value={dob}
                                            onChange={e => setDob(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="gender">{t('settings.gender')}</Label>
                                        <select
                                            id="gender"
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                            value={gender}
                                            onChange={e => setGender(e.target.value)}
                                        >
                                            <option value="">{t('settings.select_gender')}</option>
                                            <option value="male">{t('settings.male')}</option>
                                            <option value="female">{t('settings.female')}</option>
                                            <option value="other">{t('settings.other')}</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="blood">{t('settings.blood_type')}</Label>
                                        <select
                                            id="blood"
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                            value={bloodType}
                                            onChange={e => setBloodType(e.target.value)}
                                        >
                                            <option value="">{t('settings.select_blood')}</option>
                                            <option value="A">A</option>
                                            <option value="B">B</option>
                                            <option value="AB">AB</option>
                                            <option value="O">O</option>
                                        </select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="height">{t('settings.height')}</Label>
                                            <Input
                                                id="height"
                                                type="number"
                                                value={height}
                                                onChange={e => setHeight(e.target.value)}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="weight">{t('settings.weight')}</Label>
                                            <Input
                                                id="weight"
                                                type="number"
                                                value={weight}
                                                onChange={e => setWeight(e.target.value)}
                                            />
                                        </div>
                                    </div>

                                    {/* Timezone Selection */}
                                    <div className="space-y-2 md:col-span-2">
                                        <Label htmlFor="timezone">{t('settings.timezone')}</Label>
                                        <select
                                            id="timezone"
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                            value={timezone}
                                            onChange={e => setTimezone(e.target.value)}
                                        >
                                            {TIMEZONE_CHOICES.map((tz) => (
                                                <option key={tz.value} value={tz.value}>
                                                    {language === "th" ? tz.label.th : tz.label.en}
                                                </option>
                                            ))}
                                        </select>
                                        <p className="text-xs text-slate-500">{t('settings.timezone_desc')}</p>
                                    </div>
                                </div>

                                {/* Security Prompt for Sensitive Changes */}
                                {/* Normalize comparison to handle null vs empty string */}
                                {((email || "") !== (user?.email || "") || (phone || "") !== (user?.phone_number || "")) && (
                                    <div className="space-y-4 mt-4">
                                        <Alert className="bg-amber-50 border-amber-200">
                                            <Lock className="h-4 w-4" />
                                            <AlertTitle>{t('settings.security_verification')}</AlertTitle>
                                            <AlertDescription className="space-y-3">
                                                <p>{t('settings.sensitive_change_msg')}</p>
                                                <Input
                                                    type="password"
                                                    placeholder={t('settings.enter_req_pwd')}
                                                    value={confirmCurrentPassword}
                                                    onChange={(e) => setConfirmCurrentPassword(e.target.value)}
                                                    className="bg-white"
                                                />
                                            </AlertDescription>
                                        </Alert>

                                        {/* OTP Requirement for Phone Change if User has Email */}
                                        {phone !== user?.phone_number && user?.email && (
                                            <Alert className="bg-blue-50 border-blue-200">
                                                <AlertCircle className="h-4 w-4" />
                                                <AlertTitle>{t('settings.two_factor_auth')}</AlertTitle>
                                                <AlertDescription className="space-y-3">
                                                    <p>{t('settings.otp_change_phone')}: <strong>{user.email}</strong></p>
                                                    <div className="flex gap-2">
                                                        <Input
                                                            placeholder="Enter 4-digit OTP"
                                                            value={otpCode}
                                                            onChange={e => setOtpCode(e.target.value)}
                                                            maxLength={4}
                                                            className="bg-white"
                                                        />
                                                        <Button
                                                            type="button"
                                                            variant="outline"
                                                            onClick={handleRequestOtp}
                                                            disabled={otpTimer > 0}
                                                        >
                                                            {otpTimer > 0 ? `${t('settings.resend_in')} ${otpTimer}s` : t('settings.request_otp')}
                                                        </Button>
                                                    </div>
                                                </AlertDescription>
                                            </Alert>
                                        )}
                                    </div>
                                )}


                            </CardContent>
                            <CardFooter>
                                <Button type="submit" disabled={isSaving}>
                                    {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    {t('settings.save_changes')}
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>
                </TabsContent>

                <TabsContent value="security">
                    <Card>
                        <CardHeader>
                            <CardTitle>{t('settings.password_title')}</CardTitle>
                            <CardDescription>
                                {t('settings.password_desc')}
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleChangePassword}>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="current">{t('settings.current_password')}</Label>
                                    <Input
                                        id="current"
                                        type="password"
                                        value={currentPassword}
                                        onChange={e => setCurrentPassword(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="new">{t('settings.new_password')}</Label>
                                    <Input
                                        id="new"
                                        type="password"
                                        value={newPassword}
                                        onChange={e => setNewPassword(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="confirm">{t('settings.confirm_new_password')}</Label>
                                    <Input
                                        id="confirm"
                                        type="password"
                                        value={confirmPassword}
                                        onChange={e => setConfirmPassword(e.target.value)}
                                        required
                                    />
                                </div>
                            </CardContent>
                            <CardFooter>
                                <Button type="submit" disabled={isChangingPwd}>
                                    {isChangingPwd && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    {t('settings.change_password')}
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>

                    <div className="mt-4">
                        <Alert variant="default" className={user?.is_email_verified ? "bg-green-50 border-green-200" : "bg-blue-50 border-blue-200"}>
                            <AlertCircle className={user?.is_email_verified ? "h-4 w-4 text-green-600" : "h-4 w-4 text-blue-600"} />
                            <AlertTitle className={user?.is_email_verified ? "text-green-800" : "text-blue-800"}>
                                {user?.is_email_verified ? t('settings.otp_active') : t('settings.enable_otp')}
                            </AlertTitle>
                            <AlertDescription className={user?.is_email_verified ? "text-green-700" : "text-blue-700"}>
                                {user?.is_email_verified
                                    ? t('settings.otp_active_desc')
                                    : t('settings.otp_inactive_desc')}
                                <br />
                                {!user?.is_email_verified && (
                                    <Button
                                        variant="link"
                                        className="p-0 h-auto font-semibold text-blue-800 underline mt-1"
                                        onClick={() => setActiveTab("profile")}
                                    >
                                        {t('settings.go_to_verify')}
                                    </Button>
                                )}
                            </AlertDescription>
                        </Alert>
                    </div>

                    <div className="mt-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>{t('settings.telegram_integration')}</CardTitle>
                                <CardDescription>
                                    {t('settings.telegram_desc')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {user?.telegram_id ? (
                                    <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-md border border-green-200">
                                        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                                        <span className="font-medium">{t('settings.connected_telegram')}</span>
                                        <span className="text-xs opacity-75">(ID: {user.telegram_id})</span>
                                    </div>
                                ) : (
                                    <Button onClick={handleConnectTelegram} disabled={isGeneratingLink}>
                                        {isGeneratingLink && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        {t('settings.connect_telegram')}
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>
        </div >
    );
}
