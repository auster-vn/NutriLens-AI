"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Bot, GitCompare, Heart, Home, LogIn, LogOut,
  PackageSearch, ScanLine, Soup, User
} from "lucide-react";
import { useAuth } from "./AuthProvider";

const nav = [
  { href: "/",             label: "Tổng quan",   icon: Home },
  { href: "/scan",         label: "Quét mã",     icon: ScanLine },
  { href: "/compare",      label: "So sánh",     icon: GitCompare },
  { href: "/chat",         label: "Chat AI",     icon: Bot },
  { href: "/pantry",       label: "Tủ đồ",      icon: PackageSearch },
  { href: "/favorites",    label: "Yêu thích",   icon: Heart },
  { href: "/meal-planner", label: "Bữa ăn",      icon: Soup },
  { href: "/profile",      label: "Hồ sơ",      icon: User },
];

const protectedRoutes = ["/pantry", "/favorites", "/meal-planner", "/profile"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  if (pathname.startsWith("/admin")) {
    return <div className="admin-workspace">
      <header className="admin-topbar">
        <Link href="/admin" className="admin-brand"><BarChart3 size={18} />NutriLens Control Plane</Link>
        <div className="admin-topbar-actions"><span>Knowledge & Data Operations</span><Link href="/" className="button secondary">Về ứng dụng</Link></div>
      </header>
      <main className="admin-main">{children}</main>
    </div>;
  }
  const protectedRoute = protectedRoutes.some((r) => pathname.startsWith(r));

  const initials = user?.display_name
    ? user.display_name.slice(0, 2).toUpperCase()
    : "?";

  return (
    <>
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-icon">
            <BarChart3 size={16} aria-hidden />
          </span>
          NutriLens
        </Link>

        <nav>
          {nav.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                className={active ? "active" : ""}
              >
                <Icon aria-hidden size={16} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="account-block">
          {user ? (
            <>
              <div className="account-avatar">{initials}</div>
              <div className="account-copy">
                <strong>{user.display_name}</strong>
                <span>{user.email}</span>
              </div>
              <button
                className="icon-button"
                title="Đăng xuất"
                onClick={() => void logout()}
              >
                <LogOut size={15} />
              </button>
            </>
          ) : (
            <Link href="/auth" className="account-link">
              <LogIn size={15} />
              <span>Đăng nhập</span>
            </Link>
          )}
        </div>
      </aside>

      <main className="shell">
        {loading ? (
          <div className="loading-state">Đang tải không gian làm việc…</div>
        ) : null}

        {!loading && protectedRoute && !user ? (
          <section className="auth-gate animate-fade-in">
            <User size={32} strokeWidth={1.5} />
            <h1>Đăng nhập để tiếp tục</h1>
            <p className="muted">
              Dữ liệu dinh dưỡng cá nhân được lưu trữ theo từng tài khoản.
            </p>
            <Link href="/auth" className="button">
              <LogIn size={16} />
              Tiếp tục
            </Link>
          </section>
        ) : null}

        {!loading && (!protectedRoute || user) ? children : null}
      </main>
    </>
  );
}
