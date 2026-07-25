import { useMemo, useState } from "react";
import { ScrollText, Search, CircleAlert, TriangleAlert, CheckCircle2, Info, Download } from "lucide-react";
import { Card, PanelHeader, Segmented } from "../components/ui/primitives";
import { AuditRow } from "../components/AuditRow";
import type { UseLiveData } from "../data/useLiveData";
import type { Severity } from "../types";

const TYPE_LABELS: Record<string, string> = {
  compliance: "Compliance",
  agent: "Agent",
  platform: "Platform",
  security: "Security",
  system: "System",
  approval: "Approval",
};

export function Audit({ data }: { data: UseLiveData }) {
  const [q, setQ] = useState("");
  const [sev, setSev] = useState<"all" | Severity>("all");
  const [type, setType] = useState("all");

  const events = data.audit;
  const counts = useMemo(() => {
    const c: Record<string, number> = { critical: 0, warning: 0, success: 0, info: 0 };
    events.forEach((e) => (c[e.severity] = (c[e.severity] ?? 0) + 1));
    return c;
  }, [events]);

  const filtered = events.filter(
    (e) =>
      (sev === "all" || e.severity === sev) &&
      (type === "all" || e.type === type) &&
      (q === "" || e.action.toLowerCase().includes(q.toLowerCase()) || e.detail.toLowerCase().includes(q.toLowerCase()) || e.actor.toLowerCase().includes(q.toLowerCase()))
  );

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `aios-audit-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const sevCard = [
    { key: "critical", label: "Critical", value: counts.critical ?? 0, icon: CircleAlert, tone: "rose" },
    { key: "warning", label: "Warnings", value: counts.warning ?? 0, icon: TriangleAlert, tone: "amber" },
    { key: "success", label: "Success", value: counts.success ?? 0, icon: CheckCircle2, tone: "emerald" },
    { key: "info", label: "Info", value: counts.info ?? 0, icon: Info, tone: "indigo" },
  ] as const;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {sevCard.map((s) => (
          <Card key={s.key} className="flex items-center gap-3 p-4">
            <div className={`grid h-10 w-10 place-items-center rounded-xl bg-${s.tone}-500/10 text-${s.tone}-300`}>
              <s.icon className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xl font-extrabold tabular text-white">{s.value}</div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">{s.label}</div>
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <PanelHeader
            icon={<ScrollText className="h-[18px] w-[18px]" />}
            title="Immutable Audit Stream"
            subtitle="Tamper-evident · OpenTelemetry-traced"
            className="mb-0"
          />
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={exportJson} className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-300 hover:border-white/15">
              <Download className="h-3.5 w-3.5" /> Export JSON
            </button>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search events…"
                className="w-44 rounded-lg border border-white/[0.08] bg-white/[0.03] py-2 pl-9 pr-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-400/50"
              />
            </div>
            <Segmented
              size="sm"
              value={sev}
              onChange={setSev}
              options={[
                { value: "all", label: "All" },
                { value: "critical", label: "Crit" },
                { value: "warning", label: "Warn" },
                { value: "success", label: "OK" },
              ]}
            />
          </div>
        </div>

        <div className="mb-3 flex flex-wrap gap-1.5">
          <Chip active={type === "all"} onClick={() => setType("all")} label="All types" />
          {Object.entries(TYPE_LABELS).map(([k, label]) => (
            <Chip key={k} active={type === k} onClick={() => setType(k)} label={label} />
          ))}
        </div>

        <div className="-mx-5 -mb-5 max-h-[560px] divide-y divide-white/[0.04] overflow-y-auto">
          {filtered.map((e) => (
            <AuditRow key={e.id} event={e} />
          ))}
          {filtered.length === 0 && <div className="py-12 text-center text-sm text-slate-500">No events match your filters.</div>}
        </div>
      </Card>
    </div>
  );
}

function Chip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${active ? "bg-indigo-500/90 text-white" : "bg-white/[0.04] text-slate-400 hover:text-slate-200"}`}
    >
      {label}
    </button>
  );
}
