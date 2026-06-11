import { createSerwistRoute } from "@serwist/turbopack";

// Cache-busting revision for non-build-manifest precache entries.
// Vercel exposes the commit SHA; local builds fall back to a random id
// (only invalidates the offline page's precache entry, which is cheap).
const revision = process.env.VERCEL_GIT_COMMIT_SHA ?? crypto.randomUUID();

export const { dynamic, dynamicParams, revalidate, generateStaticParams, GET } =
    createSerwistRoute({
        additionalPrecacheEntries: [{ url: "/~offline", revision }],
        swSrc: "sw/index.ts",
        useNativeEsbuild: true,
    });
