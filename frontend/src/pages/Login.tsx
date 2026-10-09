import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { Recycle } from "lucide-react";
import { useAuth } from "../lib/auth";
import { apiError } from "../lib/api";
import { Button, Card, ErrorNote, inputClass } from "../components/ui";

export default function Login() {
  const { user, signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await (mode === "login" ? signIn(email, password) : signUp(email, password));
    } catch (err) {
      setError(apiError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-sky-100 via-white to-emerald-100 p-4 dark:from-slate-950 dark:via-slate-900 dark:to-emerald-950">
      <Card className="w-full max-w-sm">
        <div className="mb-5 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
          <Recycle className="h-6 w-6 text-emerald-600" /> Garbage Birth Prediction
        </div>
        <form onSubmit={submit} className="space-y-3">
          <label className="block text-sm text-slate-600 dark:text-slate-300">
            Email
            <input className={inputClass + " mt-1"} type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="block text-sm text-slate-600 dark:text-slate-300">
            Password
            <input className={inputClass + " mt-1"} type="password" required minLength={mode === "register" ? 8 : 1} maxLength={72}
              autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {mode === "register" && <p className="text-xs text-slate-500 dark:text-slate-400">At least 8 characters. Public accounts are citizen accounts. Staff roles are assigned by an admin.</p>}
          {error && <ErrorNote message={error} />}
          <Button type="submit" disabled={busy} className="w-full">{busy ? "Please wait" : mode === "login" ? "Sign in" : "Create account"}</Button>
        </form>
        <button className="mt-4 w-full text-center text-sm text-emerald-700 hover:underline dark:text-emerald-400"
          onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "Create a citizen account" : "I already have an account"}
        </button>
      </Card>
    </div>
  );
}
