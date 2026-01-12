
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
    return (
        <div className="p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-slate-500">Manage your account preferences</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Profile Settings</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground mb-4">Profile editing features are coming soon.</p>
                    <Button variant="outline" disabled>Edit Profile</Button>
                </CardContent>
            </Card>
        </div>
    );
}
