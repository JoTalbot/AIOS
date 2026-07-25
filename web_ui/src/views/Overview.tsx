import { useState } from "react";
import {
  ShieldCheck,
  BrainCircuit,
  Boxes,
  Activity,
  CheckCircle2,
  Database,
  Timer,
  Network,
  Scale,
  Radar,
  Eye,
  Cpu,
  ArrowRight,
} from "lucide-react";
import { Card, PanelHeader, Badge, Progress, Dot, Segmented } from "../components/ui/primitives";
import { StatCard } from "../components/ui/StatCard";
import { AreaChart, Donut, Gauge, Sparkline } from "../components/ui/charts";
import { AuditRow } from "../components/AuditRow";
import type { UseLiveData } from "../data/useLiveData";
import { formatNumber, formatTime } from "../lib/format";
import { cn } from "../utils/cn";

type Metric = "tasks" | "compliance" | "latency" | "throughput";

const METRICS: Record<Metric, { label: string; color: string; format: (v: number) => string }> = {
  tasks: { label: "Tasks / interval", color: "#818cf8", format: (v) => String(Math.round(v)) },
  compliance: { label: "Compliance %", color: "#34d399", format: (v) => v.toFixed(1) + "%" },
  latency: { label: "P95 latency (ms)", color: "#22d3ee", format: (v) => Math.round(v) + "ms" },
  throughput: { label: "Throughput", color: "#fbbf24", format: (v) => String(Math.round(v)) },
};

const PILLARS = [
  { icon: Scale, title: "Constitutional Engine", desc: "67 articles · Law Veto Engine · real-time Tula scanner", tone: "text-indigo-300" },
  { icon: BrainCircuit, title: "Multi-Agent Orchestrator", desc: "Federation manager · predictive autonomy · DAG scheduler", tone: "text-cyan-300" },
  { icon: Eye, title: "Observability & Telemetry", desc: "OpenTelemetry tracing · Prometheus · structured context logs", tone: "text-emerald-300" },
  { icon: Network, title: "Device Pool & Routing", desc: "Lease contracts · HRW shard hashing · sticky profiles", tone: "text-violet-300" },
];

