import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone is for Docker/self-hosting only
  // Vercel uses its own optimized output format
  ...(process.env.VERCEL ? {} : { output: 'standalone' }),

  async rewrites() {
    const apiUrl = process.env.BACKEND_URL || 'http://localhost:8888';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
