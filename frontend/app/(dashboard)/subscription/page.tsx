"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Crown, Check, Loader2, ArrowLeft, Clock, History } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { getApiErrorMessage, type ApiResponse } from "@/lib/api-helpers";
import type { PaymentAccount, Plan } from "@/lib/app-types";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface PaymentHistoryItem {
    id: number;
    plan_type: string;
    amount: number;
    status: string;
    trans_date: string | null;
    created_at: string;
    verified_at: string | null;
}

export default function SubscriptionPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [plans, setPlans] = useState<Plan[]>([]);
    const [paymentAccount, setPaymentAccount] = useState<PaymentAccount | null>(null);
    const [currentTier, setCurrentTier] = useState("free");
    const [isActive, setIsActive] = useState(false);
    const [expiresAt, setExpiresAt] = useState<string | null>(null);
    const [daysRemaining, setDaysRemaining] = useState(0);
    const [lang, setLang] = useState("th");

    const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
    const [slipFile, setSlipFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    const [paymentHistory, setPaymentHistory] = useState<PaymentHistoryItem[]>([]);

    const fetchPlans = useCallback(async () => {
        try {
            const res = await api.get<ApiResponse<{
                plans: Plan[];
                payment_account: PaymentAccount;
                current_tier: string;
                is_active: boolean;
                expires_at: string | null;
                days_remaining: number;
                language?: string;
            }>>("/payment/plans");
            const data = res.data.data;
            setPlans(data.plans);
            setPaymentAccount(data.payment_account);
            setCurrentTier(data.current_tier);
            setIsActive(data.is_active ?? false);
            setExpiresAt(data.expires_at);
            setDaysRemaining(data.days_remaining ?? 0);
            if (data.language) setLang(data.language);
        } catch {
            toast.error("Failed to load subscription plans");
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchHistory = useCallback(async () => {
        try {
            const res = await api.get<ApiResponse<{ payments: PaymentHistoryItem[] }>>("/payment/history");
            setPaymentHistory(res.data.data.payments ?? []);
        } catch {
            // silent
        }
    }, []);

    useEffect(() => {
        fetchPlans();
        fetchHistory();
    }, [fetchPlans, fetchHistory]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSlipFile(e.target.files[0]);
        }
    };

    const handleSubmit = async () => {
        if (!selectedPlan || !slipFile) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append("plan_type", selectedPlan);
        formData.append("file", slipFile);

        try {
            await api.post("/payment/verify-slip", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });

            const successMsg = lang === "en" ? "Payment Successful! Upgraded to Premium." : "ชำระเงินสำเร็จ! อัพเกรดเป็น Premium แล้ว";
            toast.success(successMsg);

            // Refetch server state instead of optimistic update
            await fetchPlans();
            await fetchHistory();
            setSelectedPlan(null);
            setSlipFile(null);

            window.scrollTo({ top: 0, behavior: 'smooth' });

        } catch (error: unknown) {
            const errMsg = getApiErrorMessage(error, lang === "en" ? "Payment Failed" : "ชำระเงินไม่สำเร็จ");
            toast.error(errMsg);
        } finally {
            setIsUploading(false);
        }
    };

    if (loading) {
        return <div className="p-8 flex items-center justify-center">Loading...</div>;
    }

    // Bilingual Texts
    const t = {
        title: lang === "en" ? "Subscription" : "Subscription",
        subtitle: lang === "en" ? "Upgrade to Premium for full access" : "อัพเกรดเป็น Premium เพื่อใช้งานเต็มรูปแบบ",
        currentStatus: lang === "en" ? "Current Status" : "สถานะปัจจุบัน",
        expires: lang === "en" ? "Expires: " : "หมดอายุ: ",
        daysLeft: lang === "en" ? "days remaining" : "วันที่เหลือ",
        perDay: lang === "en" ? "Days" : "วัน",
        price: lang === "en" ? "THB" : "บาท",
        payTitle: lang === "en" ? "Payment" : "ชำระเงิน",
        transferTo: lang === "en" ? "Transfer to:" : "โอนเงินมาที่:",
        bank: lang === "en" ? "Bank:" : "ธนาคาร:",
        accNo: lang === "en" ? "Account No.:" : "เลขบัญชี:",
        accName: lang === "en" ? "Account Name:" : "ชื่อบัญชี:",
        amount: lang === "en" ? "Amount:" : "ยอดโอน:",
        uploadLabel: lang === "en" ? "Upload Transfer Slip" : "อัพโหลดสลิปการโอนเงิน",
        verifyBtn: lang === "en" ? "Verify & Pay" : "ตรวจสอบและชำระเงิน",
        verifying: lang === "en" ? "Verifying..." : "กำลังตรวจสอบ...",
        back: lang === "en" ? "Back" : "กลับ",
        free: "Free",
        premium: "Premium",
        premiumActive: lang === "en" ? "Premium Active" : "Premium ใช้งานอยู่",
        premiumExpired: lang === "en" ? "Expired" : "หมดอายุแล้ว",
        historyTitle: lang === "en" ? "Payment History" : "ประวัติการชำระเงิน",
        noHistory: lang === "en" ? "No payment history" : "ยังไม่มีประวัติการชำระเงิน",
        date: lang === "en" ? "Date" : "วันที่",
        plan: lang === "en" ? "Plan" : "แพลน",
        amountCol: lang === "en" ? "Amount" : "ยอดเงิน",
        statusCol: lang === "en" ? "Status" : "สถานะ",
    };

    // Derive status badge
    const getStatusBadge = () => {
        if (isActive) {
            return <Badge variant="default" className="bg-green-600">{t.premiumActive}</Badge>;
        }
        if (currentTier === "premium" || expiresAt) {
            // Expired premium — server already normalized tier to "free"
            return <Badge variant="destructive">{t.premiumExpired}</Badge>;
        }
        return <Badge variant="secondary">{t.free}</Badge>;
    };

    return (
        <div className="p-6 md:p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard')}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t.title}</h1>
                    <p className="text-slate-500">{t.subtitle}</p>
                </div>
            </div>

            {/* Current Status */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Crown className="h-5 w-5" />
                        {t.currentStatus}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-4 flex-wrap">
                        {getStatusBadge()}
                        {expiresAt && (
                            <span className="text-sm text-slate-500">
                                {t.expires} {new Date(expiresAt).toLocaleDateString(lang === 'en' ? 'en-US' : 'th-TH')}
                            </span>
                        )}
                        {isActive && daysRemaining > 0 && (
                            <span className="text-sm text-slate-500 flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" />
                                {daysRemaining} {t.daysLeft}
                            </span>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Plans */}
            <div className="grid md:grid-cols-2 gap-6">
                {plans.map((plan) => (
                    <Card
                        key={plan.plan_type}
                        className={`cursor-pointer transition-all ${selectedPlan === plan.plan_type
                                ? "ring-2 ring-primary border-primary"
                                : "hover:shadow-lg"
                            }`}
                        onClick={() => setSelectedPlan(plan.plan_type)}
                    >
                        <CardHeader>
                            <CardTitle>{lang === 'en' ? plan.name_en : plan.name}</CardTitle>
                            <CardDescription>{lang === 'en' ? plan.name : plan.name_en}</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold mb-4">
                                {plan.price} {t.price}
                                <span className="text-sm font-normal text-slate-500">
                                    /{plan.duration_days} {t.perDay}
                                </span>
                            </div>
                            <ul className="space-y-2">
                                {plan.features.map((feature, i) => (
                                    <li key={i} className="flex items-center gap-2">
                                        <Check className="h-4 w-4 text-green-500" />
                                        <span className="text-sm">{feature}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Payment Form */}
            {selectedPlan && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CreditCard className="h-5 w-5" />
                            {t.payTitle}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                            <p className="font-medium">{t.transferTo}</p>
                            <div className="grid grid-cols-[100px_1fr] gap-1 text-sm">
                                <span className="text-slate-500">{t.bank}</span>
                                <span className="font-medium">{paymentAccount?.bank}</span>

                                <span className="text-slate-500">{t.accNo}</span>
                                <span className="font-medium font-mono text-lg">{paymentAccount?.account_number}</span>

                                <span className="text-slate-500">{t.accName}</span>
                                <span className="font-medium">{paymentAccount?.account_name}</span>

                                <span className="text-slate-500 mt-2">{t.amount}</span>
                                <span className="font-bold text-xl text-primary mt-2">
                                    {plans.find(p => p.plan_type === selectedPlan)?.price} {t.price}
                                </span>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">
                                {t.uploadLabel}
                            </label>
                            <Input
                                type="file"
                                accept="image/*"
                                onChange={handleFileChange}
                            />
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button
                            onClick={handleSubmit}
                            disabled={!slipFile || isUploading}
                            className="w-full"
                        >
                            {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {isUploading ? t.verifying : t.verifyBtn}
                        </Button>
                    </CardFooter>
                </Card>
            )}

            {/* Payment History */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <History className="h-5 w-5" />
                        {t.historyTitle}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {paymentHistory.length === 0 ? (
                        <p className="text-sm text-slate-500">{t.noHistory}</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-left text-slate-500">
                                        <th className="pb-2 pr-4">{t.date}</th>
                                        <th className="pb-2 pr-4">{t.plan}</th>
                                        <th className="pb-2 pr-4">{t.amountCol}</th>
                                        <th className="pb-2">{t.statusCol}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {paymentHistory.map((item) => (
                                        <tr key={item.id} className="border-b last:border-0">
                                            <td className="py-2 pr-4">
                                                {new Date(item.created_at).toLocaleDateString(
                                                    lang === "en" ? "en-US" : "th-TH"
                                                )}
                                            </td>
                                            <td className="py-2 pr-4 capitalize">{item.plan_type}</td>
                                            <td className="py-2 pr-4">{item.amount} {t.price}</td>
                                            <td className="py-2">
                                                <Badge
                                                    variant={item.status === "verified" ? "default" : "destructive"}
                                                    className="text-xs"
                                                >
                                                    {item.status}
                                                </Badge>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
