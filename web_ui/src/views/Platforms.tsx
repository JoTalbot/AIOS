import { useState } from "react";
import { Boxes, MapPin, Users, Zap, TrendingUp } from "lucide-react";
import { Card, PanelHeader, Badge, Segmented, Progress } from "../components/ui/primitives";
import { Sparkline } from "../components/ui/charts";
import { formatNumber } from "../lib/format";
import type { UseLiveData } from "../data/useLiveData";
import type { PlatformInfo } from "../types";

type Filter = "all" | PlatformInfo["status"];

const STATUS_TONE: Record<PlatformInfo["status"], { tone: any; label: string }> = {
  full: { tone: "emerald", label: "Full Stack" },
  collector: { tone: "cyan", label: "Collector" },
  messaging: { tone: "violet", label: "Messaging" },
  scaffold: { tone: "amber", label: "Scaffold" },
};

export function Platforms({ data }: { data: UseLiveData }) {
  const [filter, setFilter] = useState<Filter>("all");
  const platforms = data.connectors;
  const list = filter === "all" ? platforms : platforms.filter((p) => p.status === filter);
  const totalActions = platforms.reduce((a, p) => a + p.actionsToday, 0);
  const activePlatforms = platforms.filter((p) => p.actionsToday > 0);
  const avgSuccess = activePlatforms.length ? (activePlatforms.reduce((a, p) => a + p.successRate, 0) / activePlatforms.length).toFixed(1) : "0.0";
  const totalProfiles = platforms.reduce((a, p) => a + p.profiles, 0);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Connectors", value: platforms.length, icon: Boxes, tone: "indigo" as const },
          { label: "Profiles managed", value: formatNumber(totalProfiles), icon: Users, tone: "cyan" as const },
          { label: "Actions today", value: formatNumber(totalActions), icon: Zap, tone: "emerald" as const },
          { label: "Avg success", value: `${avgSuccess}%`, icon: TrendingUp, tone: "violet" as const },
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

      <Card>
        <PanelHeader
          icon={<Boxes className="h-[18px] w-[18px]" />}
          title="Marketplace Connectors"
          subtitle="Multi-platform automation via YAML descriptors"
          action={
            <Segmented
              size="sm"
              value={filter}
              onChange={setFilter}
              options={[
                { value: "all", label: "All" },
                { value: "full", label: "Full" },
                { value: "collector", label: "Collector" },
                { value: "messaging", label: "Messaging" },
                { value: "scaffold", label: "Scaffold" },
              ]}
            />
          }
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((p) => {
            const st = STATUS_TONE[p.status];
            return (
              <div key={p.id} className="card-hover glass rounded-2xl p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="grid h-11 w-11 place-items-center rounded-xl text-2xl" style={{ background: `${p.color}1f`, boxShadow: `inset 0 0 0 1px ${p.color}33` }}>
                      {p.emoji}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white">{p.name}</div>
                      <div className="font-mono text-[10px] text-slate-500">{p.package}</div>
                    </div>
                  </div>
                  <Badge tone={st.tone}>{st.label}</Badge>
                </div>

                <div className="mt-4 flex items-end justify-between">
                  <Sparkline data={p.trend} color={p.color} width={120} height={36} />
                  <div className="text-right">
                    <div className="text-lg font-extrabold tabular text-white">{formatNumber(p.actionsToday)}</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-500">actions today</div>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>Success rate</span>
                    <span className="font-semibold tabular text-slate-200">{p.successRate}%</span>
                  </div>
                  <Progress value={p.successRate} tone="emerald" className="mt-1.5" />
                </div>

                <div className="mt-3 flex items-center gap-3 border-t border-white/[0.05] pt-3 text-[11px] text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <Users className="h-3 w-3" /> {p.profiles} profiles
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3" /> {p.region}
                  </span>
                </div>
              </div>
            );
          })}
          {!list.length && <div className="col-span-full py-12 text-center text-sm text-slate-500">Waiting for live connector inventory…</div>}
        </div>
      </Card>
    </div>
  );
}
