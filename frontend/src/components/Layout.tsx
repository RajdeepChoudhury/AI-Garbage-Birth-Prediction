import { NavLink, Outlet } from "react-router-dom";
import { Bot, Brain, LayoutDashboard, LogOut, Moon, Recycle, Sun, Upload } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { cn } from "../lib/utils";

export default function Layout() {
  const { user, signOut, hasRole } = useAuth();
  const { theme, toggle } = useTheme();

  const links = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, show: true, end: true },
    { to: "/models", label: "Models", icon: Brain, show: true },
    { to: "/assistant", label: "Assistant", icon: Bot, show: hasRole("admin", "officer", "analyst") },
    { to: "/upload", label: "Data upload", icon: Upload, show: hasRole("admin", "officer") },
  ].filter((l) => l.show);

  return (
    <div className="flex min-h-full flex-col bg-gradient-to-br from-sky-50 via-white to-emerald-50 text-slate-800 md:flex-row dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 dark:text-slate-100">
      <aside className="flex shrink-0 items-center gap-3 border-b border-white/40 bg-white/60 p-3 backdrop-blur-md md:w-60 md:flex-col md:items-stretch md:border-b-0 md:border-r md:p-5 dark:border-white/10 dark:bg-slate-900/50">
        <div className="flex items-center gap-2 font-semibold">
          <Recycle className="h-6 w-6 text-emerald-600" />
          <span className="hidden sm:inline">Garbage Birth Prediction</span>
        </div>
        <nav className="flex flex-1 gap-1 overflow-x-auto md:mt-6 md:flex-none md:flex-col">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2 text-sm transition",
                  isActive
                    ? "bg-emerald-600 text-white"
                    : "text-slate-600 hover:bg-slate-200/60 dark:text-slate-300 dark:hover:bg-white/10",
                )
              }
            >
              <Icon className="h-4 w-4" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2 md:mt-auto md:flex-col md:items-stretch">
          <div className="hidden truncate text-xs text-slate-500 md:block dark:text-slate-400">
            {user?.email}
            <div className="capitalize">{user?.role}</div>
          </div>
          <button onClick={toggle} aria-label="Toggle theme" className="rounded-xl border border-slate-300/70 p-2 hover:bg-slate-200/60 dark:border-white/15 dark:hover:bg-white/10">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <button onClick={signOut} aria-label="Sign out" className="flex items-center justify-center gap-2 rounded-xl border border-slate-300/70 p-2 text-sm hover:bg-slate-200/60 dark:border-white/15 dark:hover:bg-white/10">
            <LogOut className="h-4 w-4" /> <span className="hidden md:inline">Sign out</span>
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
