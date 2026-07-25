import { useState } from "react";
import { Bot, Cpu, Activity, Loader, Brain, Ban, Layers, Gauge as GaugeIcon } from "lucide-react";
import { Card, PanelHeader, Badge, Progress, Dot } from "../components/ui/primitives";
import { Sparkline, Gauge } from "../components/ui/charts";
import { formatNumber } from "../lib/format";
import type { UseLiveData } from "../data/useLiveData";
import { cn } from "../utils/cn";
import type { AgentProfile } from "../types";

const STATUS: Record<AgentProfile["status"], { tone: any; label: string; icon: any }> = {
  executing: { tone: "emerald", label: "Executing", icon: Activity },
  thinking: { tone: "cyan", label: "Thinking", icon: Brain },
  blocked: { tone: "amber", label: "Blocked", icon: Ban },
  idle: { tone: "slate", label: "Idle", icon: Loader },
};

export function Swarm({ data }: { data: UseLiveData }) {
  const agents = data.agents;
  const [selectedId, setSelectedId] = useState("");
  const selected = agents.find((a) => a.agent_id === selectedId) ?? agents[0];
  const executing = agents.filter((a) => a.status === "executing").length;
  const blocked = agents.filter((a) => a.status === "blocked").length;
  const avgAutonomy = agents.length ? (agents.reduce((a, x) => a + x.autonomy, 0) / agents.length).toFixed(1) : "0.0";

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Agents in swarm", value: agents.length, icon: Bot, tone: "indigo" },
          { label: "Executing", value: executing, icon: Activity, tone: "emerald" },
          { label: "Blocked / awaiting", value: blocked, icon: Ban, tone: "amber" },
          { label: "Avg autonomy", value: `L${avgAutonomy}`, icon: GaugeIcon, tone: "violet" },
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

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <PanelHeader icon={<Bot className="h-[18px] w-[18px]" />} title="Agent Roster" subtitle="Click an agent to inspect" />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {agents.map((a) => {
              const st = STATUS[a.status];
              const isSel = a.agent_id === selectedId;
              return (
                <button
                  key={a.agent_id}
                  onClick={() => setSelectedId(a.agent_id)}
                  className={cn(
                    "rounded-2xl border p-4 text-left transition-all",
                    isSel ? "border-indigo-400/40 bg-indigo-500/[0.07]" : "border-white/[0.06] bg-white/[0.02] hover:border-white/15"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="relative grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-indigo-500/30 to-cyan-400/20 text-sm font-bold text-white">
                      {a.name.slice(0, 2).toUpperCase()}
                      <span className={cn("absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-[#0d1220]", `bg-${st.tone}-400`)} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-bold text-white">{a.name}</span>
                      </div>
                      <div className="truncate text-[11px] text-slate-400">{a.role}</div>
                    </div>
                    <Badge tone={st.tone}>{st.label}</Badge>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Autonomy</span>
                    <span className="font-semibold text-indigo-300">L{a.autonomy}</span>
                  </div>
                  <div className="mt-1 flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <div key={n} className={cn("h-1.5 flex-1 rounded-full", n <= a.autonomy ? "bg-indigo-400" : "bg-white/[0.06]")} />
                    ))}
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <Sparkline data={a.trend} color="#818cf8" width={90} height={26} fill={false} />
                    <span className="text-[11px] text-slate-500">{formatNumber(a.completed_tasks)} done</span>
                  </div>
                </button>
              );
            })}
            {!agents.length && <div className="col-span-full py-12 text-center text-sm text-slate-500">Waiting for the live agent roster…</div>}
          </div>
        </Card>

        {/* Detail */}
        <Card>
          {selected ? <>
          <PanelHeader icon={<Cpu className="h-[18px] w-[18px]" />} title="Agent Inspector" subtitle={selected.name} />
          <div className="flex flex-col items-center">
            <div className="relative">
              <Gauge value={selected.load / 100} color="#818cf8" size={150} />
              <div className="absolute inset-0 grid place-items-center pt-4">
                <div className="text-center">
                  <div className="text-2xl font-extrabold tabular text-white">{selected.load}%</div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">CPU load</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            <Detail label="Role" value={selected.role} />
            <Detail label="Autonomy" value={selected.autonomy_label} />
            <Detail label="Status" value={<Badge tone={STATUS[selected.status].tone}><Dot tone={STATUS[selected.status].tone as any} pulse /> {STATUS[selected.status].label}</Badge>} />
            <Detail label="Platform" value={selected.platform ?? "cross-platform"} />
            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-slate-400">Completed tasks</span>
                <span className="font-bold tabular text-white">{formatNumber(selected.completed_tasks)}</span>
              </div>
              <Progress value={selected.load} tone="indigo" />
            </div>
          </div>

          {selected.current_task && (
            <div className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-slate-500">
                <Layers className="h-3 w-3" /> Current task
              </div>
              <div className="text-sm text-slate-200">{selected.current_task}</div>
            </div>
          )}
          </> : <div className="grid h-64 place-items-center text-sm text-slate-500">No agent selected.</div>}
        </Card>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="text-right font-medium text-slate-200">{value}</span>
    </div>
  );
}
