"use client";

import { useEffect } from "react";

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 p-4">
            <div className="text-center space-y-4">
                <h1 className="text-6xl font-bold text-red-300 dark:text-red-700">Error</h1>
                <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
                    Something went wrong
                </h2>
                <p className="text-slate-500 max-w-md">
                    An unexpected error occurred. Please try again.
                </p>
                <div className="flex gap-4 justify-center pt-4">
                    <button
                        onClick={() => reset()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                        Try Again
                    </button>
                    <a
                        href="/dashboard"
                        className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md hover:bg-slate-100 transition-colors dark:text-slate-300 dark:border-slate-600 dark:hover:bg-slate-800"
                    >
                        Go to Dashboard
                    </a>
                </div>
            </div>
        </div>
    );
}
