import { cookies } from "next/headers";
import { redirect } from "next/navigation";

// Force dynamic rendering (cookies() requires it)
export const dynamic = "force-dynamic";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token");

  // Server-side auth check (defense-in-depth)
  // proxy.ts handles the first redirect, this is a safety net
  if (!token) {
    redirect("/auth/login");
  }

  return <>{children}</>;
}
