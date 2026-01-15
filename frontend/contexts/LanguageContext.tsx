"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from "js-cookie";
import { en } from '../locales/en';
import { th } from '../locales/th';
import api from '@/lib/api';

type Language = 'en' | 'th';

interface LanguageContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (path: string, fallback?: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguageState] = useState<Language>('en');
    const [isLoaded, setIsLoaded] = useState(false);

    // Load from LocalStorage on init
    useEffect(() => {
        const saved = localStorage.getItem('language') as Language;
        if (saved && (saved === 'en' || saved === 'th')) {
            setLanguageState(saved);
        }
        setIsLoaded(true);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const setLanguage = React.useCallback(async (lang: Language) => {
        setLanguageState(lang);
        localStorage.setItem('language', lang);

        // Update User Cookie to persist preference across refreshes
        const userCookie = Cookies.get("user");
        if (userCookie) {
            try {
                const userData = JSON.parse(userCookie);
                userData.language = lang;
                Cookies.set("user", JSON.stringify(userData), { expires: 7 }); // Preserve for 7 days
            } catch (e) {
                console.error("Failed to update user cookie", e);
            }
        }

        // Sync with Backend (Fire and Forget)
        try {
            await api.put('/users/me', { language: lang });
        } catch {
            // Ignore error if not logged in
        }
    }, []);

    // Helper to access nested keys (e.g. "dashboard.welcome")
    const t = React.useCallback((path: string, fallback?: string): string => {
        const keys = path.split('.');
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        let current: any = language === 'th' ? th : en;

        for (const key of keys) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return fallback || path;
            }
        }

        return typeof current === 'string' ? current : path;
    }, [language]); // t depends on language

    // Memoize the context value
    const contextValue = React.useMemo(() => ({
        language,
        setLanguage,
        t
    }), [language, setLanguage, t]);

    return (
        <LanguageContext.Provider value={contextValue}>
            {/* Prevent flash of wrong language content if needed, or just render */}
            {!isLoaded ? (
                // Render children even if not loaded to assume default 'en' or prevent blank page
                children
            ) : (
                children
            )}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (context === undefined) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return context;
}
