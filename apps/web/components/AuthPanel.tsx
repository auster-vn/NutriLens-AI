"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, LogIn, UserPlus } from "lucide-react";
import { useAuth } from "./AuthProvider";

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
      setError(err instanceof Error ? err.message : "Authentication failed");
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
      setError(err instanceof Error ? err.message : "Demo session failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-intro">
        <p className="eyebrow">Personal nutrition workspace</p>
        <h1>Your product decisions, pantry, and insights in one account.</h1>
        <div className="auth-proof">
          <span>HttpOnly session</span><span>Argon2 password hashing</span><span>User-isolated data</span>
        </div>
      </section>
      <section className="auth-form">
        <div className="segmented" aria-label="Authentication mode">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create account</button>
        </div>
        {mode === "register" ? (
          <label className="field"><span>Display name</span><input autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        ) : null}
        <label className="field"><span>Email</span><input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label className="field"><span>Password</span><input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <button className="button" onClick={submit} disabled={loading || !email || password.length < 8}>
          {mode === "login" ? <LogIn size={18} /> : <UserPlus size={18} />}
          {loading ? "Working" : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <div className="auth-divider"><span>or</span></div>
        <button className="button secondary" onClick={demo} disabled={loading}><FlaskConical size={18} />Open portfolio demo</button>
        {error ? <p className="error">{error}</p> : null}
      </section>
    </div>
  );
}
