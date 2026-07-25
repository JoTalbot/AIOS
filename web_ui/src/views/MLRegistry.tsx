import { useEffect, useState } from "react";
import { Cpu, ArrowUp, ArrowDown, Archive, Hash, Boxes, TrendingUp } from "lucide-react";
import { Card, PanelHeader, Badge, Progress } from "../components/ui/primitives";
import { apiGet, apiPost } from "../lib/api";
import type { MLModelInfo } from "../types";

const STAGE_TONE: Record<MLModelInfo["stage"], any> = {
  production: "emerald",
  staging: "amber",
  archived: "slate",
};

export function MLRegistry() {
  const [models, setModels] = useState<MLModelInfo[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = () => apiGet<any[]>("api/models")
    .then((rows) => setModels(rows.map((m) => ({ ...m, size_mb: Number(m.size_mb || 0) }))))
    .catch((e) => setMessage(e instanceof Error ? e.message : String(e)));

  useEffect(() => { load(); }, []);

  const cycle = async (name: string) => {
    const model = models.find((m) => m.name === name);
    if (!model) return;
    const stage: MLModelInfo["stage"] = model.stage === "staging" ? "production" : model.stage === "production" ? "archived" : "staging";
    setBusy(name);
    setMessage(null);
    try {
      await apiPost(`api/models/${encodeURIComponent(name)}/stage`, { stage });
      setModels((prev) => prev.map((m) => m.name === name ? { ...m, stage } : m));
      setMessage(`${name} moved to ${stage}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const prod = models.filter((m) => m.stage === "production").length;
  const staging = models.filter((m) => m.stage === "staging").length;
  const archived = models.filter((m) => m.stage === "archived").length;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Registered models", value: models.length, icon: Boxes, tone: "indigo" },
          { label: "In production", value: prod, icon: TrendingUp, tone: "emerald" },
          { label: "Staging", value: staging, icon: Cpu, tone: "amber" },
          { label: "Archived", value: archived, icon: Archive, tone: "slate" },
        ].map((s) => (
          <Card key={s.label} className="flex items-center gap-3 p-4">
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

      {message && <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-xs text-slate-300">{message}</div>}
      <Card>
        <PanelHeader icon={<Cpu className="h-[18px] w-[18px]" />} title="Model Registry" subtitle="Live versioned, SHA-pinned artifacts · persistent stages" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {models.map((m) => (
            <div key={m.name} className="card-hover glass rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{m.name}</span>
                    <span className="font-mono text-[11px] text-slate-500">{m.version}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <Badge tone={STAGE_TONE[m.stage]}>{m.stage}</Badge>
                    <Badge tone="slate">{m.framework}</Badge>
                    <span className="inline-flex items-center gap-1 text-[10px] text-slate-500"><Hash className="h-2.5 w-2.5" />{m.sha256}</span>
                  </div>
                </div>
                <span className="shrink-0 rounded-lg bg-white/[0.04] px-2 py-1 text-[11px] tabular text-slate-400">{m.size_mb} MB</span>
              </div>

              <div className="mt-4 space-y-2.5">
                {Object.entries(m.eval_metrics).map(([k, v]) => {
                  const pct = k.toLowerCase().includes("latency") || k.toLowerCase().includes("mae")
                    ? null
                    : Math.min(100, v * 100);
                  return (
                    <div key={k}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">{k}</span>
                        <span className="font-semibold tabular text-slate-200">{v}</span>
                      </div>
                      {pct !== null && <Progress value={pct} tone="indigo" />}
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 flex items-center justify-end gap-2 border-t border-white/[0.05] pt-3">
                <button disabled={busy === m.name} onClick={() => cycle(m.name)} className="inline-flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-2.5 py-1.5 text-[11px] font-medium text-slate-300 ring-1 ring-inset ring-white/10 hover:bg-white/[0.08] disabled:opacity-50">
                  {m.stage === "staging" ? <><ArrowUp className="h-3 w-3 text-emerald-400" /> Promote</> : m.stage === "production" ? <><ArrowDown className="h-3 w-3 text-amber-400" /> Archive</> : <><ArrowUp className="h-3 w-3 text-cyan-400" /> Re-stage</>}
                </button>
              </div>
            </div>
          ))}
          {!models.length && <div className="col-span-full py-12 text-center text-sm text-slate-500">Loading live model registry…</div>}
        </div>
      </Card>
    </div>
  );
}
