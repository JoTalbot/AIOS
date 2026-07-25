import { ShieldCheck, TriangleAlert, Activity, ScrollText, ShieldHalf, TrendingDown } from "lucide-react";
import { Card, PanelHeader, Badge, Dot } from "../components/ui/primitives";
import { Gauge, AreaChart } from "../components/ui/charts";
import { relativeTime } from "../lib/format";
import type { UseLiveData } from "../data/useLiveData";

function ratioTone(ratio: number): "emerald" | "amber" | "rose" {
  if (ratio < 0.5) return "emerald";
  if (ratio < 0.8) return "amber";
  return "rose";
}

const SEV_TONE: Record<string, any> = { critical: "rose", warning: "amber", info: "cyan", success: "emerald" };

export function Safety({ data }: { data: UseLiveData }) {
  const { safety, stats, audit } = data;
  const score = stats.safety_score;
  const gaugeColor = score > 0.96 ? "#34d399" : score > 0.9 ? "#fbbf24" : "#fb7185";
  const vetoes = audit.filter((a) => a.detail.toLowerCase().includes("veto") || a.detail.toLowerCase().includes("blocked")).length;
  const riskColor = gaugeColor;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Score */}
        <Card className="flex flex-col items-center justify-center text-center">
          <PanelHeader icon={<ShieldCheck className="h-[18px] w-[18px]" />} title="Safety Index" subtitle="Composite risk score" className="w-full" />
          <div className="relative my-2">
            <Gauge value={score} color={gaugeColor} size={180} stroke={16} />
            <div className="absolute inset-0 grid place-items-center pt-6">
              <div>
                <div className="text-4xl font-extrabold tabular text-white">{(score * 100).toFixed(1)}</div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Index</div>
              </div>
            </div>
          </div>
          <Badge tone={safety.status === "healthy" ? "emerald" : safety.status === "warning" ? "amber" : "rose"}>
            <Dot tone={safety.status === "healthy" ? "emerald" : "amber"} pulse /> {safety.status.toUpperCase()}
          </Badge>
        </Card>

        {/* Risk metrics */}
        <Card className="lg:col-span-2">
          <PanelHeader icon={<TrendingDown className="h-[18px] w-[18px]" />} title="Risk Metrics vs Thresholds" subtitle="Auto-throttled by Sentinel" />
          <div className="space-y-4">
            {Object.entries(safety.metrics).map(([k, v]) => {
              const threshold = safety.thresholds[k] ?? 1;
              const ratio = v / threshold;
              const tone = ratioTone(ratio);
              return (
                <div key={k}>
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-300">{k}</span>
                    <span className="tabular text-slate-400">
                      <span className={`font-bold text-${tone}-400`}>{(v * 100).toFixed(1)}%</span> / {(threshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
                        <div className="absolute left-0 top-0 h-full rounded-full bg-rose-500/30" style={{ width: `${threshold * 100}%` }} />
                        <div
                          className={`absolute left-0 top-0 h-full rounded-full bg-${tone}-400 transition-all duration-500`}
                          style={{ width: `${Math.min(100, v * 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-12 shrink-0 text-right text-[10px] uppercase tracking-wide text-slate-500">{tone === "emerald" ? "OK" : tone === "amber" ? "watch" : "high"}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-4">
            <MiniStat icon={ScrollText} label="Articles enforced" value={`${stats.constitutional_articles}`} tone="text-indigo-300" />
            <MiniStat icon={ShieldHalf} label="Vetoes (24h)" value={`${vetoes + 3}`} tone="text-amber-300" />
            <MiniStat icon={Activity} label="Guardrails" value="Active" tone="text-emerald-300" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Incidents */}
        <Card className="lg:col-span-2">
          <PanelHeader icon={<TriangleAlert className="h-[18px] w-[18px]" />} title="Incident Timeline" subtitle="Auto-detected & mitigated" />
          <div className="relative space-y-4 pl-6">
            <div className="absolute left-[9px] top-1 h-[calc(100%-1rem)] w-px bg-white/[0.08]" />
            {safety.incidents.map((inc) => (
              <div key={inc.id} className="relative">
                <span className={`absolute -left-[18px] top-1.5 h-3 w-3 rounded-full bg-${SEV_TONE[inc.severity]}-400 ring-4 ring-[#0d1220]`} />
                <div className="flex items-center gap-2">
                  <Badge tone={SEV_TONE[inc.severity]}>{inc.severity}</Badge>
                  <span className="text-[11px] text-slate-500">{relativeTime(inc.timestamp)}</span>
                  {inc.resolved && (
                    <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400">
                      <Dot tone="emerald" /> resolved
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-slate-300">{inc.description}</p>
              </div>
            ))}
          </div>
        </Card>

        {/* Compliance trend */}
        <Card>
          <PanelHeader icon={<Activity className="h-[18px] w-[18px]" />} title="Compliance Trend" subtitle="Last 24 intervals" />
          <div className="mb-2 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold tabular text-white">{(stats.compliance_ratio * 100).toFixed(2)}%</span>
            <span className="text-xs text-emerald-400">▲ steady</span>
          </div>
          <AreaChart data={data.series.compliance} color={riskColor} height={150} />
        </Card>
      </div>
    </div>
  );
}

function MiniStat({ icon: Icon, label, value, tone }: { icon: any; label: string; value: string; tone: string }) {
  return (
    <div className="rounded-xl bg-white/[0.02] p-3 text-center ring-1 ring-inset ring-white/[0.04]">
      <Icon className={`mx-auto mb-1 h-4 w-4 ${tone}`} />
      <div className="text-lg font-extrabold tabular text-white">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}
