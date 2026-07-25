import { Menu, Search, Bell, Activity, Wifi, WifiOff, ChevronDown } from "lucide-react";
import { StatusPill } from "../ui/primitives";
import { cn } from "../../utils/cn";
import type { HealthStatus } from "../../types";

export function Topbar({
  title,
  subtitle,
  onMenu,
  onOpenCommand,
  wsConnected,
  health,
  clock,
  tasksPerMin,
  notifications,
}: {
  title: string;
  subtitle: string;
  onMenu: () => void;
  onOpenCommand: () => void;
  wsConnected: boolean;
  health: HealthStatus;
  clock: string;
  tasksPerMin: number;
  notifications: number;
}) {
  const healthTone = health === "ok" ? "emerald" : health === "degraded" ? "amber" : "rose";
  const healthLabel = health === "ok" ? "All systems operational" : health === "degraded" ? "Degraded performance" : "Critical issue";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-white/[0.06] bg-[#070b15]/80 px-4 backdrop-blur-xl sm:px-6">
      <button
        onClick={onMenu}
        className="grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:bg-white/5 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-bold tracking-tight text-white sm:text-lg">{title}</h1>
        <p className="hidden truncate text-xs text-slate-500 sm:block">{subtitle}</p>
      </div>

      {/* Search trigger */}
      <button
        onClick={onOpenCommand}
        className="group hidden items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-500 transition-colors hover:border-white/15 hover:text-slate-300 md:flex"
      >
        <Search className="h-4 w-4" />
        <span className="hidden lg:inline">Search…</span>
        <kbd className="ml-2 hidden rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-400 lg:inline">⌘K</kbd>
      </button>

      {/* Live ticker */}
      <div className="hidden items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 xl:flex">
        <Activity className="h-4 w-4 text-emerald-400" />
        <div className="leading-none">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">Throughput</div>
          <div className="text-sm font-bold tabular text-white">
            {tasksPerMin}<span className="ml-1 text-[10px] font-medium text-slate-500">tasks/min</span>
          </div>
        </div>
      </div>

      {/* Clock */}
      <div className="hidden items-center rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 font-mono text-sm tabular text-slate-300 sm:flex">
        {clock}
      </div>

      {/* WS + health */}
      <div className="hidden items-center gap-2 sm:flex">
        <StatusPill tone={wsConnected ? "emerald" : "slate"} label={wsConnected ? "Live" : "Connecting"} pulse={wsConnected} />
      </div>

      <button className="relative grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:bg-white/5">
        <Bell className="h-[18px] w-[18px]" />
        {notifications > 0 && (
          <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">
            {notifications > 9 ? "9+" : notifications}
          </span>
        )}
      </button>

      <div className="flex items-center gap-1 rounded-lg py-1 pl-1 pr-2 hover:bg-white/5">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-xs font-bold text-white">
          OP
        </div>
        <ChevronDown className="hidden h-4 w-4 text-slate-500 sm:block" />
      </div>

      {/* Mobile compact status */}
      <div className="flex items-center sm:hidden">
        {wsConnected ? <Wifi className="h-4 w-4 text-emerald-400" /> : <WifiOff className="h-4 w-4 text-slate-500 blink" />}
      </div>

      <div className={cn("hidden xl:block")}>
        <StatusPill tone={healthTone} label={healthLabel} pulse={health === "ok"} />
      </div>
    </header>
  );
}
