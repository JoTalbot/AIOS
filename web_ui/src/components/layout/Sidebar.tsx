import { Hexagon, ChevronsLeft, X, ExternalLink } from "lucide-react";
import { NAV_GROUPS, type ViewId } from "./nav";
import { Dot } from "../ui/primitives";
import { cn } from "../../utils/cn";
import type { HealthStatus } from "../../types";

export function Sidebar({
  active,
  onNavigate,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  health,
  version,
  safety,
}: {
  active: ViewId;
  onNavigate: (id: ViewId) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  health: HealthStatus;
  version: string;
  safety: number;
}) {
  const healthTone = health === "ok" ? "emerald" : health === "degraded" ? "amber" : "rose";
  const healthLabel = health === "ok" ? "Operational" : health === "degraded" ? "Degraded" : "Critical";

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onCloseMobile} />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[0.06] bg-[#080c17]/95 backdrop-blur-xl transition-all duration-300",
          collapsed ? "w-[76px]" : "w-[256px]",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-white/[0.06] px-4">
          <div className="relative grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 shadow-lg shadow-indigo-900/40">
            <Hexagon className="h-5 w-5 text-white" strokeWidth={2.4} />
            <span className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-[15px] font-extrabold leading-tight tracking-tight text-white">AIOS</div>
              <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">Control Plane</div>
            </div>
          )}
          <button
            onClick={onCloseMobile}
            className="ml-auto grid h-8 w-8 place-items-center rounded-lg text-slate-400 hover:bg-white/5 lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-5">
              {!collapsed && (
                <div className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                  {group.label}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = active === item.id;
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        onNavigate(item.id);
                        onCloseMobile();
                      }}
                      title={collapsed ? item.label : undefined}
                      className={cn(
                        "group relative flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-sm transition-all",
                        collapsed && "justify-center px-0",
                        isActive
                          ? "bg-gradient-to-r from-indigo-500/20 to-indigo-500/5 text-white ring-1 ring-inset ring-indigo-400/30"
                          : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100"
                      )}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-gradient-to-b from-indigo-400 to-cyan-400" />
                      )}
                      <Icon
                        className={cn(
                          "h-[18px] w-[18px] shrink-0 transition-colors",
                          isActive ? "text-indigo-300" : "text-slate-500 group-hover:text-slate-300"
                        )}
                        strokeWidth={2}
                      />
                      {!collapsed && <span className="truncate font-medium">{item.label}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-white/[0.06] p-3">
          {!collapsed ? (
            <>
              <div className="mb-2 flex items-center justify-between rounded-xl bg-white/[0.03] px-3 py-2.5 ring-1 ring-inset ring-white/[0.06]">
                <div className="flex items-center gap-2">
                  <Dot tone={healthTone} pulse />
                  <div className="leading-tight">
                    <div className="text-xs font-semibold text-slate-200">{healthLabel}</div>
                    <div className="text-[10px] text-slate-500">Safety {(safety * 100).toFixed(1)}%</div>
                  </div>
                </div>
                <span className="rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                  v{version}
                </span>
              </div>
              <div className="flex items-center justify-between px-1">
                <a
                  href="https://github.com/JoTalbot/AIOS"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] text-slate-500 transition-colors hover:text-slate-300"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Repository
                </a>
                <button
                  onClick={onToggleCollapse}
                  className="hidden items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-slate-500 hover:bg-white/5 hover:text-slate-300 lg:inline-flex"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" /> Collapse
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={onToggleCollapse}
              className="mx-auto grid h-9 w-9 place-items-center rounded-lg text-slate-500 hover:bg-white/5 hover:text-slate-300"
              title="Expand"
            >
              <ChevronsLeft className="h-4 w-4 rotate-180" />
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
