import React from "react";
import { ArrowUpRight, ArrowDownRight, type LucideIcon } from "lucide-react";
import { Sparkline } from "./charts";
import { cn } from "../../utils/cn";

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  tone = "indigo",
  spark,
  delta,
  className,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  icon?: LucideIcon;
  tone?: "indigo" | "cyan" | "emerald" | "amber" | "rose" | "violet";
  spark?: { data: number[]; color?: string };
  delta?: number;
  className?: string;
}) {
  const tones: Record<string, { bg: string; text: string; spark: string }> = {
    indigo: { bg: "bg-indigo-500/10 text-indigo-300 ring-indigo-400/20", text: "text-indigo-300", spark: "#818cf8" },
    cyan: { bg: "bg-cyan-500/10 text-cyan-300 ring-cyan-400/20", text: "text-cyan-300", spark: "#22d3ee" },
    emerald: { bg: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20", text: "text-emerald-300", spark: "#34d399" },
    amber: { bg: "bg-amber-500/10 text-amber-300 ring-amber-400/20", text: "text-amber-300", spark: "#fbbf24" },
    rose: { bg: "bg-rose-500/10 text-rose-300 ring-rose-400/20", text: "text-rose-300", spark: "#fb7185" },
    violet: { bg: "bg-violet-500/10 text-violet-300 ring-violet-400/20", text: "text-violet-300", spark: "#a78bfa" },
  };
  const t = tones[tone];
  return (
    <div className={cn("card-hover glass relative overflow-hidden rounded-2xl p-4", className)}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {Icon && (
              <div className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-lg ring-1 ring-inset", t.bg)}>
                <Icon className="h-4 w-4" />
              </div>
            )}
            <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</span>
          </div>
          <div className="mt-2.5 text-2xl font-extrabold tabular tracking-tight text-white">{value}</div>
          {sub && <div className="mt-0.5 truncate text-xs text-slate-500">{sub}</div>}
        </div>
        {spark && (
          <div className="shrink-0">
            <Sparkline data={spark.data} color={spark.color ?? t.spark} width={84} height={32} />
          </div>
        )}
      </div>
      {delta !== undefined && (
        <div className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold">
          {delta >= 0 ? (
            <ArrowUpRight className="h-3 w-3 text-emerald-400" />
          ) : (
            <ArrowDownRight className="h-3 w-3 text-rose-400" />
          )}
          <span className={delta >= 0 ? "text-emerald-400" : "text-rose-400"}>{Math.abs(delta).toFixed(1)}%</span>
          <span className="text-slate-500">vs last hour</span>
        </div>
      )}
    </div>
  );
}
