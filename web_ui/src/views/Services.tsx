import { useEffect, useState } from "react";
import { ServerCog, Cpu, MemoryStick, Power, RotateCw, Play, Square, Activity, Clock, AlertTriangle } from "lucide-react";
import { Card, PanelHeader, Progress, IconButton, StatusPill } from "../components/ui/primitives";
import { apiPost } from "../lib/api";
import { cn } from "../utils/cn";
import type { ServiceInfo, ServiceState } from "../types";
import type { UseLiveData } from "../data/useLiveData";

export function Services({ data }: { data: UseLiveData }) {
  const [services, setServices] = useState<ServiceInfo[]>(data.services);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => setServices(data.services), [data.services]);

  const act = async (name: string, action: "start" | "stop" | "restart") => {
    if (name === "emulator") return;
    setBusy((b) => ({ ...b, [name]: true }));
    setMessage(null);
    try {
      const result = await apiPost<{ ok: boolean; error?: string }>(`api/services/${encodeURIComponent(name)}/action`, { action });
      if (!result.ok) throw new Error(result.error || `${action} failed`);
      setMessage(`${name}: ${action} command accepted`);
      window.setTimeout(() => data.refresh(), 1200);
    } catch (error) {
      setMessage(`${name}: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      window.setTimeout(() => setBusy((b) => ({ ...b, [name]: false })), 1000);
    }
  };

  const restartAll = async () => {
    if (!window.confirm("Restart all AIOS services? The dashboard connection can briefly drop.")) return;
    const ordered = services.filter((s) => s.name !== "emulator" && s.name !== "aios-dash");
    for (const service of ordered) await act(service.name, "restart");
    if (services.some((s) => s.name === "aios-dash")) await act("aios-dash", "restart");
  };

  const active = services.filter((s) => s.active).length;
  const totalCpu = services.reduce((a, s) => a + s.cpu, 0);
  const totalMem = services.reduce((a, s) => a + s.mem, 0);
  const stateTone: Record<ServiceState, any> = { active: "emerald", activating: "amber", failed: "rose", inactive: "slate" };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Services", value: services.length, icon: ServerCog, tone: "indigo" },
          { label: "Active", value: `${active}/${services.length}`, icon: Activity, tone: "emerald" },
          { label: "Total CPU", value: `${totalCpu}%`, icon: Cpu, tone: "amber" },
          { label: "Memory", value: totalMem ? `${(totalMem / 1024).toFixed(2)} GB` : "n/a", icon: MemoryStick, tone: "cyan" },
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

      {message && (
        <div className="flex items-center gap-2 rounded-xl border border-indigo-400/20 bg-indigo-500/10 px-4 py-3 text-xs text-indigo-200">
          <AlertTriangle className="h-4 w-4" /> {message}
        </div>
      )}

      <Card>
        <PanelHeader
          icon={<ServerCog className="h-[18px] w-[18px]" />}
          title="System Services"
          subtitle="Live systemd units · start / stop / restart"
          action={
            <button onClick={restartAll} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-500/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500">
              <RotateCw className="h-3.5 w-3.5" /> Restart all
            </button>
          }
        />
        <div className="space-y-2">
          <div className="hidden grid-cols-12 gap-3 px-4 text-[10px] font-semibold uppercase tracking-wide text-slate-500 md:grid">
            <div className="col-span-4">Service</div><div className="col-span-1">Port</div><div className="col-span-2">Status</div>
            <div className="col-span-2">CPU</div><div className="col-span-1">Mem</div><div className="col-span-2 text-right">Actions</div>
          </div>
          {services.map((s) => {
            const controllable = s.name !== "emulator";
            return (
              <div key={s.name} className="grid grid-cols-2 items-center gap-3 rounded-xl bg-white/[0.02] p-3 ring-1 ring-inset ring-white/[0.04] md:grid-cols-12 md:px-4">
                <div className="col-span-2 md:col-span-4">
                  <div className="flex items-center gap-2.5">
                    <div className={cn("grid h-8 w-8 place-items-center rounded-lg", s.active ? "bg-emerald-500/10 text-emerald-300" : "bg-slate-500/10 text-slate-400")}>
                      {busy[s.name] ? <RotateCw className="h-4 w-4 spin-slow" /> : <Power className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-100">{s.label}</div>
                      <div className="truncate font-mono text-[10px] text-slate-500">{s.name} · <span className="inline-flex items-center gap-0.5"><Clock className="h-2.5 w-2.5" />{s.since ? s.since.substring(0, 24) : "—"}</span></div>
                    </div>
                  </div>
                </div>
                <div className="col-span-1 hidden md:block"><span className="font-mono text-xs text-slate-400">{s.port ?? "—"}</span></div>
                <div className="col-span-1 md:col-span-2"><StatusPill tone={stateTone[s.state]} label={s.state} pulse={s.state === "active"} /></div>
                <div className="col-span-1 hidden items-center gap-2 md:col-span-2 md:flex">
                  <Progress value={s.cpu} tone={s.cpu > 40 ? "amber" : "indigo"} />
                  <span className="w-8 shrink-0 text-right text-[11px] tabular text-slate-400">{s.cpu}%</span>
                </div>
                <div className="col-span-1 hidden md:block"><span className="tabular text-xs text-slate-400">{s.mem ? `${s.mem}MB` : "—"}</span></div>
                <div className="col-span-1 flex items-center justify-end gap-1.5 md:col-span-2">
                  <IconButton tone="rose" disabled={!controllable || !s.active || busy[s.name]} onClick={() => act(s.name, "stop")} title="Stop" className="!h-7 !w-7"><Square className="h-3.5 w-3.5" /></IconButton>
                  <IconButton tone="indigo" disabled={!controllable || busy[s.name]} onClick={() => act(s.name, "restart")} title="Restart" className="!h-7 !w-7"><RotateCw className="h-3.5 w-3.5" /></IconButton>
                  <IconButton tone="emerald" disabled={!controllable || s.active || busy[s.name]} onClick={() => act(s.name, "start")} title="Start" className="!h-7 !w-7"><Play className="h-3.5 w-3.5" /></IconButton>
                </div>
              </div>
            );
          })}
          {!services.length && <div className="py-12 text-center text-sm text-slate-500">Waiting for service telemetry…</div>}
        </div>
      </Card>
    </div>
  );
}
