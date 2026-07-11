"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Bot, GitCompare, Heart, Home, LogIn, LogOut, PackageSearch,
  ScanLine, ShieldCheck, Soup, User
} from "lucide-react";
import { useAuth } from "./AuthProvider";

const nav = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/scan", label: "Scan", icon: ScanLine },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/chat", label: "Chat", icon: Bot },
  { href: "/pantry", label: "Pantry", icon: PackageSearch },
  { href: "/favorites", label: "Favorites", icon: Heart },
  { href: "/meal-planner", label: "Meals", icon: Soup },
  { href: "/profile", label: "Profile", icon: User },
  { href: "/admin", label: "Admin", icon: ShieldCheck }
];

const protectedRoutes = ["/pantry", "/favorites", "/meal-planner", "/profile"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const protectedRoute = protectedRoutes.some((route) => pathname.startsWith(route));

  return (
    <>
      <aside className="sidebar">
        <Link href="/" className="brand">
          <BarChart3 aria-hidden />
          <span>NutriLens</span>
        </Link>
        <nav>
          {nav.map((item) => {
            const Icon = item.icon;
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} title={item.label} className={active ? "active" : ""}>
                <Icon aria-hidden size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="account-block">
          {user ? (
            <>
              <div className="account-copy">
                <strong>{user.display_name}</strong>
                <span>{user.email}</span>
              </div>
              <button className="icon-button" title="Log out" onClick={() => void logout()}><LogOut size={17} /></button>
            </>
          ) : (
            <Link href="/auth" className="account-link"><LogIn size={17} /><span>Sign in</span></Link>
          )}
        </div>
      </aside>
      <main className="shell">
        {loading ? <div className="loading-state">Loading workspace...</div> : null}
        {!loading && protectedRoute && !user ? (
          <section className="auth-gate">
            <User size={28} />
            <h1>Sign in to open this workspace</h1>
            <p className="muted">Personal nutrition data is isolated per account.</p>
            <Link href="/auth" className="button"><LogIn size={18} />Continue</Link>
          </section>
        ) : null}
        {!loading && (!protectedRoute || user) ? children : null}
      </main>
    </>
  );
}
