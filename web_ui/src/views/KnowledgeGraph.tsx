import { useEffect, useMemo, useState } from "react";
import { Share2, Database, Cpu, Bot, ListChecks, Scale } from "lucide-react";
import { Card, PanelHeader, Badge } from "../components/ui/primitives";
import { apiGet } from "../lib/api";
import type { KgNode, KnowledgeGraphData } from "../types";

const TYPE_META: Record<KgNode["type"], { color: string; icon: any; label: string }> = {
  agent: { color: "#818cf8", icon: Bot, label: "Agent" },
  rule: { color: "#fb7185", icon: Scale, label: "Rule" },
  task: { color: "#22d3ee", icon: ListChecks, label: "Task" },
  memory: { color: "#fbbf24", icon: Database, label: "Memory" },
  model: { color: "#a78bfa", icon: Cpu, label: "Model" },
};

export function KnowledgeGraph() {
  const [hover, setHover] = useState<string | null>(null);
  const [graph, setGraph] = useState<KnowledgeGraphData>({ nodes: [], edges: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<KnowledgeGraphData>("api/knowledge-graph").then(setGraph).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const positions = useMemo(() => {
    const result: Record<string, { x: number; y: number }> = {};
    const center = graph.nodes.find((node) => node.id === "orchestrator") ?? graph.nodes[0];
    if (center) result[center.id] = { x: 270, y: 210 };
    const outer = graph.nodes.filter((node) => node.id !== center?.id);
    outer.forEach((node, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(1, outer.length);
      result[node.id] = { x: 270 + Math.cos(angle) * 185, y: 210 + Math.sin(angle) * 145 };
    });
    return result;
  }, [graph.nodes]);

  const KG = graph;
  const neighbors = new Set<string>();
  if (hover) {
    neighbors.add(hover);
    KG.edges.forEach((e) => {
      if (e.source === hover) neighbors.add(e.target);
      if (e.target === hover) neighbors.add(e.source);
    });
  }

  const relatedEdges = hover ? KG.edges.filter((e) => e.source === hover || e.target === hover) : [];

  return (
    <div className="space-y-5">
      {error && <div className="rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">{error}</div>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {(Object.keys(TYPE_META) as KgNode["type"][]).map((t) => {
          const count = KG.nodes.filter((n) => n.type === t).length;
          const m = TYPE_META[t];
          return (
            <Card key={t} className="flex items-center gap-3 p-3.5">
              <div className="grid h-9 w-9 place-items-center rounded-lg" style={{ background: `${m.color}1a`, color: m.color }}>
                <m.icon className="h-4 w-4" />
              </div>
              <div>
                <div className="text-lg font-extrabold tabular text-white">{count}</div>
                <div className="text-[10px] uppercase tracking-wide text-slate-500">{m.label}</div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-4">
        <Card className="xl:col-span-3">
          <PanelHeader
            icon={<Share2 className="h-[18px] w-[18px]" />}
            title="Federated Knowledge Graph"
            subtitle="Hover a node to trace relations"
            action={<Badge tone="indigo">{KG.edges.length} relations</Badge>}
          />
          {!KG.nodes.length && <div className="py-12 text-center text-sm text-slate-500">Loading live graph…</div>}
          <div className="overflow-hidden rounded-xl border border-white/[0.05] bg-[radial-gradient(circle_at_50%_40%,rgba(99,102,241,0.08),transparent_60%)]">
            <svg viewBox="0 0 540 420" className="w-full" style={{ aspectRatio: "540 / 420" }}>
              {/* edges */}
              {KG.edges.map((e, i) => {
                const a = positions[e.source];
                const b = positions[e.target];
                const dim = hover && !relatedEdges.includes(e);
                if (!a || !b) return null;
                return (
                  <g key={i} opacity={dim ? 0.08 : hover ? 1 : 0.4}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={relatedEdges.includes(e) ? "#818cf8" : "#64748b"} strokeWidth={relatedEdges.includes(e) ? 1.6 : 1} />
                  </g>
                );
              })}
              {/* nodes */}
              {KG.nodes.map((n) => {
                const p = positions[n.id];
                const meta = TYPE_META[n.type] || TYPE_META.agent;
                if (!p) return null;
                const dim = hover && !neighbors.has(n.id);
                const r = n.id === "orchestrator" ? 26 : 19;
                return (
                  <g
                    key={n.id}
                    transform={`translate(${p.x} ${p.y})`}
                    onMouseEnter={() => setHover(n.id)}
                    onMouseLeave={() => setHover(null)}
                    style={{ cursor: "pointer", opacity: dim ? 0.25 : 1, transition: "opacity .2s" }}
                  >
                    {n.id === "orchestrator" && <circle r={r + 8} fill="none" stroke={meta.color} strokeWidth="1" opacity="0.3" className="spin-slow" strokeDasharray="4 6" />}
                    <circle r={r} fill={`${meta.color}22`} stroke={meta.color} strokeWidth="2" />
                    <circle r={r - 7} fill={meta.color} opacity={hover === n.id ? 1 : 0.85} />
                    <text y={r + 13} textAnchor="middle" className="fill-slate-300" style={{ fontSize: 11, fontWeight: 600 }}>
                      {n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </Card>

        <Card>
          <PanelHeader icon={<Database className="h-[18px] w-[18px]" />} title="Node Inspector" subtitle={hover ? "selected" : "pick a node"} />
          {hover ? (
            (() => {
              const node = KG.nodes.find((n) => n.id === hover)!;
              const meta = TYPE_META[node.type];
              const out = KG.edges.filter((e) => e.source === hover);
              const inE = KG.edges.filter((e) => e.target === hover);
              return (
                <div>
                  <div className="rounded-xl border border-white/[0.06] p-4" style={{ background: `${meta.color}10` }}>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ background: meta.color }} />
                      <Badge tone="slate">{meta.label}</Badge>
                    </div>
                    <div className="mt-2 text-base font-bold text-white">{node.label}</div>
                    <div className="font-mono text-[10px] text-slate-500">{node.id}</div>
                  </div>
                  <div className="mt-4 space-y-3">
                    <RelGroup title="Outgoing" edges={out} nodes={KG.nodes} />
                    <RelGroup title="Incoming" edges={inE} nodes={KG.nodes} />
                    {out.length === 0 && inE.length === 0 && <p className="text-xs text-slate-500">Isolated node.</p>}
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="grid h-48 place-items-center text-center text-sm text-slate-500">
              <div>
                <Share2 className="mx-auto mb-2 h-8 w-8 text-slate-700" />
                Hover any node to inspect its<br />relationships in the federation.
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function RelGroup({ title, edges, nodes }: { title: string; edges: any[]; nodes: KgNode[] }) {
  if (!edges.length) return null;
  return (
    <div>
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="space-y-1.5">
        {edges.map((e, i) => {
          const otherId = title === "Outgoing" ? e.target : e.source;
          const other = nodes.find((n) => n.id === otherId);
          return (
            <div key={i} className="flex items-center justify-between rounded-lg bg-white/[0.02] px-2.5 py-1.5 text-xs">
              <span className="truncate font-medium text-slate-300">{other?.label}</span>
              <span className="ml-2 shrink-0 rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-slate-400">{e.relation}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
