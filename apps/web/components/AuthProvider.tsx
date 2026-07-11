"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
};

type Credentials = { email: string; password: string };
type RegisterInput = Credentials & { display_name: string };
type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (input: Credentials) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  enterDemo: () => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(await apiFetch<AuthUser>("/api/auth/me"));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Bootstrap the browser session once when the provider mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  const authenticate = useCallback(async (path: string, input?: object) => {
    const session = await apiFetch<{ user: AuthUser }>(path, {
      method: "POST",
      body: input ? JSON.stringify(input) : undefined
    });
    setUser(session.user);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    login: (input) => authenticate("/api/auth/login", input),
    register: (input) => authenticate("/api/auth/register", input),
    enterDemo: () => authenticate("/api/auth/demo"),
    logout: async () => {
      await apiFetch<void>("/api/auth/logout", { method: "POST" });
      setUser(null);
    },
    refresh
  }), [authenticate, loading, refresh, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
