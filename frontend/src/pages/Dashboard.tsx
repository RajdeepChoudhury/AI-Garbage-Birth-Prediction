import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { Bot, Search } from "lucide-react";
import type { LatLngTuple } from "leaflet";
import { getForecasts, apiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Forecast, Risk } from "../lib/types";
import { RISK_COLOR, RISK_ORDER, filterForecasts, fmt, formatDate, pct, urgencyColor, urgencyLabel } from "../lib/utils";
import { Card, ErrorNote, inputClass, RiskBadge, Spinner, StatCard } from "../components/ui";
import RiskMap from "../components/RiskMap";

const TICK = { fill: "#94a3b8", fontSize: 12 };

export default function Dashboard() {
  const { hasRole } = useAuth();
  const { data, isLoading, error } = useQuery({ queryKey: ["forecasts"], queryFn: () => getForecasts() });
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState<Risk | "All">("All");
  const [selected, setSelected] = useState<number | null>(null);

  const all = data ?? [];
  const visible = useMemo(() => filterForecasts(all, search, risk), [all, search, risk]);
  const points = useMemo<LatLngTuple[]>(() => all.map((f) => [f.latitude, f.longitude]), [all]);
  const detail = all.find((f) => f.ward === selected) ?? null;

  if (isLoading) return <Spinner label="Loading forecasts" />;
  if (error) return <ErrorNote message={apiError(error)} />;

  if (all.length === 0) {
    return (
      <Card>
        <h1 className="text-xl font-semibold">No forecasts yet</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          {hasRole("admin", "officer")
            ? <>Upload ward data to generate forecasts. The sample file is <code>ml/data/garbage_synthetic.csv</code>. <Link className="text-emerald-700 underline dark:text-emerald-400" to="/upload">Go to upload</Link></>
            : "An officer needs to upload data before forecasts appear here."}
        </p>
      </Card>
    );
  }

  const counts = RISK_ORDER.map((r) => ({ name: r, value: all.filter((f) => f.risk_level === r).length })).filter((d) => d.value > 0);
  const top = [...all].sort((a, b) => b.urgency_score - a.urgency_score).slice(0, 10).map((f) => ({ name: `W${f.ward}`, urgency: f.urgency_score }));
  const scatter = all.map((f) => ({ ward: f.ward, volume: f.predicted_volume, hotspot: f.hotspot_probability, urgency: f.urgency_score }));
  const atRisk = all.filter((f) => f.risk_level === "High" || f.risk_level === "Critical").length;
  const avgHotspot = all.reduce((s, f) => s + f.hotspot_probability, 0) / all.length;
  const forecastDate = all.reduce((d, f) => (f.forecast_date > d ? f.forecast_date : d), all[0].forecast_date);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">City forecast</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Predicted garbage accumulation for {formatDate(forecastDate)}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Wards forecast" value={all.length} delay={0} />
        <StatCard label="High or critical" value={atRisk} hint={pct(atRisk / all.length) + " of wards"} delay={0.05} />
        <StatCard label="Avg hotspot chance" value={pct(avgHotspot)} delay={0.1} />
        <StatCard label="Highest urgency" value={`Ward ${[...all].sort((a, b) => b.urgency_score - a.urgency_score)[0].ward}`} delay={0.15} />
      </div>

      <Card className="flex flex-wrap items-center gap-3 !p-3">
        <div className="relative min-w-[180px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input aria-label="Search ward" className={inputClass + " pl-9"} placeholder="Search ward number" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select aria-label="Risk level" className={inputClass + " !w-auto"} value={risk} onChange={(e) => setRisk(e.target.value as Risk | "All")}>
          <option value="All">All risk levels</option>
          {RISK_ORDER.map((r) => <option key={r}>{r}</option>)}
        </select>
        <span className="text-sm text-slate-500 dark:text-slate-400">{visible.length} of {all.length} wards</span>
      </Card>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card className="overflow-hidden !p-2 xl:col-span-2">
          <RiskMap forecasts={visible} points={points} selected={selected} onSelect={setSelected} />
          <div className="flex flex-wrap items-center gap-3 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
            {[10, 30, 50, 70, 90].map((u) => (
              <span key={u} className="inline-flex items-center gap-1"><i className="inline-block h-3 w-3 rounded-full" style={{ background: urgencyColor(u) }} />{urgencyLabel(u)}</span>
            ))}
            <span>Circle size follows predicted volume</span>
          </div>
        </Card>

        <Card className="flex max-h-[520px] flex-col !p-0">
          <div className="border-b border-slate-200/60 p-4 text-sm font-semibold dark:border-white/10">Ward ranking by urgency</div>
          <ul className="flex-1 divide-y divide-slate-200/60 overflow-y-auto dark:divide-white/10">
            {visible.length === 0 && <li className="p-4 text-sm text-slate-500">No wards match the filters.</li>}
            {visible.map((f, i) => (
              <li key={f.ward}>
                <button onClick={() => setSelected(f.ward)}
                  className={"flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-slate-100/70 dark:hover:bg-white/5 " + (f.ward === selected ? "bg-emerald-50 dark:bg-emerald-500/10" : "")}>
                  <span className="w-5 text-xs text-slate-400">{i + 1}</span>
                  <span className="flex-1 font-medium">Ward {f.ward}</span>
                  <span className="tabular-nums text-xs text-slate-500">{f.urgency_score.toFixed(0)}</span>
                  <RiskBadge risk={f.risk_level} />
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {detail && <WardDetail f={detail} canAsk={hasRole("admin", "officer", "analyst")} />}

      <div className="grid gap-5 lg:grid-cols-3">
        <Card>
          <h2 className="mb-2 text-sm font-semibold">Risk distribution</h2>
          <div className="h-60">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={counts} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                  {counts.map((d) => <Cell key={d.name} fill={RISK_COLOR[d.name as Risk]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h2 className="mb-2 text-sm font-semibold">Top 10 wards by urgency</h2>
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={top}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b855" />
                <XAxis dataKey="name" tick={TICK} />
                <YAxis domain={[0, 100]} tick={TICK} />
                <Tooltip />
                <Bar dataKey="urgency" radius={[6, 6, 0, 0]}>
                  {top.map((d) => <Cell key={d.name} fill={urgencyColor(d.urgency)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h2 className="mb-2 text-sm font-semibold">Volume vs hotspot probability</h2>
          <div className="h-60">
            <ResponsiveContainer>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b855" />
                <XAxis type="number" dataKey="volume" name="Volume" tick={TICK} />
                <YAxis type="number" dataKey="hotspot" name="Hotspot probability" domain={[0, 1]} tick={TICK} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={scatter}>
                  {scatter.map((d) => <Cell key={d.ward} fill={urgencyColor(d.urgency)} />)}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

function WardDetail({ f, canAsk }: { f: Forecast; canAsk: boolean }) {
  const factors = f.top_factors ?? [];
  const max = Math.max(0.01, ...factors.map((x) => Math.abs(x.impact)));
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold">Ward {f.ward} <RiskBadge risk={f.risk_level} /></h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Clean: {f.recommended_cleaning_time}</p>
        </div>
        {canAsk && (
          <Link to={`/assistant?ward=${f.ward}`} className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/40 px-3 py-1.5 text-sm text-emerald-700 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10">
            <Bot className="h-4 w-4" /> Ask the assistant why
          </Link>
        )}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-5">
        {[
          ["Predicted volume", fmt(f.predicted_volume)],
          ["Hotspot probability", pct(f.hotspot_probability)],
          ["Urgency score", f.urgency_score.toFixed(0)],
          ["Confidence", pct(f.confidence)],
          ["Overflow date", formatDate(f.predicted_overflow_date)],
        ].map(([k, v]) => (
          <div key={k}><dt className="text-xs text-slate-500 dark:text-slate-400">{k}</dt><dd className="font-medium">{v}</dd></div>
        ))}
      </dl>
      {factors.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-sm font-semibold">What drives this forecast</h3>
          <ul className="space-y-1.5">
            {factors.map((x) => (
              <li key={x.feature} className="flex items-center gap-3 text-xs">
                <span className="w-44 shrink-0 truncate">{x.feature} = {x.value}</span>
                <div className="relative h-3 flex-1 rounded bg-slate-200/70 dark:bg-white/10">
                  <div className="absolute top-0 h-3 rounded" style={{
                    width: `${(Math.abs(x.impact) / max) * 50}%`,
                    left: x.impact >= 0 ? "50%" : `${50 - (Math.abs(x.impact) / max) * 50}%`,
                    background: x.impact >= 0 ? "#dc2626" : "#22c55e",
                  }} />
                </div>
                <span className="w-14 text-right tabular-nums">{x.impact >= 0 ? "+" : ""}{x.impact.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Red pushes volume up, green pushes it down (SHAP, in volume units).</p>
        </div>
      )}
    </Card>
  );
}
