import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { AssistantReply, Forecast, Metrics, Risk, TokenPair, UploadSummary, User } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const STORAGE_KEY = "gbp_tokens";

interface Stored { access: string; refresh: string }

/** Tokens live in localStorage for simplicity. Move to httpOnly cookies before a real deployment. */
export const tokens = {
  get(): Stored | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as Stored) : null;
    } catch {
      return null;
    }
  },
  set(t: Stored) { localStorage.setItem(STORAGE_KEY, JSON.stringify(t)); },
  clear() { localStorage.removeItem(STORAGE_KEY); },
};

export const api = axios.create({ baseURL: BASE, timeout: 60_000 });

api.interceptors.request.use((cfg) => {
  const t = tokens.get();
  if (t) cfg.headers.Authorization = `Bearer ${t.access}`;
  return cfg;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccess(): Promise<string | null> {
  const t = tokens.get();
  if (!t) return null;
  try {
    const r = await axios.post<TokenPair>(`${BASE}/auth/refresh`, { refresh_token: t.refresh });
    tokens.set({ access: r.data.access_token, refresh: r.data.refresh_token });
    return r.data.access_token;
  } catch {
    tokens.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const cfg = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const url = cfg?.url ?? "";
    const isAuthCall = url === "/auth/login" || url === "/auth/refresh";
    if (error.response?.status === 401 && cfg && !cfg._retry && !isAuthCall) {
      cfg._retry = true;
      // One refresh at a time, shared by every request that failed together.
      refreshing ??= refreshAccess().finally(() => { refreshing = null; });
      const token = await refreshing;
      if (token) {
        cfg.headers.Authorization = `Bearer ${token}`;
        return api(cfg);
      }
      window.dispatchEvent(new Event("gbp:logout"));
    }
    return Promise.reject(error);
  },
);

export function apiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    if (!e.response) return "Cannot reach the server. Is the backend running?";
    const detail = e.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) return detail.map((d: { msg?: string }) => d.msg ?? "Invalid input").join("; ");
    if (e.response.status === 429) return "Too many requests. Please wait a moment.";
  }
  return "Something went wrong. Please try again.";
}

export const login = async (email: string, password: string) =>
  (await api.post<TokenPair>("/auth/login", { email, password })).data;
export const register = async (email: string, password: string) =>
  (await api.post<User>("/auth/register", { email, password })).data;
export const getMe = async () => (await api.get<User>("/auth/me")).data;

export const getForecasts = async (risk?: Risk) =>
  (await api.get<Forecast[]>("/predictions/latest", { params: risk ? { risk_level: risk } : {} })).data;
export const getMetrics = async () => (await api.get<Metrics>("/models/metrics")).data;

export const uploadCsv = async (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return (await api.post<UploadSummary>("/data/upload", form)).data;
};

export const askAssistant = async (question: string, availableTrucks?: number) =>
  (await api.post<AssistantReply>("/assistant/ask", { question, available_trucks: availableTrucks })).data;
export const dailyPlan = async (availableTrucks?: number) =>
  (await api.post<AssistantReply>("/assistant/daily-plan", { available_trucks: availableTrucks })).data;
export const executiveReport = async (availableTrucks?: number) =>
  (await api.post<AssistantReply>("/assistant/executive-report", { available_trucks: availableTrucks })).data;
