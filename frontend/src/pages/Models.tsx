import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Trophy } from "lucide-react";
import { apiError, getMetrics } from "../lib/api";
import { Card, ErrorNote, Spinner } from "../components/ui";

const TICK = { fill: "#94a3b8", fontSize: 12 };
const th = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400";

export default function Models() {
  const { data, isLoading, error } = useQuery({ queryKey: ["metrics"], queryFn: getMetrics });
  if (isLoading) return <Spinner label="Loading model metrics" />;
  if (error || !data) return <ErrorNote message={apiError(error)} />;

  const reg = Object.entries(data.regression);
  const cls = Object.entries(data.classification);
  const rmse = reg.map(([name, m]) => ({ name, RMSE: Number(m.RMSE.toFixed(4)) }));
  const importance = Object.entries(data.feature_importance).slice(0, 10).map(([name, v]) => ({ name, value: v }));
  const Best = () => <Trophy className="ml-1 inline h-3.5 w-3.5 text-amber-500" aria-label="best" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Model comparison</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Evaluated on the most recent 20 percent of dates, so scores reflect forecasting forward in time.</p>
      </div>
      <div className="rounded-xl border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-950/40 dark:text-amber-200" role="note">
        {data.data_note}
      </div>

      <Card>
        <h2 className="mb-2 text-sm font-semibold">Volume forecast (regression)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr><th className={th}>Model</th><th className={th}>MAE</th><th className={th}>RMSE</th><th className={th}>R2</th><th className={th}>Train s</th></tr></thead>
            <tbody className="divide-y divide-slate-200/60 dark:divide-white/10">
              {reg.map(([name, m]) => (
                <tr key={name}>
                  <td className="px-3 py-2 font-medium">{name}{name === data.best.regressor && <Best />}</td>
                  <td className="px-3 py-2 tabular-nums">{m.MAE.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m.RMSE.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m.R2.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m["Train Seconds"]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold">Risk level (classification, macro averaged)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr><th className={th}>Model</th><th className={th}>Precision</th><th className={th}>Recall</th><th className={th}>F1</th><th className={th}>F1 high and critical</th><th className={th}>Train s</th></tr></thead>
            <tbody className="divide-y divide-slate-200/60 dark:divide-white/10">
              {cls.map(([name, m]) => (
                <tr key={name}>
                  <td className="px-3 py-2 font-medium">{name}{name === data.best.classifier && <Best />}</td>
                  <td className="px-3 py-2 tabular-nums">{m.Precision.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m.Recall.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m.F1.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m["F1 High and Critical"].toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{m["Train Seconds"]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-sm font-semibold">RMSE by model (lower is better)</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={rmse}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b855" />
                <XAxis dataKey="name" tick={TICK} />
                <YAxis tick={TICK} domain={[0, "auto"]} />
                <Tooltip />
                <Bar dataKey="RMSE" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h2 className="mb-2 text-sm font-semibold">Top features by mean SHAP impact</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={importance} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b855" />
                <XAxis type="number" tick={TICK} />
                <YAxis type="category" dataKey="name" tick={TICK} width={120} />
                <Tooltip />
                <Bar dataKey="value" fill="#0ea5e9" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {data.not_yet_evaluated.length > 0 && (
        <p className="text-sm text-slate-500 dark:text-slate-400">Not yet evaluated: {data.not_yet_evaluated.join(", ")}.</p>
      )}
    </div>
  );
}
