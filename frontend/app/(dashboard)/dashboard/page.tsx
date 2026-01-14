"use client";

import { useEffect, useState, useRef } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { Activity, Users, FilePlus, Calendar, LogOut, Settings, Camera, Upload, Loader2, X, ChevronLeft, ChevronRight, Crown } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BPChart } from "@/components/bp-chart";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

export default function DashboardPage() {
    const router = useRouter();
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const { t, setLanguage } = useLanguage();

    useEffect(() => {
        const userCookie = Cookies.get("user");
        if (!userCookie) {
            router.push("/auth/login");
            return;
        }
        try {
            const userData = JSON.parse(userCookie);
            setUser(userData);
            if (userData.language) {
                setLanguage(userData.language);
            }
        } catch (e) {
            router.push("/auth/login");
        } finally {
            setLoading(false);
        }
    }, [router, setLanguage]);

    const handleLogout = async () => {
        try {
            await api.post("/auth/logout");
        } catch (e) {
            console.error("Logout failed", e);
        }
        Cookies.remove("token");
        Cookies.remove("user");
        router.push("/auth/login");
        toast.success("Logged out successfully");
    };

    if (loading) return <div className="p-8">Loading...</div>;
    if (!user) return null;

    return (
        <div className="p-6 md:p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t('common.dashboard')}</h1>
                    <p className="text-slate-500">{t('dashboard.welcome')} {user.full_name}</p>
                </div>
                <div className="flex items-center gap-4">
                    <LanguageSwitcher />
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                                <Avatar className="h-10 w-10">
                                    <AvatarImage src={`https://api.dicebear.com/7.x/initials/svg?seed=${user.full_name}`} />
                                    <AvatarFallback>{user.full_name[0]}</AvatarFallback>
                                </Avatar>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-56" align="end" forceMount>
                            <DropdownMenuLabel className="font-normal">
                                <div className="flex flex-col space-y-1">
                                    <p className="text-sm font-medium leading-none">{user.full_name}</p>
                                    <p className="text-xs leading-none text-muted-foreground">{user.role}</p>
                                </div>
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => router.push('/settings')}>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>{t('common.settings')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => router.push('/subscription')}>
                                <Crown className="mr-2 h-4 w-4 text-yellow-500" />
                                <span>{t('common.subscription')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                                <LogOut className="mr-2 h-4 w-4" />
                                <span>{t('common.logout')}</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            {user.role === "patient" ? <PatientView user={user} /> : <DoctorView user={user} />}
        </div>
    );
}

