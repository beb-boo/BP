"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { User, Lock, Save, Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function SettingsPage() {
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
    const [isOtpSent, setIsOtpSent] = useState(false);
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

                current_password: confirmCurrentPassword || null,
                otp_code: otpCode || null
            };

            // Only send medical license if user is a doctor
            if (user.role === 'doctor') {
                payload.medical_license = medicalLicense;
            }

            await api.put("/users/me", payload);
            toast.success("Profile updated successfully");

            // Refresh cookie if needed (optional, but good for consistency)
            const cookieUser = JSON.parse(Cookies.get("user") || "{}");
            Cookies.set("user", JSON.stringify({ ...cookieUser, full_name: fullName }));
            router.refresh();

        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to update profile");
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
            setIsOtpSent(true);
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
            toast.error("New passwords do not match");
            return;
        }

        setIsChangingPwd(true);
        try {
            await api.post("/auth/change-password", {
                current_password: currentPassword,
                new_password: newPassword
            });
            toast.success("Password changed successfully");

            // Clear fields
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to change password");
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
        return <div className="p-8 flex items-center justify-center">Loading settings...</div>;
    }

    return (
        <div className="p-6 md:p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard')}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                    <p className="text-slate-500">Manage your account settings and preferences.</p>
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                <TabsList>
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="security">Security</TabsTrigger>
                </TabsList>

                <TabsContent value="profile">
                    <Card>
                        <CardHeader>
                            <CardTitle>Profile Information</CardTitle>
                            <CardDescription>
                                Update your personal details. Sensitive ID fields are encrypted securely.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleUpdateProfile}>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="fullName">Full Name</Label>
                                        <Input
                                            id="fullName"
                                            value={fullName}
                                            onChange={e => setFullName(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="role">Role</Label>
                                        <Input id="role" value={user?.role} disabled className="bg-slate-100" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="email">Email</Label>
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
                                                    <span>Email not verified</span>
                                                    {!isVerifyingEmail && (
                                                        <Button
                                                            variant="link"
                                                            className="h-auto p-0 text-amber-700 font-bold underline ml-auto"
                                                            type="button"
                                                            onClick={handleStartEmailVerification}
                                                        >
                                                            Verify Now
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
                                                            Confirm
                                                        </Button>
                                                        <Button
                                                            type="button"
                                                            size="sm"
                                                            variant="ghost"
                                                            disabled={emailOtpTimer > 0}
                                                            onClick={handleStartEmailVerification}
                                                        >
                                                            {emailOtpTimer > 0 ? `${emailOtpTimer}s` : "Resend"}
                                                        </Button>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        {user?.is_email_verified && (
                                            <div className="mt-1 text-xs text-green-600 flex items-center gap-1">
                                                ✓ Verified
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="phone">Phone Number</Label>
                                        <Input
                                            id="phone"
                                            value={phone}
                                            onChange={e => setPhone(e.target.value)}
                                            placeholder="0812345678"
                                        />
                                        {phone !== user?.phone_number && (
                                            <div className="text-xs text-amber-600 mt-1">
                                                ⚠️ Changing phone number will unlink Telegram
                                            </div>
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-2">
                                            <Label htmlFor="citizenId">Citizen ID</Label>
                                            <Lock className="w-3 h-3 text-slate-400" />
                                        </div>
                                        <Input
                                            id="citizenId"
                                            value={citizenId}
                                            onChange={e => setCitizenId(e.target.value)}
                                            placeholder="Encrypted storage"
                                        />
                                        <p className="text-xs text-slate-500">Only visible to authorized personnel.</p>
                                    </div>

                                    {user?.role === 'doctor' && (
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <Label htmlFor="license">Medical License</Label>
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
                                        <Label htmlFor="dob">Date of Birth</Label>
                                        <Input
                                            id="dob"
                                            type="date"
                                            value={dob}
                                            onChange={e => setDob(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="gender">Gender</Label>
                                        <select
                                            id="gender"
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                            value={gender}
                                            onChange={e => setGender(e.target.value)}
                                        >
                                            <option value="">Select Gender</option>
                                            <option value="male">Male</option>
                                            <option value="female">Female</option>
                                            <option value="other">Other</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="blood">Blood Type</Label>
                                        <select
                                            id="blood"
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                            value={bloodType}
                                            onChange={e => setBloodType(e.target.value)}
                                        >
                                            <option value="">Select Blood Type</option>
                                            <option value="A">A</option>
                                            <option value="B">B</option>
                                            <option value="AB">AB</option>
                                            <option value="O">O</option>
                                        </select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="height">Height (cm)</Label>
                                            <Input
                                                id="height"
                                                type="number"
                                                value={height}
                                                onChange={e => setHeight(e.target.value)}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="weight">Weight (kg)</Label>
                                            <Input
                                                id="weight"
                                                type="number"
                                                value={weight}
                                                onChange={e => setWeight(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Security Prompt for Sensitive Changes */}
                                {(email !== user?.email || phone !== user?.phone_number) && (
                                    <div className="space-y-4 mt-4">
                                        <Alert className="bg-amber-50 border-amber-200">
                                            <Lock className="h-4 w-4" />
                                            <AlertTitle>Security Verification Required</AlertTitle>
                                            <AlertDescription className="space-y-3">
                                                <p>You are changing sensitive contact information. Please confirm your current password.</p>
                                                <Input
                                                    type="password"
                                                    placeholder="Enter Request Password"
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
                                                <AlertTitle>Two-Factor Authentication (OTP)</AlertTitle>
                                                <AlertDescription className="space-y-3">
                                                    <p>To change your phone number, please enter the OTP sent to your registered email: <strong>{user.email}</strong></p>
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
                                                            {otpTimer > 0 ? `Resend in ${otpTimer}s` : "Request OTP"}
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
                                    Save Changes
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>
                </TabsContent>

                <TabsContent value="security">
                    <Card>
                        <CardHeader>
                            <CardTitle>Password</CardTitle>
                            <CardDescription>
                                Change your password. Use a strong password to keep your account secure.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleChangePassword}>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="current">Current Password</Label>
                                    <Input
                                        id="current"
                                        type="password"
                                        value={currentPassword}
                                        onChange={e => setCurrentPassword(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="new">New Password</Label>
                                    <Input
                                        id="new"
                                        type="password"
                                        value={newPassword}
                                        onChange={e => setNewPassword(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="confirm">Confirm New Password</Label>
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
                                    Change Password
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>

                    <div className="mt-4">
                        <Alert variant="default" className={user?.is_email_verified ? "bg-green-50 border-green-200" : "bg-blue-50 border-blue-200"}>
                            <AlertCircle className={user?.is_email_verified ? "h-4 w-4 text-green-600" : "h-4 w-4 text-blue-600"} />
                            <AlertTitle className={user?.is_email_verified ? "text-green-800" : "text-blue-800"}>
                                {user?.is_email_verified ? "Two-Factor Authentication is Active (Email)" : "Enable Two-Factor Authentication"}
                            </AlertTitle>
                            <AlertDescription className={user?.is_email_verified ? "text-green-700" : "text-blue-700"}>
                                {user?.is_email_verified
                                    ? "Your account is protected. We will require an OTP from your verified email for sensitive profile changes (e.g. changing phone number)."
                                    : "To enable OTP protection for sensitive actions, please verify your email address."}
                                <br />
                                {!user?.is_email_verified && (
                                    <Button
                                        variant="link"
                                        className="p-0 h-auto font-semibold text-blue-800 underline mt-1"
                                        onClick={() => setActiveTab("profile")}
                                    >
                                        Go to Profile Verification
                                    </Button>
                                )}
                            </AlertDescription>
                        </Alert>
                    </div>

                    <div className="mt-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>Telegram Integration</CardTitle>
                                <CardDescription>
                                    Connect your Telegram account to receive notifications and manage BP logs via bot.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {user?.telegram_id ? (
                                    <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-md border border-green-200">
                                        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                                        <span className="font-medium">Connected with Telegram</span>
                                        <span className="text-xs opacity-75">(ID: {user.telegram_id})</span>
                                    </div>
                                ) : (
                                    <Button onClick={handleConnectTelegram} disabled={isGeneratingLink}>
                                        {isGeneratingLink && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Connect Telegram
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
