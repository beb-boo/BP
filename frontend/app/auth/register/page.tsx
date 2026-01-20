
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

export default function RegisterPage() {
    const router = useRouter();
    const { t } = useLanguage();
    const [isLoading, setIsLoading] = useState(false);
    const [role, setRole] = useState("patient");

    const [formData, setFormData] = useState({
        email: "",
        phone_number: "",
        password: "",
        full_name: "",
        citizen_id: "",
        medical_license: "",
        date_of_birth: "",
        gender: "male",
        height: "",
        weight: "",
        blood_type: "A"
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.id]: e.target.value });
    };

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault();
        setIsLoading(true);

        try {
            // Basic validation
            // Basic validation
            if (!formData.email && !formData.phone_number) {
                throw new Error("Email or Phone Number is required");
            }

            // Validate Email Format
            if (formData.email) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(formData.email)) {
                    throw new Error(t('auth.invalid_email') || "Invalid email format");
                }
            }

            // Validate Password Length
            if (formData.password.length < 8) {
                throw new Error(t('auth.password_min_length') || "Password must be at least 8 characters");
            }

            const payload = {
                ...formData,
                role: role,
                height: formData.height ? parseFloat(formData.height) : undefined,
                weight: formData.weight ? parseFloat(formData.weight) : undefined
            };

            await api.post("/auth/register", payload);

            // Redirect to verify page with email
            const encodedEmail = encodeURIComponent(formData.email);
            toast.success(t('auth.reg_success')); // "Registration successful! Please login." -> Might want to update this text later or rely on next page context
            router.push(`/auth/verify-otp?email=${encodedEmail}`);

        } catch (error: any) {
            console.error(error);
            // Check for Axios response error first, then standard Error message, then fallback
            const msg = error.response?.data?.detail || error.message || t('common.error');
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

            <Card className="w-full max-w-2xl shadow-lg my-8">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">{t('auth.create_account')}</CardTitle>
                    <CardDescription className="text-center">
                        {t('auth.register_desc')}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={onSubmit} className="space-y-4">

                        {/* Role Selection */}
                        <div className="space-y-2">
                            <Label>{t('auth.i_am_a')}</Label>
                            <div className="flex gap-4">
                                <Button
                                    type="button"
                                    variant={role === "patient" ? "default" : "outline"}
                                    onClick={() => setRole("patient")}
                                    className="w-1/2"
                                >
                                    {t('auth.patient')}
                                </Button>
                                <Button
                                    type="button"
                                    variant={role === "doctor" ? "default" : "outline"}
                                    onClick={() => setRole("doctor")}
                                    className="w-1/2"
                                >
                                    {t('auth.doctor')}
                                </Button>
                            </div>
                        </div>

                        <Separator />

                        {/* Account Info */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">{t('settings.email')}</Label>
                                <Input id="email" type="email" value={formData.email} onChange={handleChange} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="phone_number">{t('settings.phone')}</Label>
                                <Input id="phone_number" value={formData.phone_number} onChange={handleChange} />
                            </div>
                            <div className="space-y-2 col-span-2">
                                <Label htmlFor="password">{t('settings.password_title')}</Label>
                                <Input id="password" type="password" value={formData.password} onChange={handleChange} required />
                            </div>
                        </div>

                        <Separator />

                        {/* Personal Info */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2 col-span-2">
                                <Label htmlFor="full_name">{t('settings.full_name')}</Label>
                                <Input id="full_name" value={formData.full_name} onChange={handleChange} required />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="citizen_id">{t('settings.citizen_id')}</Label>
                                <Input id="citizen_id" value={formData.citizen_id} onChange={handleChange} />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="date_of_birth">{t('settings.dob')}</Label>
                                <Input id="date_of_birth" type="date" value={formData.date_of_birth} onChange={handleChange} />
                            </div>

                            <div className="space-y-2">
                                <Label>{t('settings.gender')}</Label>
                                <Select onValueChange={(val) => setFormData({ ...formData, gender: val })} defaultValue={formData.gender}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={t('settings.select_gender')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="male">{t('settings.male')}</SelectItem>
                                        <SelectItem value="female">{t('settings.female')}</SelectItem>
                                        <SelectItem value="other">{t('settings.other')}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>{t('settings.blood_type')}</Label>
                                <Select onValueChange={(val) => setFormData({ ...formData, blood_type: val })} defaultValue={formData.blood_type}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={t('settings.select_blood')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {['A', 'B', 'AB', 'O'].map(t => (
                                            <SelectItem key={t} value={t}>{t}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="height">{t('settings.height')}</Label>
                                <Input id="height" type="number" value={formData.height} onChange={handleChange} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="weight">{t('settings.weight')}</Label>
                                <Input id="weight" type="number" value={formData.weight} onChange={handleChange} />
                            </div>
                        </div>

                        {role === "doctor" && (
                            <div className="space-y-2 border-l-4 border-blue-500 pl-4 bg-slate-50 p-2 rounded">
                                <Label htmlFor="medical_license">{t('settings.medical_license')}</Label>
                                <Input id="medical_license" value={formData.medical_license} onChange={handleChange} required />
                            </div>
                        )}

                        <div className="text-xs text-amber-600">
                            {t('auth.otp_note')}
                        </div>

                        <Button className="w-full" type="submit" disabled={isLoading}>
                            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {t('common.register')}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="flex justify-center">
                    <Link href="/auth/login" className="text-sm text-blue-600 hover:text-blue-500">
                        {t('auth.already_account')}
                    </Link>
                </CardFooter>
            </Card>
        </div>
    );
}
