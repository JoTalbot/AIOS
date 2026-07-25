import { useEffect, useMemo, useState } from "react";
import { Scale, Search, BookText, ShieldCheck, Globe, CheckCircle2, FileEdit, Loader2 } from "lucide-react";
import { Card, PanelHeader, Badge } from "../components/ui/primitives";
import { apiGet } from "../lib/api";
import { cn } from "../utils/cn";
import type { ConstitutionArticle } from "../types";

type Article = ConstitutionArticle & { filename?: string; body?: string };
const LEVEL_TONE: Record<string, any> = { Fundamental: "rose", Constitutional: "indigo", Operational: "indigo", Advisory: "slate" };

function categoryFor(article: any): string {
  if (article.category) return article.category;
  const stem = String(article.filename || article.title || "General").replace(/\.md$/i, "");
  const parts = stem.split("-").slice(2);
  return parts[0] ? parts[0].replace(/_/g, " ") : "General";
}

export function Constitution() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("All");
  const [level, setLevel] = useState("All");
  const [selectedNum, setSelectedNum] = useState(0);
  const [detail, setDetail] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<any[]>("api/constitution")
      .then((rows) => {
        const mapped = rows.map((a) => ({ ...a, category: categoryFor(a) }));
        setArticles(mapped);
        if (mapped[0]) setSelectedNum(mapped[0].number);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedNum) return;
    setDetail(null);
    apiGet<Article>(`api/constitution/${selectedNum}`)
      .then((article) => setDetail({ ...article, category: categoryFor(article) }))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [selectedNum]);

  const categories = useMemo(() => ["All", ...Array.from(new Set(articles.map((a) => a.category)))], [articles]);
  const levels = useMemo(() => ["All", ...Array.from(new Set(articles.map((a) => a.level)))], [articles]);
  const filtered = useMemo(() => articles.filter((a) =>
    (cat === "All" || a.category === cat) &&
    (level === "All" || a.level === level) &&
    (!q || `${a.title} ${a.numeral} ${a.scope}`.toLowerCase().includes(q.toLowerCase()))
  ), [articles, q, cat, level]);
  const selected = detail ?? articles.find((a) => a.number === selectedNum) ?? articles[0];
  const fundamental = articles.filter((a) => ["Fundamental", "Constitutional"].includes(a.level)).length;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Total articles", value: articles.length, icon: BookText, tone: "indigo" },
          { label: "Constitutional", value: fundamental, icon: Scale, tone: "rose" },
          { label: "Categories", value: Math.max(0, categories.length - 1), icon: ShieldCheck, tone: "cyan" },
          { label: "Enforced", value: articles.filter((a) => a.valid).length, icon: CheckCircle2, tone: "emerald" },
        ].map((s) => (
          <Card key={s.label} className="flex items-center gap-3 p-4">
            <div className={`grid h-10 w-10 place-items-center rounded-xl bg-${s.tone}-500/10 text-${s.tone}-300`}><s.icon className="h-5 w-5" /></div>
            <div><div className="text-xl font-extrabold tabular text-white">{s.value}</div><div className="text-[11px] uppercase tracking-wide text-slate-500">{s.label}</div></div>
          </Card>
        ))}
      </div>

      {error && <div className="rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">{error}</div>}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <div className="mb-4 space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search live constitution…" className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] py-2.5 pl-9 pr-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-400/50" />
              </div>
              <select value={level} onChange={(e) => setLevel(e.target.value)} className="rounded-xl border border-white/[0.08] bg-[#111827] px-3 py-2.5 text-xs text-slate-300 outline-none">
                {levels.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((c) => (
                <button key={c} onClick={() => setCat(c)} className={cn("rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors", cat === c ? "bg-indigo-500/90 text-white" : "bg-white/[0.04] text-slate-400 hover:text-slate-200")}>{c}</button>
              ))}
            </div>
          </div>

          <div className="grid max-h-[620px] grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
            {filtered.map((a) => (
              <button key={a.number} onClick={() => setSelectedNum(a.number)} className={cn("flex items-start gap-3 rounded-xl border p-3 text-left transition-all", selectedNum === a.number ? "border-indigo-400/40 bg-indigo-500/[0.07]" : "border-white/[0.05] bg-white/[0.02] hover:border-white/15")}>
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/[0.04] font-mono text-[11px] font-bold text-indigo-300 ring-1 ring-inset ring-white/[0.06]">{a.numeral}</div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold leading-snug text-slate-100">{a.title}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5"><span className="text-[10px] text-slate-500">{a.category}</span><Badge tone={LEVEL_TONE[a.level] || "slate"}>{a.level}</Badge>{!a.valid && <Badge tone="amber"><FileEdit className="h-2.5 w-2.5" /> Draft</Badge>}</div>
                </div>
              </button>
            ))}
            {loading && <div className="col-span-2 flex items-center justify-center gap-2 py-12 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading articles…</div>}
            {!loading && filtered.length === 0 && <div className="col-span-2 py-10 text-center text-sm text-slate-500">No articles match your filters.</div>}
          </div>
        </Card>

        <Card>
          <PanelHeader icon={<Scale className="h-[18px] w-[18px]" />} title="Article Detail" subtitle={`Constitution · ${filtered.length} shown`} />
          {selected ? <>
            <div className="rounded-2xl border border-white/[0.06] bg-gradient-to-b from-indigo-500/[0.06] to-transparent p-5">
              <div className="flex items-center gap-3">
                <div className="grid h-14 w-14 place-items-center rounded-xl bg-indigo-500/15 font-mono text-base font-bold text-indigo-300 ring-1 ring-inset ring-indigo-400/20">{selected.numeral}</div>
                <div><div className="text-[11px] uppercase tracking-wide text-slate-500">Article {selected.number}</div><Badge tone={LEVEL_TONE[selected.level] || "slate"}>{selected.level}</Badge></div>
              </div>
              <h3 className="mt-4 text-lg font-bold leading-snug text-white">{selected.title}</h3>
              <div className="mt-4 space-y-2.5 text-sm"><Row label="Category" value={selected.category} /><Row label="Scope" value={selected.scope} icon={Globe} /><Row label="Status" value={selected.status || (selected.valid ? "Active" : "Draft")} /></div>
            </div>
            {selected.body && <pre className="mt-4 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-black/20 p-3 font-mono text-[10px] leading-relaxed text-slate-400 ring-1 ring-inset ring-white/[0.05]">{selected.body}</pre>}
            <div className="mt-4 flex items-center gap-2 rounded-xl bg-white/[0.02] p-3 ring-1 ring-inset ring-white/[0.04]">
              {selected.valid ? <><CheckCircle2 className="h-5 w-5 text-emerald-400" /><div><div className="text-sm font-semibold text-slate-200">Enforced by Constitution Engine</div><div className="text-[11px] text-slate-500">Evaluated before every governed action.</div></div></> : <><FileEdit className="h-5 w-5 text-amber-400" /><div><div className="text-sm font-semibold text-slate-200">Draft — not yet enforced</div><div className="text-[11px] text-slate-500">Awaiting ratification.</div></div></>}
            </div>
          </> : <div className="py-12 text-center text-sm text-slate-500">Select an article.</div>}
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value, icon: Icon }: { label: string; value: string; icon?: any }) {
  return <div className="flex items-center justify-between gap-3 border-b border-white/[0.04] pb-2"><span className="text-slate-500">{label}</span><span className="inline-flex items-center gap-1.5 text-right font-medium text-slate-200">{Icon && <Icon className="h-3.5 w-3.5 text-slate-500" />} {value}</span></div>;
}
