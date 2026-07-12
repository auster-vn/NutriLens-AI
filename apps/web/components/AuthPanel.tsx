"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, LogIn, UserPlus, Leaf, ShieldCheck, Zap } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { toUserMessage } from "@/lib/api";

export function AuthPanel() {
  const router = useRouter();
  const { login, register, enterDemo } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      if (mode === "login") await login({ email, password });
      else await register({ email, password, display_name: displayName });
      router.push("/");
    } catch (err) {
      setError(toUserMessage(err, "Không thể xác thực. Vui lòng thử lại."));
    } finally {
      setLoading(false);
    }
  }

  async function demo() {
    setLoading(true);
    setError(null);
    try {
      await enterDemo();
      router.push("/");
    } catch (err) {
      setError(toUserMessage(err, "Không thể mở phiên demo. Vui lòng thử lại."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout animate-fade-in">
      {/* Left – intro */}
      <section className="auth-intro">
        <p className="eyebrow">Không gian làm việc dinh dưỡng cá nhân</p>
        <h1>Quyết định sản phẩm, tủ đồ và thông tin chi tiết của bạn.</h1>

        <div style={{ display: "grid", gap: 14, maxWidth: 440 }}>
          {[
            { icon: ShieldCheck, label: "Bảo mật HttpOnly session & Argon2" },
            { icon: Leaf, label: "Phân tích thành phần dinh dưỡng thực phẩm" },
            { icon: Zap,  label: "Trả lời tức thì từ trợ lý AI được trích dẫn" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                width: 36, height: 36, borderRadius: "var(--r)",
                background: "rgba(16,185,129,0.10)",
                display: "grid", placeItems: "center",
                color: "var(--green)", flexShrink: 0,
              }}>
                <Icon size={17} />
              </div>
              <span style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-2)" }}>{label}</span>
            </div>
          ))}
        </div>

        <div className="auth-proof">
          <span>HttpOnly session</span>
          <span>Argon2 hashing</span>
          <span>Dữ liệu cách ly</span>
        </div>
      </section>

      {/* Right – form */}
      <section className="auth-form">
        <div>
          <p className="eyebrow" style={{ marginBottom: 4 }}>Bắt đầu ngay</p>
          <p className="auth-form-title">
            {mode === "login" ? "Đăng nhập tài khoản" : "Tạo tài khoản mới"}
          </p>
        </div>

        <div className="segmented" aria-label="Chế độ xác thực">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Đăng nhập
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Tạo tài khoản
          </button>
        </div>

        {mode === "register" ? (
          <label className="field">
            <span>Tên hiển thị</span>
            <input
              autoComplete="name"
              placeholder="Nguyễn Văn A"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>
        ) : null}

        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="field">
          <span>Mật khẩu</span>
          <input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={mode === "login" ? "••••••••" : "Ít nhất 8 ký tự"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button
          className="button"
          onClick={submit}
          disabled={loading || !email || password.length < 8}
          style={{ minHeight: 44 }}
        >
          {mode === "login" ? <LogIn size={16} /> : <UserPlus size={16} />}
          {loading ? "Đang xử lý…" : mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}
        </button>

        <div className="auth-divider"><span>hoặc</span></div>

        <button
          className="button secondary"
          onClick={demo}
          disabled={loading}
          style={{ minHeight: 44 }}
        >
          <FlaskConical size={16} />
          Mở demo portfolio
        </button>

        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
      </section>
    </div>
  );
}
