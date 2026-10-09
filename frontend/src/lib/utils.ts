import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Forecast, Risk } from "./types";

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

export const RISK_ORDER: Risk[] = ["Low", "Medium", "High", "Critical"];
export const RISK_COLOR: Record<Risk, string> = {
  Low: "#22c55e",
  Medium: "#eab308",
  High: "#f97316",
  Critical: "#dc2626",
};

/** Five band scale from the project spec: green, yellow, orange, red, dark red. */
export function urgencyColor(urgency: number): string {
  if (urgency < 20) return "#22c55e";
  if (urgency < 40) return "#eab308";
  if (urgency < 60) return "#f97316";
  if (urgency < 80) return "#dc2626";
  return "#7f1d1d";
}

export function urgencyLabel(urgency: number): string {
  if (urgency < 20) return "Very low";
  if (urgency < 40) return "Low";
  if (urgency < 60) return "Moderate";
  if (urgency < 80) return "High";
  return "Severe";
}

export function filterForecasts(items: Forecast[], search: string, risk: Risk | "All"): Forecast[] {
  const q = search.trim().replace(/^ward\s*/i, "");
  return items
    .filter((f) => (risk === "All" ? true : f.risk_level === risk))
    .filter((f) => (q === "" ? true : String(f.ward).includes(q)))
    .sort((a, b) => b.urgency_score - a.urgency_score);
}

export const pct = (x: number) => `${(x * 100).toFixed(0)}%`;
export const fmt = (x: number, d = 2) => x.toFixed(d);
export function formatDate(iso: string | null): string {
  if (!iso) return "None within 7 days";
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
