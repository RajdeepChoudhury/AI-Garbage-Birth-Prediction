import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { Role, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  hasRole: (...roles: Role[]) => boolean;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => api.tokens.get() !== null);
  const qc = useQueryClient();

  const signOut = useCallback(() => {
    api.tokens.clear();
    setUser(null);
    qc.clear();
  }, [qc]);

  useEffect(() => {
    if (!api.tokens.get()) return;
    api.getMe()
      .then(setUser)
      .catch(() => api.tokens.clear())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    window.addEventListener("gbp:logout", signOut);
    return () => window.removeEventListener("gbp:logout", signOut);
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const t = await api.login(email, password);
    api.tokens.set({ access: t.access_token, refresh: t.refresh_token });
    setUser(await api.getMe());
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    await api.register(email, password);
    await signIn(email, password);
  }, [signIn]);

  const value = useMemo<AuthState>(
    () => ({ user, loading, signIn, signUp, signOut, hasRole: (...roles) => !!user && roles.includes(user.role) }),
    [user, loading, signIn, signUp, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
