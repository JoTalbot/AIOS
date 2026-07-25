import React from "react";
import { cn } from "../../utils/cn";

/* ---------------------------------- Card ---------------------------------- */
export function Card({
  className,
  children,
  hover,
  strong,
}: {
  className?: string;
  children: React.ReactNode;
  hover?: boolean;
  strong?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl p-5",
        strong ? "glass-strong" : "glass",
        hover && "card-hover",
        className
      )}
    >
      {children}
    </div>
  );
}

export function PanelHeader({
  title,
  subtitle,
  icon,
  action,
  className,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-start justify-between gap-3", className)}>
      <div className="flex items-center gap-3 min-w-0">
        {icon && (
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/[0.04] text-indigo-300 ring-1 ring-white/10">
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-100">{title}</h3>
          {subtitle && <p className="truncate text-xs text-slate-400">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/* --------------------------------- Badge ---------------------------------- */
const BADGE_TONES: Record<string, string> = {
  indigo: "bg-indigo-500/15 text-indigo-300 ring-indigo-400/30",
  cyan: "bg-cyan-500/15 text-cyan-300 ring-cyan-400/30",
  emerald: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
  amber: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
  rose: "bg-rose-500/15 text-rose-300 ring-rose-400/30",
  violet: "bg-violet-500/15 text-violet-300 ring-violet-400/30",
  slate: "bg-slate-500/15 text-slate-300 ring-slate-400/30",
};

export function Badge({
  children,
  tone = "slate",
  className,
}: {
  children: React.ReactNode;
  tone?: keyof typeof BADGE_TONES;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
        BADGE_TONES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

/* ---------------------------------- Dot ----------------------------------- */
export function Dot({
  tone = "emerald",
  pulse,
  className,
}: {
  tone?: "emerald" | "amber" | "rose" | "slate" | "cyan" | "indigo";
  pulse?: boolean;
  className?: string;
}) {
  const colors: Record<string, string> = {
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    rose: "bg-rose-400",
    slate: "bg-slate-500",
    cyan: "bg-cyan-400",
    indigo: "bg-indigo-400",
  };
  const ring: Record<string, string> = {
    emerald: "pulse-dot",
    amber: "pulse-dot-amber",
    rose: "",
    slate: "",
    cyan: "",
    indigo: "",
  };
  return <span className={cn("inline-block h-2 w-2 rounded-full", colors[tone], pulse && ring[tone], className)} />;
}

export function StatusPill({
  tone = "slate",
  label,
  pulse,
}: {
  tone?: "emerald" | "amber" | "rose" | "slate" | "cyan" | "indigo";
  label: string;
  pulse?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium text-slate-300 ring-1 ring-inset ring-white/10"
      )}
    >
      <Dot tone={tone} pulse={pulse} />
      {label}
    </span>
  );
}

/* ------------------------------- Progress --------------------------------- */
export function Progress({
  value,
  tone = "indigo",
  className,
}: {
  value: number;
  tone?: "indigo" | "emerald" | "amber" | "rose" | "cyan" | "violet";
  className?: string;
}) {
  const tones: Record<string, string> = {
    indigo: "from-indigo-500 to-indigo-400",
    emerald: "from-emerald-500 to-emerald-400",
    amber: "from-amber-500 to-amber-400",
    rose: "from-rose-500 to-rose-400",
    cyan: "from-cyan-500 to-cyan-400",
    violet: "from-violet-500 to-violet-400",
  };
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]", className)}>
      <div
        className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-500", tones[tone])}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

/* ----------------------------- Segmented tabs ----------------------------- */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  size = "md",
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  size?: "sm" | "md";
}) {
  return (
    <div className="inline-flex items-center gap-1 rounded-xl bg-white/[0.04] p-1 ring-1 ring-inset ring-white/10">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-lg font-medium transition-all",
            size === "sm" ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs",
            value === o.value
              ? "bg-indigo-500/90 text-white shadow-sm shadow-indigo-900/40"
              : "text-slate-400 hover:text-slate-200"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------- IconButton ------------------------------- */
export function IconButton({
  children,
  onClick,
  active,
  tone = "slate",
  title,
  disabled,
  className,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
  tone?: "slate" | "emerald" | "amber" | "indigo" | "rose";
  title?: string;
  disabled?: boolean;
  className?: string;
}) {
  const tones: Record<string, string> = {
    slate: "ring-white/10 text-slate-300 hover:bg-white/[0.06] hover:text-white",
    emerald: "bg-emerald-500/90 text-white hover:bg-emerald-500",
    amber: "bg-amber-500/90 text-white hover:bg-amber-500",
    indigo: "bg-indigo-500/90 text-white hover:bg-indigo-500",
    rose: "bg-rose-500/90 text-white hover:bg-rose-500",
  };
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        active ? tones[tone] : "bg-white/[0.03] " + tones.slate,
        className
      )}
    >
      {children}
    </button>
  );
}