export function Overview({ data, onNavigate }: { data: UseLiveData; onNavigate: (v: any) => void }) {
  const [metric, setMetric] = useState<Metric>("tasks");
  const s = data.stats;
  const topPlatforms = [...data.connectors].sort((a, b) => b.actionsToday - a.actionsToday).slice(0, 6);

  return (
    <div className="space-y-5">
      {/* Hero KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Compliance"
          icon={ShieldCheck}
          tone="emerald"
          value={`${(s.compliance_ratio * 100).toFixed(1)}%`}
          sub={`${s.constitutional_articles} articles validated`}
          spark={{ data: data.series.compliance, color: "#34d399" }}
        />
        <StatCard
          label="AI Safety Index"
          icon={Scale}
          tone="cyan"
          value={`${(s.safety_score * 100).toFixed(1)}%`}
          sub="Real-time guardrails active"
          spark={{ data: data.series.latency, color: "#22d3ee" }}
        />
        <StatCard
          label="Active Agents"
          icon={BrainCircuit}
          tone="violet"
          value={s.active_agents}
          sub="L1 – L5 autonomy scale"
          spark={{ data: data.series.throughput, color: "#a78bfa" }}
        />
        <StatCard
          label="Throughput"
          icon={Activity}
          tone="indigo"
          value={`${s.tasks_per_min}`}
          sub="tasks / min · live"
          spark={{ data: data.series.tasks, color: "#818cf8" }}
        />
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Completed Tasks" icon={CheckCircle2} tone="emerald" value={formatNumber(s.completed_tasks)} sub={`${s.failed_tasks} failures · ${s.total_tasks ? ((s.completed_tasks / s.total_tasks) * 100).toFixed(2) : "100.00"}% success`} />
        <StatCard label="Memory Nodes" icon={Database} tone="amber" value={formatNumber(s.memory_nodes)} sub="Persistent SQLite vector store" />
        <StatCard label="P95 Latency" icon={Timer} tone="cyan" value={`${s.p95_latency_ms}ms`} sub="REST API gateway" />
        <StatCard label="API Routes" icon={Network} tone="indigo" value={s.api_routes} sub={`${s.tests_passed} tests passing`} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {/* System pulse */}
        <Card className="xl:col-span-2">
          <PanelHeader
            icon={<Activity className="h-[18px] w-[18px]" />}
            title="System Pulse"
            subtitle="Live telemetry · last 24 intervals"
            action={
              <Segmented
                size="sm"
                value={metric}
                onChange={setMetric}
                options={[
                  { value: "tasks", label: "Tasks" },
                  { value: "compliance", label: "Compliance" },
                  { value: "latency", label: "Latency" },
                  { value: "throughput", label: "Throughput" },
                ]}
              />
            }
          />
          <div className="mb-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold tabular text-white">
              {METRICS[metric].format(data.series[metric][data.series[metric].length - 1])}
            </span>
            <span className="text-xs font-medium text-slate-500">{METRICS[metric].label}</span>
            <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] text-emerald-400">
              <Dot tone="emerald" pulse /> streaming
            </span>
          </div>
          <AreaChart data={data.series[metric]} color={METRICS[metric].color} height={210} />
        </Card>

        {/* Compliance + Safety */}
        <Card>
          <PanelHeader icon={<ShieldCheck className="h-[18px] w-[18px]" />} title="Compliance & Safety" subtitle="Constitution-gated runtime" />
          <div className="flex items-center justify-around gap-2">
            <div className="flex flex-col items-center gap-2">
              <Donut value={s.compliance_ratio} color="#34d399" label={`${(s.compliance_ratio * 100).toFixed(0)}%`} sublabel="Compliance" size={116} />
              <Badge tone="emerald">{s.constitutional_articles} / {s.constitutional_articles} valid</Badge>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="relative">
                <Gauge value={s.safety_score} color="#22d3ee" size={116} />
                <div className="absolute inset-0 grid place-items-center pt-3">
                  <div className="text-center">
                    <div className="text-xl font-extrabold tabular text-white">{(s.safety_score * 100).toFixed(1)}</div>
                    <div className="text-[9px] uppercase tracking-wide text-slate-500">Safety</div>
                  </div>
                </div>
              </div>
              <Badge tone="cyan">{data.safety.status}</Badge>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-white/[0.06] pt-4">
            <div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Ban risk</span>
                <span className="font-semibold tabular text-slate-200">{(data.safety.metrics["Ban Risk Index"] * 100).toFixed(1)}%</span>
              </div>
              <Progress value={data.safety.metrics["Ban Risk Index"] * 100 * 5} tone="amber" className="mt-1.5" />
            </div>
            <div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Detection</span>
                <span className="font-semibold tabular text-slate-200">{(data.safety.metrics["Detection Probability"] * 100).toFixed(1)}%</span>
              </div>
              <Progress value={data.safety.metrics["Detection Probability"] * 100 * 3} tone="emerald" className="mt-1.5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Platform activity + audit feed */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <PanelHeader
            icon={<Boxes className="h-[18px] w-[18px]" />}
            title="Platform Activity"
            subtitle="Top connectors by today's actions"
            action={
              <button onClick={() => onNavigate("platforms")} className="inline-flex items-center gap-1 text-xs font-medium text-indigo-300 hover:text-indigo-200">
                View all <ArrowRight className="h-3 w-3" />
              </button>
            }
          />
          <div className="space-y-3">
            {topPlatforms.map((p) => (
              <div key={p.id} className="flex items-center gap-3 rounded-xl bg-white/[0.02] p-2.5 ring-1 ring-inset ring-white/[0.04]">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-lg" style={{ background: `${p.color}1a` }}>
                  {p.emoji}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-slate-200">{p.name}</span>
                    <span className="shrink-0 text-sm font-bold tabular text-white">{formatNumber(p.actionsToday)}</span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-2">
                    <Progress value={p.successRate} tone="emerald" />
                    <span className="shrink-0 text-[11px] font-medium tabular text-slate-400">{p.successRate}%</span>
                  </div>
                </div>
                <div className="hidden shrink-0 sm:block">
                  <Sparkline data={p.trend} color={p.color} width={64} height={28} fill={false} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="flex flex-col">
          <PanelHeader
            icon={<Radar className="h-[18px] w-[18px]" />}
            title="Live Audit Stream"
            subtitle="Immutable, tamper-evident"
            action={
              <button onClick={() => onNavigate("audit")} className="inline-flex items-center gap-1 text-xs font-medium text-indigo-300 hover:text-indigo-200">
                All <ArrowRight className="h-3 w-3" />
              </button>
            }
          />
          <div className="-mx-5 -mb-5 max-h-[360px] flex-1 divide-y divide-white/[0.04] overflow-y-auto">
            {data.audit.slice(0, 8).map((e) => (
              <AuditRow key={e.id} event={e} />
            ))}
          </div>
        </Card>
      </div>

      {/* Runtime banner */}
      <Card strong className="overflow-hidden">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 shadow-lg shadow-indigo-900/30">
              <Cpu className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">{s.runtime}</div>
              <div className="text-xs text-slate-400">Uptime {formatTime(s.uptime_seconds)} · {formatNumber(s.memory_nodes)} memory nodes</div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
            <Badge tone="indigo">v{s.version}</Badge>
            <Badge tone="slate">{s.registered_capabilities} capabilities</Badge>
            <Badge tone="violet">{s.platforms} platforms</Badge>
            <Badge tone="emerald">{s.tests_passed ? `${s.tests_passed} tests` : "tests: n/a"}</Badge>
          </div>
        </div>
      </Card>

      {/* Infrastructure pillars */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-300">Executive Infrastructure</h2>
          <div className="h-px flex-1 bg-white/[0.06]" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => {
            const Icon = p.icon;
            return (
              <Card key={p.title} hover className="p-4">
                <div className={cn("mb-3 grid h-9 w-9 place-items-center rounded-lg bg-white/[0.04]", p.tone)}>
                  <Icon className="h-[18px] w-[18px]" />
                </div>
                <div className="text-sm font-semibold text-slate-100">{p.title}</div>
                <div className="mt-1 text-xs leading-relaxed text-slate-400">{p.desc}</div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
