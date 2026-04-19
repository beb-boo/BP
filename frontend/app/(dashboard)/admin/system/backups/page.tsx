"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronDown, ChevronUp, Database, Loader2, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-helpers";
import type { AppUser, NeonBranchItem } from "@/lib/app-types";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

const POLL_INTERVAL_MS = 30_000;

function formatBytes(bytes?: number | null): string {
    if (!bytes && bytes !== 0) return "–";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatTimestamp(value?: string | null): string {
    if (!value) return "–";
    try {
        return new Date(value).toLocaleString();
    } catch {
        return value;
    }
}

export default function BackupsPage() {
    const router = useRouter();
    const { t } = useLanguage();
    const [user, setUser] = useState<AppUser | null>(null);
    const [authChecked, setAuthChecked] = useState(false);

    const [branches, setBranches] = useState<NeonBranchItem[]>([]);
    const [loading, setLoading] = useState(true);

    const [createOpen, setCreateOpen] = useState(false);
    const [createName, setCreateName] = useState("");
    const [createDescription, setCreateDescription] = useState("");
    const [createTyped, setCreateTyped] = useState("");
    const [creating, setCreating] = useState(false);

    const [deleteTarget, setDeleteTarget] = useState<NeonBranchItem | null>(null);
    const [deleteTyped, setDeleteTyped] = useState("");
    const [deleting, setDeleting] = useState(false);

    const [showGuide, setShowGuide] = useState(false);

    // ── Auth guard (client-side; backend is the real guard) ────────
    useEffect(() => {
        const raw = Cookies.get("user");
        if (!raw) {
            router.push("/auth/login");
            return;
        }
        try {
            const parsed: AppUser = JSON.parse(raw);
            setUser(parsed);
        } catch {
            router.push("/auth/login");
            return;
        }
        setAuthChecked(true);
    }, [router]);

    const isSuperadmin = useMemo(() => {
        if (!user) return false;
        // Transition window: legacy role === 'staff' OR new primary_role === 'superadmin'
        if (user.role === "staff") return true;
        const extended = user as unknown as { primary_role?: string };
        return extended.primary_role === "superadmin";
    }, [user]);

    // ── Data fetch ─────────────────────────────────────────────────
    const fetchBranches = useCallback(async () => {
        try {
            const res = await api.get("/admin/system/backups");
            setBranches(res.data?.data?.branches ?? []);
        } catch (error) {
            toast.error(getApiErrorMessage(error, t("common.error")));
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => {
        if (!authChecked || !isSuperadmin) return;
        fetchBranches();
        const interval = setInterval(fetchBranches, POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [authChecked, isSuperadmin, fetchBranches]);

    // ── Create branch handler ──────────────────────────────────────
    const branchNameValid = /^[a-z0-9][a-z0-9-]{2,63}$/.test(createName);
    const canConfirmCreate = branchNameValid && createTyped === "CREATE" && !creating;

    const handleCreate = async () => {
        if (!canConfirmCreate) return;
        setCreating(true);
        try {
            await api.post("/admin/system/backups", {
                name: createName,
                description: createDescription,
            });
            toast.success(t("backups.create_success"));
            setCreateOpen(false);
            setCreateName("");
            setCreateDescription("");
            setCreateTyped("");
            fetchBranches();
        } catch (error) {
            toast.error(getApiErrorMessage(error, t("common.error")));
        } finally {
            setCreating(false);
        }
    };

    // ── Delete branch handler ──────────────────────────────────────
    const canConfirmDelete = deleteTarget !== null && deleteTyped === deleteTarget.name && !deleting;

    const handleDelete = async () => {
        if (!canConfirmDelete || !deleteTarget) return;
        setDeleting(true);
        try {
            await api.delete(`/admin/system/backups/${deleteTarget.id}`);
            toast.success(t("backups.delete_success"));
            setDeleteTarget(null);
            setDeleteTyped("");
            fetchBranches();
        } catch (error) {
            toast.error(getApiErrorMessage(error, t("common.error")));
        } finally {
            setDeleting(false);
        }
    };

    // ── Render ─────────────────────────────────────────────────────
    if (!authChecked) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin" />
            </div>
        );
    }

    if (!isSuperadmin) {
        return (
            <div className="flex min-h-screen items-center justify-center p-4">
                <Card className="max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ShieldAlert className="h-5 w-5 text-red-600" />
                            403
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-slate-600">{t("backups.forbidden")}</p>
                        <Link href="/dashboard" className="mt-4 inline-block">
                            <Button variant="outline" size="sm">
                                <ArrowLeft className="mr-2 h-4 w-4" />
                                Dashboard
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50">
            <div className="mx-auto max-w-4xl space-y-6 p-4 md:p-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Link href="/dashboard">
                            <Button variant="ghost" size="icon">
                                <ArrowLeft className="h-5 w-5" />
                            </Button>
                        </Link>
                        <div>
                            <h1 className="text-xl font-bold flex items-center gap-2">
                                <Database className="h-5 w-5 text-blue-600" />
                                {t("backups.title")}
                            </h1>
                        </div>
                    </div>
                    <LanguageSwitcher />
                </div>

                {/* Warning banner */}
                <Card className="border-amber-200 bg-amber-50">
                    <CardContent className="flex items-start gap-3 py-4">
                        <ShieldAlert className="h-5 w-5 shrink-0 text-amber-700" />
                        <p className="text-sm text-amber-900">{t("backups.warning_superadmin_only")}</p>
                    </CardContent>
                </Card>

                {/* Create section */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">{t("backups.create_section")}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="space-y-1">
                            <Label htmlFor="bk-name">{t("backups.name_label")}</Label>
                            <Input
                                id="bk-name"
                                value={createName}
                                onChange={(e) => setCreateName(e.target.value)}
                                placeholder={t("backups.name_placeholder")}
                            />
                            {createName.length > 0 && !branchNameValid ? (
                                <p className="text-xs text-red-600">
                                    ^[a-z0-9][a-z0-9-]{"{2,63}"}$ (lowercase letters, digits, hyphen)
                                </p>
                            ) : null}
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="bk-desc">{t("backups.description_label")}</Label>
                            <Input
                                id="bk-desc"
                                value={createDescription}
                                onChange={(e) => setCreateDescription(e.target.value)}
                                placeholder={t("backups.description_placeholder")}
                                maxLength={500}
                            />
                        </div>
                        <Button
                            onClick={() => {
                                setCreateTyped("");
                                setCreateOpen(true);
                            }}
                            disabled={!branchNameValid}
                        >
                            <Plus className="mr-2 h-4 w-4" />
                            {t("backups.create_button")}
                        </Button>
                    </CardContent>
                </Card>

                {/* Existing branches */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-base">{t("backups.existing_section")}</CardTitle>
                        <Button variant="ghost" size="sm" onClick={fetchBranches}>
                            {t("backups.refresh")}
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="flex justify-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                            </div>
                        ) : branches.length === 0 ? (
                            <p className="py-4 text-sm text-slate-500">{t("backups.no_branches")}</p>
                        ) : (
                            <ul className="space-y-3">
                                {branches.map((b) => (
                                    <li
                                        key={b.id}
                                        className="flex flex-col gap-2 rounded-md border border-slate-200 bg-white p-3 sm:flex-row sm:items-start sm:justify-between"
                                    >
                                        <div className="min-w-0 flex-1">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="font-mono text-sm font-medium">{b.name}</span>
                                                {b.is_default ? (
                                                    <Badge variant="secondary">{t("backups.branch_default")}</Badge>
                                                ) : null}
                                                {b.protected && !b.is_default ? (
                                                    <Badge variant="secondary">{t("backups.branch_protected")}</Badge>
                                                ) : null}
                                                {b.current_state ? (
                                                    <Badge variant="outline" className="text-xs">
                                                        {b.current_state}
                                                    </Badge>
                                                ) : null}
                                            </div>
                                            <dl className="mt-1 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-slate-500 sm:grid-cols-3">
                                                <div>
                                                    <dt className="inline font-medium">{t("backups.branch_size")}: </dt>
                                                    <dd className="inline">{formatBytes(b.logical_size_bytes)}</dd>
                                                </div>
                                                <div>
                                                    <dt className="inline font-medium">{t("backups.branch_created")}: </dt>
                                                    <dd className="inline">{formatTimestamp(b.created_at)}</dd>
                                                </div>
                                                <div>
                                                    <dt className="inline font-medium">{t("backups.branch_updated")}: </dt>
                                                    <dd className="inline">{formatTimestamp(b.updated_at)}</dd>
                                                </div>
                                            </dl>
                                            <p className="mt-1 truncate font-mono text-xs text-slate-400">{b.id}</p>
                                        </div>
                                        <div className="shrink-0">
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                disabled={b.is_default || b.protected}
                                                onClick={() => {
                                                    setDeleteTyped("");
                                                    setDeleteTarget(b);
                                                }}
                                            >
                                                <Trash2 className="mr-1 h-4 w-4" />
                                                {t("common.delete")}
                                            </Button>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </CardContent>
                </Card>

                {/* Local pg_dump guide */}
                <Card>
                    <CardHeader>
                        <button
                            type="button"
                            onClick={() => setShowGuide((v) => !v)}
                            className="flex w-full items-center justify-between text-left"
                        >
                            <CardTitle className="text-base">{t("backups.local_guide_section")}</CardTitle>
                            {showGuide ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                    </CardHeader>
                    {showGuide ? (
                        <CardContent className="prose prose-sm max-w-none text-slate-700">
                            <p className="text-sm">
                                Neon branch snapshots cover in-platform recovery. For an offline <code>.sql</code> file, run{" "}
                                <code>pg_dump</code> locally:
                            </p>
                            <ol className="list-decimal space-y-2 pl-5 text-sm">
                                <li>
                                    Install the Postgres client — <strong>version ≥ server</strong> (Neon runs
                                    Postgres 17, so <code>pg_dump</code> must be 17+):
                                    <ul className="mt-1 list-disc pl-5">
                                        <li>
                                            macOS: <code>brew install libpq@17 && brew link --force libpq@17</code>
                                        </li>
                                        <li>
                                            Linux: <code>sudo apt install postgresql-client-17</code> (PGDG repo)
                                        </li>
                                        <li>Windows: download from postgresql.org (v17+)</li>
                                        <li>
                                            No install: <code>docker run --rm -v &quot;$PWD:/out&quot; postgres:17 pg_dump ...</code>
                                        </li>
                                    </ul>
                                </li>
                                <li>
                                    Copy the connection string for the desired branch from the Neon Console → Connect.
                                </li>
                                <li>
                                    Run:
                                    <pre className="mt-1 whitespace-pre-wrap rounded bg-slate-900 p-3 text-xs text-slate-100">
{`# custom format (recommended)
pg_dump "postgresql://user:pass@ep-xxx.neon.tech/neondb" \\
  --no-owner --no-acl -Fc \\
  -f backup-$(date +%Y%m%d-%H%M).dump

# plain SQL text
pg_dump "postgresql://..." --no-owner --no-acl \\
  -f backup-$(date +%Y%m%d-%H%M).sql`}
                                    </pre>
                                </li>
                                <li>
                                    Store the file offline (contains PII). Never commit to git or upload unencrypted.
                                </li>
                            </ol>
                            <p className="mt-3 text-sm font-medium">Restore</p>
                            <pre className="whitespace-pre-wrap rounded bg-slate-900 p-3 text-xs text-slate-100">
{`# custom format
pg_restore --dbname="postgresql://..." --no-owner --no-acl backup.dump

# plain SQL
psql "postgresql://..." < backup.sql`}
                            </pre>
                            <p className="mt-3 text-xs text-slate-500">
                                Audit log only records Neon branch actions. Local <code>pg_dump</code> calls are not
                                visible to the admin panel.
                            </p>
                        </CardContent>
                    ) : null}
                </Card>
            </div>

            {/* Create confirmation */}
            <Dialog
                open={createOpen}
                onOpenChange={(v) => {
                    setCreateOpen(v);
                    if (!v) setCreateTyped("");
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t("backups.confirm_create_title")}</DialogTitle>
                        <DialogDescription>{t("backups.confirm_create_body")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 text-sm">
                        <p>
                            <span className="text-slate-500">Name:</span>{" "}
                            <span className="font-mono">{createName}</span>
                        </p>
                        <div>
                            <Label htmlFor="create-typed" className="text-xs">
                                {t("backups.confirm_create_typed")}
                            </Label>
                            <Input
                                id="create-typed"
                                value={createTyped}
                                onChange={(e) => setCreateTyped(e.target.value)}
                                autoComplete="off"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateOpen(false)}>
                            {t("backups.cancel")}
                        </Button>
                        <Button onClick={handleCreate} disabled={!canConfirmCreate}>
                            {creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            {t("backups.confirm_create_action")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete confirmation */}
            <Dialog
                open={deleteTarget !== null}
                onOpenChange={(v) => {
                    if (!v) {
                        setDeleteTarget(null);
                        setDeleteTyped("");
                    }
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t("backups.confirm_delete_title")}</DialogTitle>
                        <DialogDescription>{t("backups.confirm_delete_body")}</DialogDescription>
                    </DialogHeader>
                    {deleteTarget ? (
                        <div className="space-y-2 text-sm">
                            <p>
                                <span className="text-slate-500">Branch:</span>{" "}
                                <span className="font-mono">{deleteTarget.name}</span>
                            </p>
                            <div>
                                <Label htmlFor="delete-typed" className="text-xs">
                                    {t("backups.confirm_delete_typed")}
                                </Label>
                                <Input
                                    id="delete-typed"
                                    value={deleteTyped}
                                    onChange={(e) => setDeleteTyped(e.target.value)}
                                    autoComplete="off"
                                />
                            </div>
                        </div>
                    ) : null}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                            {t("backups.cancel")}
                        </Button>
                        <Button variant="destructive" onClick={handleDelete} disabled={!canConfirmDelete}>
                            {deleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            {t("backups.confirm_delete_action")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