function PatientView({ user }: { user: any }) {
    const { t } = useLanguage();
    const [stats, setStats] = useState<any>(null);
    const [graphRecords, setGraphRecords] = useState<any[]>([]);
    const [tableRecords, setTableRecords] = useState<any[]>([]);
    const [pagination, setPagination] = useState<any>({ current_page: 1, total_pages: 1 });
    const [loadingData, setLoadingData] = useState(true);
    const [isAddOpen, setIsAddOpen] = useState(false);

    // OCR & Form states
    const [activeTab, setActiveTab] = useState("photo");
    const [ocrLoading, setOcrLoading] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form fields
    const [sys, setSys] = useState("");
    const [dia, setDia] = useState("");
    const [pulse, setPulse] = useState("");
    const [measureDate, setMeasureDate] = useState("");
    const [measureTime, setMeasureTime] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const fetchInitialData = async () => {
        setLoadingData(true);
        try {
            const [statsRes, recordsRes] = await Promise.all([
                api.get("/stats/summary?days=30"),
                api.get("/bp-records?per_page=30&page=1")
            ]);

            if (statsRes.data.data.stats) {
                setStats(statsRes.data.data.stats);
            }

            const records = recordsRes.data.data.records;
            const meta = recordsRes.data.meta.pagination;

            setGraphRecords(records); // Graph always shows latest 30
            setTableRecords(records); // Table starts with page 1
            setPagination(meta);

        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoadingData(false);
        }
    };

    const fetchTablePage = async (page: number) => {
        try {
            const res = await api.get(`/bp-records?per_page=30&page=${page}`);
            setTableRecords(res.data.data.records);
            setPagination(res.data.meta.pagination);
        } catch (error) {
            console.error("Failed to fetch page", error);
        }
    };

    useEffect(() => {
        fetchInitialData();
        // Set default date/time when dialog opens (only if empty)
        if (isAddOpen && !measureDate) {
            const now = new Date();
            setMeasureDate(now.toISOString().split('T')[0]);
            setMeasureTime(now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }));
        }
    }, [isAddOpen]); // Depend on isAddOpen to reset defaults

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.[0]) return;

        const file = e.target.files[0];
        // Create preview
        const objectUrl = URL.createObjectURL(file);
        setPreviewUrl(objectUrl);

        const formData = new FormData();
        formData.append("file", file);

        setOcrLoading(true);
        try {
            const res = await api.post("/ocr/process-image", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            const { ocr_result } = res.data.data;

            if (ocr_result.error) {
                toast.error("OCR Error: " + ocr_result.error);
                return;
            }

            // Pre-fill form
            if (ocr_result.systolic) setSys(ocr_result.systolic.toString());
            if (ocr_result.diastolic) setDia(ocr_result.diastolic.toString());
            if (ocr_result.pulse) setPulse(ocr_result.pulse.toString());

            // Use derived timestamp priority
            if (ocr_result.measurement_date) setMeasureDate(ocr_result.measurement_date);
            if (ocr_result.measurement_time) setMeasureTime(ocr_result.measurement_time);

            toast.success("Read successful! Please verify numbers and time.");
            setActiveTab("manual"); // Switch to manual tab for review

        } catch (error: any) {
            console.error("OCR Failed", error);
            toast.error("Failed to process image. Please enter manually.");
        } finally {
            setOcrLoading(false);
            if (fileInputRef.current) fileInputRef.current.value = ""; // Reset input so same file can be selected again
        }
    };

    const clearPreview = () => {
        setPreviewUrl(null);
        setSys(""); setDia(""); setPulse("");
    };

    const handleAddRecord = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            // Construct ISO string from date and time inputs
            const specificDate = new Date(`${measureDate}T${measureTime}:00`);

            await api.post("/bp-records", {
                systolic: parseInt(sys),
                diastolic: parseInt(dia),
                pulse: parseInt(pulse),
                measurement_date: specificDate.toISOString(),
                measurement_time: measureTime,
                notes: "Web Entry"
            });
            toast.success("Record added successfully");
            setIsAddOpen(false);
            // Reset form
            setSys(""); setDia(""); setPulse("");
            setPreviewUrl(null);
            setActiveTab("photo");
            fetchInitialData(); // Refresh both table and graph
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to add record");
        } finally {
            setSubmitting(false);
        }
    };

    // Derived values
    const lastReading = graphRecords.length > 0 ? graphRecords[0] : null; // Uses graphRecords (latest)
    const avgPulse = stats ? Math.round(stats.pulse.avg) : "-";

    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.last_reading', 'Last Reading')}</CardTitle>
                        <Activity className="h-4 w-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {lastReading ? `${lastReading.systolic}/${lastReading.diastolic}` : "--/--"}
                        </div>
                        <p className="text-xs text-slate-500">
                            {lastReading ? new Date(lastReading.measurement_date).toLocaleDateString() : t('common.no_data', 'No data')}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.avg_pulse')}</CardTitle>
                        <Activity className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{avgPulse} bpm</div>
                        <p className="text-xs text-slate-500">Last 30 records</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.total_records', 'Total Records')}</CardTitle>
                        <FilePlus className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats ? stats.total_records_all_time : 0}</div>
                        <p className="text-xs text-slate-500">All time records</p>
                    </CardContent>
                </Card>
            </div>

            <div className="flex gap-4">
                <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                    <DialogTrigger asChild>
                        <Button className="gap-2">
                            <FilePlus className="w-4 h-4" /> {t('dashboard.add_record')}
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                        <DialogHeader>
                            <DialogTitle>{t('record.add_title')}</DialogTitle>
                            <DialogDescription>
                                {t('record.add_desc')}
                            </DialogDescription>
                        </DialogHeader>

                        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="photo">{t('dashboard.scan_ocr')}</TabsTrigger>
                                <TabsTrigger value="manual">{t('dashboard.manual_entry')}</TabsTrigger>
                            </TabsList>

                            <TabsContent value="photo" className="space-y-4 py-4">
                                <div className="grid w-full items-center gap-4">
                                    {previewUrl ? (
                                        <div className="relative w-full h-48 bg-black/5 rounded-lg overflow-hidden flex items-center justify-center">
                                            <img src={previewUrl} alt="Preview" className="h-full object-contain" />
                                            <Button
                                                variant="secondary"
                                                size="icon"
                                                className="absolute top-2 right-2 h-8 w-8 rounded-full bg-white/80 hover:bg-white"
                                                onClick={clearPreview}
                                            >
                                                <X className="h-4 w-4 text-slate-700" />
                                            </Button>
                                            {ocrLoading && (
                                                <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-10">
                                                    <Loader2 className="h-10 w-10 animate-spin text-white" />
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg border-slate-300 bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer"
                                            onClick={() => !ocrLoading && fileInputRef.current?.click()}
                                        >
                                            <Camera className="h-10 w-10 text-slate-400 mb-2" />
                                            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Tap to Scan / Upload</span>
                                            <span className="text-xs text-slate-500 mt-1">Supports JPG, PNG</span>
                                        </div>
                                    )}

                                    <input
                                        type="file"
                                        accept="image/*"
                                        capture="environment"
                                        className="hidden"
                                        ref={fileInputRef}
                                        onChange={handleFileChange}
                                        disabled={ocrLoading}
                                    />

                                    <div className="text-center">
                                        <p className="text-xs text-muted-foreground">
                                            AI reads Date/Time from screen, EXIF, or fallback.
                                        </p>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="manual">
                                <form onSubmit={handleAddRecord}>
                                    <div className="grid gap-4 py-4">
                                        {previewUrl && (
                                            <div className="flex justify-center mb-4">
                                                <img src={previewUrl} alt="Reference" className="h-20 w-auto rounded border" />
                                            </div>
                                        )}
                                        <div className="grid grid-cols-4 items-center gap-4">
                                            <Label htmlFor="date" className="text-right">{t('record.date')}</Label>
                                            <Input id="date" value={measureDate} onChange={e => setMeasureDate(e.target.value)} type="date" className="col-span-3" required />
                                        </div>
                                        <div className="grid grid-cols-4 items-center gap-4">
                                            <Label htmlFor="time" className="text-right">{t('record.time')}</Label>
                                            <Input id="time" value={measureTime} onChange={e => setMeasureTime(e.target.value)} type="time" className="col-span-3" required />
                                        </div>
                                        <div className="grid grid-cols-4 items-center gap-4">
                                            <Label htmlFor="sys" className="text-right">{t('record.systolic')}</Label>
                                            <Input id="sys" value={sys} onChange={e => setSys(e.target.value)} type="number" placeholder="120" className="col-span-3" required />
                                        </div>
                                        <div className="grid grid-cols-4 items-center gap-4">
                                            <Label htmlFor="dia" className="text-right">{t('record.diastolic')}</Label>
                                            <Input id="dia" value={dia} onChange={e => setDia(e.target.value)} type="number" placeholder="80" className="col-span-3" required />
                                        </div>
                                        <div className="grid grid-cols-4 items-center gap-4">
                                            <Label htmlFor="pulse" className="text-right">{t('record.pulse')}</Label>
                                            <Input id="pulse" value={pulse} onChange={e => setPulse(e.target.value)} type="number" placeholder="72" className="col-span-3" required />
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button type="submit" disabled={submitting}>{t('common.save')}</Button>
                                    </DialogFooter>
                                </form>
                            </TabsContent>
                        </Tabs>
                    </DialogContent>
                </Dialog>

                <Button variant="outline" className="gap-2" onClick={() => toast.info(t('common.coming_soon'))}>
                    <Users className="w-4 h-4" /> {t('common.manage_doctors')}
                </Button>
            </div>

            {/* Trends Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>{t('dashboard.bp_trends', 'Blood Pressure Trends')} (Last 30)</CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingData ? (
                        <div className="h-[350px] flex items-center justify-center text-slate-500">{t('common.loading')}</div>
                    ) : graphRecords.length > 0 ? (
                        <BPChart data={graphRecords} />
                    ) : (
                        <div className="h-[350px] flex items-center justify-center text-slate-500">{t('common.no_data')}</div>
                    )}
                </CardContent>
            </Card>

            <Card className="col-span-4">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>{t('common.history')}</CardTitle>
                        <span className="text-sm text-slate-500">
                            Page {pagination?.current_page} / {pagination?.total_pages}
                        </span>
                    </div>
                </CardHeader>
                <CardContent>
                    {loadingData ? (
                        <div className="text-slate-500 text-sm">{t('common.loading')}</div>
                    ) : tableRecords.length === 0 ? (
                        <div className="text-slate-500 text-sm">{t('common.no_data')}</div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>{t('record.date')}</TableHead>
                                        <TableHead>{t('record.systolic')}</TableHead>
                                        <TableHead>{t('record.diastolic')}</TableHead>
                                        <TableHead>{t('record.pulse')}</TableHead>
                                        <TableHead>
                                            <span className="hidden md:inline">{t('record.notes', 'Notes')}</span>
                                            <span className="md:hidden">Note</span>
                                        </TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {tableRecords.map((r, i) => (
                                        <TableRow key={r.id || i}>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span>{new Date(r.measurement_date).toLocaleDateString()}</span>
                                                    <span className="text-xs text-slate-500 md:hidden">{r.measurement_time}</span>
                                                </div>
                                                <span className="hidden md:inline pl-1">{r.measurement_time}</span>
                                            </TableCell>
                                            <TableCell className="font-medium">{r.systolic}</TableCell>
                                            <TableCell>{r.diastolic}</TableCell>
                                            <TableCell>{r.pulse}</TableCell>
                                            <TableCell className="text-slate-500 text-xs md:text-sm">
                                                {r.notes || "Manual"}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>

                            {/* Pagination Controls */}
                            <div className="flex items-center justify-end space-x-2 py-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => fetchTablePage(pagination.current_page - 1)}
                                    disabled={pagination.current_page <= 1}
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                    {t('common.previous')}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => fetchTablePage(pagination.current_page + 1)}
                                    disabled={pagination.current_page >= pagination.total_pages}
                                >
                                    {t('common.next')}
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function DoctorView({ user }: { user: any }) {
    const { t } = useLanguage();
    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('doctor.total_patients')}</CardTitle>
                        <Users className="h-4 w-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">12</div>
                        <p className="text-xs text-slate-500">{t('doctor.active_monitoring')}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('doctor.pending_requests')}</CardTitle>
                        <Calendar className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">3</div>
                        <p className="text-xs text-slate-500">{t('doctor.requires_approval')}</p>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="patients" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="patients">{t('doctor.my_patients')}</TabsTrigger>
                    <TabsTrigger value="requests">{t('doctor.access_requests')}</TabsTrigger>
                </TabsList>
                <TabsContent value="patients" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>{t('doctor.patient_list')}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-slate-500 text-sm">{t('common.loading')} (Demo)</div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
