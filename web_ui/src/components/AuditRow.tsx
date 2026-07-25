import {
  ShieldCheck,
  Bot,
  Store,
  Lock,
  ServerCog,
  CheckCircle2,
  TriangleAlert,
  CircleAlert,
  Info,
  type LucideIcon,
} from "lucide-react";
import type { AuditEvent } from "../types";
import { relativeTime } from "../lib/format";
import { cn } from "../utils/cn";

const TYPE_ICON: Record<AuditEvent["type"], LucideIcon> = {
  compliance: ShieldCheck,
  agent: Bot,
  platform: Store,
  security: Lock,
  system: ServerCog,
  approval: CheckCircle2,
};

const SEVERITY: Record<AuditEvent["severity"], { dot: string; icon: LucideIcon; text: string }> = {
  info: { dot: "bg-slate-400", icon: Info, text: "text-slate-400" },
  success: { dot: "bg-emerald-400", icon: CheckCircle2, text: "text-emerald-400" },
  warning: { dot: "bg-amber-400", icon: TriangleAlert, text: "text-amber-400" },
  critical: { dot: "bg-rose-400", icon: CircleAlert, text: "text-rose-400" },
};

export function AuditRow({ event }: { event: AuditEvent }) {
  const Icon = TYPE_ICON[event.type] ?? Info;
  const sev = SEVERITY[event.severity];
  const SevIcon = sev.icon;
  return (
    <div className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-white/[0.02]">
      <div className="relative mt-0.5">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.04] ring-1 ring-inset ring-white/[0.06]">
          <Icon className="h-4 w-4 text-slate-300" />
        </div>
        <span className={cn("absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-[#0d1220]", sev.dot)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold text-slate-200">{event.action}</span>
          <SevIcon className={cn("h-3.5 w-3.5 shrink-0", sev.text)} />
        </div>
        <p className="truncate text-xs text-slate-400">{event.detail}</p>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
          <span className="font-medium text-slate-400">{event.actor}</span>
          <span>·</span>
          <span className="rounded bg-white/[0.04] px-1.5 py-0.5 uppercase tracking-wide">{event.type}</span>
          <span>·</span>
          <span>{relativeTime(event.ts)}</span>
        </div>
      </div>
    </div>
  );
}
