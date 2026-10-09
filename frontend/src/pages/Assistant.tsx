import { useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Bot, Send, User as UserIcon } from "lucide-react";
import { apiError, askAssistant, dailyPlan, executiveReport } from "../lib/api";
import { Button, Card, ErrorNote, inputClass, Spinner } from "../components/ui";

interface Msg { role: "user" | "assistant"; text: string }

const QUICK: { label: string; kind: "ask" | "plan" | "report"; question?: string }[] = [
  { label: "Explain today's predictions", kind: "ask", question: "Explain today's predictions" },
  { label: "Which wards need extra trucks tomorrow?", kind: "ask", question: "Which wards require additional trucks tomorrow?" },
  { label: "Preventive recommendations", kind: "ask", question: "Provide preventive recommendations" },
  { label: "Today's cleaning schedule", kind: "plan" },
  { label: "Executive report", kind: "report" },
];

export default function Assistant() {
  const [params] = useSearchParams();
  const ward = params.get("ward");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState(ward && /^\d+$/.test(ward) ? `Why does Ward ${ward} have this forecast?` : "");
  const [trucks, setTrucks] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const truckCount = trucks.trim() === "" ? undefined : Math.max(0, Math.floor(Number(trucks)));

  async function run(label: string, call: () => Promise<{ answer: string }>) {
    setError(null);
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: label }]);
    try {
      const r = await call();
      setMessages((m) => [...m, { role: "assistant", text: r.answer }]);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }

  function send(e: FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (q.length < 3 || busy) return;
    setInput("");
    void run(q, () => askAssistant(q, truckCount));
  }

  function quick(q: (typeof QUICK)[number]) {
    if (busy) return;
    const call = q.kind === "plan" ? () => dailyPlan(truckCount) : q.kind === "report" ? () => executiveReport(truckCount) : () => askAssistant(q.question!, truckCount);
    void run(q.label, call);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Municipal assistant</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Answers use the latest stored forecasts. Check important decisions before acting.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {QUICK.map((q) => (
          <button key={q.label} onClick={() => quick(q)} disabled={busy}
            className="rounded-full border border-emerald-600/40 px-3 py-1 text-xs text-emerald-800 hover:bg-emerald-50 disabled:opacity-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10">
            {q.label}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          Trucks available
          <input type="number" min={0} max={10000} value={trucks} onChange={(e) => setTrucks(e.target.value)} placeholder="optional" className={inputClass + " !w-24 !py-1"} />
        </label>
      </div>

      <Card className="flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">Ask a question or pick a quick action above, for example "Why is Ward 17 predicted as high risk?".</p>}
        {messages.map((m, i) => (
          <div key={i} className={"flex gap-3 " + (m.role === "user" ? "justify-end" : "")}>
            {m.role === "assistant" && <Bot className="mt-1 h-5 w-5 shrink-0 text-emerald-600" />}
            <div className={"max-w-[85%] rounded-2xl px-4 py-2 text-sm " + (m.role === "user" ? "bg-emerald-600 text-white" : "bg-slate-100/80 dark:bg-white/5")}>
              {m.role === "assistant" ? <div className="md"><ReactMarkdown>{m.text}</ReactMarkdown></div> : m.text}
            </div>
            {m.role === "user" && <UserIcon className="mt-1 h-5 w-5 shrink-0 text-slate-400" />}
          </div>
        ))}
        {busy && <Spinner label="Thinking" />}
        {error && <ErrorNote message={error} />}
        <div ref={end} />
      </Card>

      <form onSubmit={send} className="flex gap-2">
        <input className={inputClass} placeholder="Ask about wards, trucks, or risks" value={input} maxLength={1000} onChange={(e) => setInput(e.target.value)} aria-label="Question" />
        <Button type="submit" disabled={busy || input.trim().length < 3} aria-label="Send"><Send className="h-4 w-4" /></Button>
      </form>
    </div>
  );
}
