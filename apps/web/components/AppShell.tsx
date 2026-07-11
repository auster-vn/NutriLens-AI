"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BarChart3, Bot, GitCompare, Heart, Home, LogIn, LogOut, Menu, X,
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
const mobileTabs = [
  { href: "/", label: "Tổng quan", icon: Home },
  { href: "/scan", label: "Quét", icon: ScanLine },
  { href: "/chat", label: "Chat AI", icon: Bot },
  { href: "/meal-planner", label: "Bữa ăn", icon: Soup },
];
const mobileMore = nav.filter((item) => !mobileTabs.some((tab) => tab.href === item.href));

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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

      <header className="mobile-header">
        <Link href="/" className="mobile-brand" aria-label="NutriLens - Tổng quan">
          <span className="brand-icon"><BarChart3 size={16} aria-hidden /></span>
          <span>NutriLens</span>
        </Link>
        {user ? <Link href="/profile" className="mobile-avatar" aria-label="Mở hồ sơ">{initials}</Link> : <Link href="/auth" className="icon-button" aria-label="Đăng nhập"><LogIn size={17} /></Link>}
      </header>

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

      <nav className="mobile-bottom-nav" aria-label="Điều hướng chính">
        {mobileTabs.map((item) => {
          const Icon = item.icon;
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return <Link key={item.href} href={item.href} className={active ? "active" : ""} aria-current={active ? "page" : undefined}><Icon size={21} /><span>{item.label}</span></Link>;
        })}
        <button type="button" className={mobileMenuOpen ? "active" : ""} onClick={() => setMobileMenuOpen((open) => !open)} aria-expanded={mobileMenuOpen} aria-controls="mobile-more-menu"><Menu size={21} /><span>Thêm</span></button>
      </nav>

      {mobileMenuOpen ? <div className="mobile-sheet-layer" role="presentation" onClick={() => setMobileMenuOpen(false)}>
        <section id="mobile-more-menu" className="mobile-sheet" role="dialog" aria-modal="true" aria-label="Điều hướng bổ sung" onClick={(event) => event.stopPropagation()}>
          <div className="mobile-sheet-heading"><div><p className="eyebrow">Không gian làm việc</p><h2>Thêm chức năng</h2></div><button className="icon-button" onClick={() => setMobileMenuOpen(false)} aria-label="Đóng menu"><X size={18} /></button></div>
          <div className="mobile-menu-grid">{mobileMore.map((item) => { const Icon = item.icon; return <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)}><span><Icon size={20} /></span><strong>{item.label}</strong></Link>; })}</div>
          <div className="mobile-account-row">{user ? <><div className="mobile-avatar">{initials}</div><div><strong>{user.display_name}</strong><small>{user.email}</small></div><button className="button secondary" onClick={() => void logout()}><LogOut size={16} />Đăng xuất</button></> : <Link href="/auth" className="button"><LogIn size={16} />Đăng nhập</Link>}</div>
        </section>
      </div> : null}
    </>
  );
}
