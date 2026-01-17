"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, User, Stethoscope } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { LanguageSwitcher } from "@/components/language-switcher";

export default function Home() {
  const { t } = useLanguage();

  return (
    <div className="flex flex-col min-h-screen">
      <header className="px-6 h-16 flex items-center border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-transparent bg-clip-text">
          BP Monitor
        </div>
        <div className="ml-auto flex gap-4 items-center">
          <LanguageSwitcher />
          <Link href="/auth/login">
            <Button variant="ghost">{t('common.login')}</Button>
          </Link>
          <Link href="/auth/register">
            <Button>{t('common.get_started')}</Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <section className="py-24 px-6 text-center bg-slate-50 dark:bg-slate-950">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            {t('landing.hero_title')}
            <br />
            <span className="text-blue-600">Monitoring System</span>
          </h1>
          <p className="mt-6 text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            {t('landing.hero_subtitle')}
          </p>
          <div className="mt-10 flex gap-4 justify-center">
            <Link href="/auth/register">
              <Button size="lg" className="gap-2">
                {t('landing.start_tracking')} <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </section>

        <section className="py-16 px-6 grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          <div className="p-6 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition">
            <div className="h-12 w-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4">
              <User className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold">{t('landing.for_patients')}</h3>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              {t('landing.for_patients_desc')}
            </p>
          </div>
          <div className="p-6 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition">
            <div className="h-12 w-12 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center mb-4">
              <Stethoscope className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold">{t('landing.for_doctors')}</h3>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              {t('landing.for_doctors_desc')}
            </p>
          </div>
        </section>
      </main>

      <footer className="py-8 text-center text-sm text-slate-500 border-t">
        {t('landing.footer')}
      </footer>
    </div>
  );
}
