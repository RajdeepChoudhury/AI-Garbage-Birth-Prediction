import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, UploadCloud } from "lucide-react";
import { apiError, uploadCsv } from "../lib/api";
import { Button, Card, ErrorNote, RiskBadge } from "../components/ui";
import { RISK_ORDER } from "../lib/utils";
import type { Risk } from "../lib/types";

const COLUMNS = "Date, Ward, Latitude, Longitude, Population, Traffic, Weather, Rainfall, Temperature, Humidity, Nearby Market Count, Nearby School Count, Restaurant Density, Collection Frequency, Complaint Count, Previous Garbage Volume, Festival Flag, Holiday Flag, Construction Flag";

export default function Upload() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const m = useMutation({
    mutationFn: uploadCsv,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["forecasts"] }); },
  });
  const tooBig = file !== null && file.size > 10 * 1024 * 1024;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Upload ward data</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Upload daily ward records as CSV. The system forecasts tomorrow for the latest date of each ward.
        </p>
      </div>
      <Card className="space-y-4">
        <div className="text-xs text-slate-500 dark:text-slate-400">Required columns: {COLUMNS}. Maximum 10 MB.</div>
        <input ref={input} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => { setFile(e.target.files?.[0] ?? null); m.reset(); }} />
        <button onClick={() => input.current?.click()} className="flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-slate-300 p-8 text-sm text-slate-500 hover:border-emerald-500 dark:border-white/20">
          <UploadCloud className="h-8 w-8" />
          {file ? `${file.name} (${(file.size / 1024).toFixed(0)} KB)` : "Choose a CSV file"}
        </button>
        {tooBig && <ErrorNote message="This file is larger than 10 MB." />}
        {m.isError && <ErrorNote message={apiError(m.error)} />}
        <Button disabled={!file || tooBig || m.isPending} onClick={() => file && m.mutate(file)} className="w-full">
          {m.isPending ? "Uploading and forecasting" : "Upload and forecast"}
        </Button>
        {m.isSuccess && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-50 p-4 text-sm dark:bg-emerald-950/30">
            <div className="flex items-center gap-2 font-medium text-emerald-700 dark:text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Forecasts created</div>
            <p className="mt-1 text-slate-600 dark:text-slate-300">{m.data.rows_read} rows read, {m.data.wards_forecast} wards forecast.</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {RISK_ORDER.filter((r) => m.data.risk_counts[r]).map((r: Risk) => (
                <span key={r} className="inline-flex items-center gap-1 text-xs"><RiskBadge risk={r} /> {m.data.risk_counts[r]}</span>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
