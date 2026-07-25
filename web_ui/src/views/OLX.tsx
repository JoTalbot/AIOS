import { useEffect, useState } from "react";
import {
  PackageOpen,
  Activity,
  Wallet,
  TrendingUp,
  MapPin,
  Building2,
  User,
  Send,
  Plus,
  Bell,
  Search,
  RefreshCw,
} from "lucide-react";
import { Card, PanelHeader, Badge, Dot, IconButton } from "../components/ui/primitives";
import { formatNumber, formatMoney, relativeTime } from "../lib/format";
import { apiPost } from "../lib/api";
import type { UseLiveData } from "../data/useLiveData";

function emojiFor(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("iphone") || t.includes("samsung") || t.includes("phone")) return "📱";
  if (t.includes("macbook") || t.includes("ноутбук") || t.includes("asus")) return "💻";
  if (t.includes("playstation") || t.includes("ps5")) return "🎮";
  if (t.includes("велосипед")) return "🚲";
  if (t.includes("toyota") || t.includes("авто")) return "🚗";
  if (t.includes("квартира")) return "🏢";
  if (t.includes("дрель") || t.includes("холодильник")) return "🔧";
  if (t.includes("watch") || t.includes("airpods")) return "🎧";
  return "📦";
}

const GRADIENTS = [
  "from-indigo-500/30 to-violet-500/20",
  "from-cyan-500/30 to-blue-500/20",
  "from-emerald-500/30 to-teal-500/20",
  "from-amber-500/30 to-orange-500/20",
  "from-rose-500/30 to-pink-500/20",
  "from-fuchsia-500/30 to-purple-500/20",
];

export function OLX({ data }: { data: UseLiveData }) {
  const olx = data.olx;
  const [subs, setSubs] = useState(data.subscriptions);
  const [query, setQuery] = useState("");
  const [chatId, setChatId] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => setSubs(data.subscriptions), [data.subscriptions]);

  const toggleSub = async (id: string) => {
    const sub = subs.find((s) => s.id === id);
    if (!sub?.chat_id) return;
    setBusy(true);
    setMessage(null);
    try {
      await apiPost("api/subs/action", {
        action: sub.active ? "remove" : "add",
        chat_id: sub.chat_id,
        query: sub.query,
        min_price: sub.min || null,
        max_price: sub.max || null,
      });
      setSubs((prev) => prev.map((s) => (s.id === id ? { ...s, active: !s.active } : s)));
      window.setTimeout(() => data.refresh(), 500);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const addSub = async () => {
    if (!query.trim() || !/^-?\d+$/.test(chatId.trim())) {
      setMessage("Enter a Telegram chat ID and a search query.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await apiPost("api/subs/action", {
        action: "add",
        chat_id: Number(chatId),
        query: query.trim(),
        min_price: minPrice ? Number(minPrice) : null,
        max_price: maxPrice ? Number(maxPrice) : null,
      });
      setQuery("");
      setMinPrice("");
      setMaxPrice("");
      setMessage("Subscription saved and connected to Telegram alerts.");
      window.setTimeout(() => data.refresh(), 400);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const collectNow = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await apiPost("api/olx/collect", {});
      setMessage("Collector restart accepted. Fresh listings will appear shortly.");
      window.setTimeout(() => data.refresh(), 2500);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const kpis = [
    { label: "Total listings", value: formatNumber(olx.ads_total), icon: PackageOpen, tone: "indigo" as const },
    { label: "Active", value: formatNumber(olx.ads_active), icon: Activity, tone: "emerald" as const },
    { label: "New / 24h", value: formatNumber(olx.new_24h), icon: TrendingUp, tone: "amber" as const },
    { label: "Avg price", value: formatMoney(olx.price_avg), icon: Wallet, tone: "violet" as const },
  ];

  return (
    <div className="space-y-5">
      <Card strong className="overflow-hidden">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-400 text-xl">🟢</div>
            <div>
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                OLX HTTP Collector
                <Badge tone="emerald"><Dot tone="emerald" pulse /> polling · 30 min</Badge>
              </div>
              <div className="text-xs text-slate-400">Stores ads in <span className="font-mono text-slate-300">data/olx_http.sqlite</span> · pushes Telegram alerts</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="slate">ua.slando</Badge>
            <button disabled={busy} onClick={collectNow} className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
              <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} /> Collect now
            </button>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label} className="p-4">
            <div className={`mb-2 inline-flex rounded-lg bg-${k.tone}-500/10 p-2 text-${k.tone}-300`}>
              <k.icon className="h-4 w-4" />
            </div>
            <div className="text-xl font-extrabold tabular text-white">{k.value}</div>
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{k.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {/* Listings */}
        <Card className="xl:col-span-2">
          <PanelHeader icon={<Search className="h-[18px] w-[18px]" />} title="Latest Listings" subtitle={`${data.ads.length} loaded · sorted by newest`} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {data.ads.map((a, i) => (
              <a
                key={a.id}
                href={a.url}
                target="_blank"
                rel="noreferrer"
                className="card-hover glass group flex gap-3 rounded-xl p-3"
              >
                <div className={`grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-lg bg-gradient-to-br ${GRADIENTS[i % GRADIENTS.length]} text-3xl`}>
                  {a.photos?.[0] ? <img src={a.photos[0]} alt="" className="h-full w-full object-cover" loading="lazy" /> : emojiFor(a.title)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="line-clamp-2 text-sm font-semibold leading-snug text-slate-100 group-hover:text-white">{a.title}</div>
                  <div className="mt-1 text-base font-extrabold text-emerald-400">{formatMoney(a.price_value, a.price_currency)}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-500">
                    <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {a.city}</span>
                    <span className="inline-flex items-center gap-1">
                      {a.business ? <Building2 className="h-3 w-3 text-cyan-400" /> : <User className="h-3 w-3" />}
                      {a.business ? "Business" : "Private"}
                    </span>
                  </div>
                  <div className="mt-1 font-mono text-[10px] text-slate-600">#{a.query}</div>
                </div>
                <span className="shrink-0 text-[10px] text-slate-600">{relativeTime((a.published ?? Date.parse((a as any).first_seen || (a as any).collected_at || "")) || Date.now())}</span>
              </a>
            ))}
            {!data.ads.length && <div className="col-span-full py-12 text-center text-sm text-slate-500">Waiting for live OLX listings…</div>}
          </div>
        </Card>

        {/* Subscriptions + Telegram */}
        <div className="space-y-5">
          <Card>
            <PanelHeader icon={<Bell className="h-[18px] w-[18px]" />} title="Subscriptions" subtitle="Telegram alerts on new matches" />
            <div className="mb-3 space-y-2">
              <div className="flex gap-2">
                <input value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="Telegram chat ID" className="w-2/5 min-w-0 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-400/50" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addSub()} placeholder="Search query" className="min-w-0 flex-1 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-400/50" />
                <IconButton tone="indigo" disabled={busy} onClick={addSub} title="Add subscription" className="w-auto px-3"><Plus className="h-4 w-4" /></IconButton>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type="number" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} placeholder="Min UAH" className="min-w-0 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600" />
                <input type="number" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} placeholder="Max UAH" className="min-w-0 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600" />
              </div>
              {message && <div className="rounded-lg bg-white/[0.03] px-3 py-2 text-[11px] text-slate-400">{message}</div>}
            </div>
            <div className="space-y-2">
              {subs.map((s) => (
                <div key={s.id} className="flex items-center gap-3 rounded-xl bg-white/[0.02] p-3 ring-1 ring-inset ring-white/[0.04]">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold text-slate-200">#{s.query}</div>
                    <div className="text-[11px] text-slate-500">
                      {s.min || s.max ? `${formatNumber(s.min)} – ${formatNumber(s.max)} UAH` : "Any price"} · {s.matches} matches
                    </div>
                  </div>
                  <button
                    onClick={() => toggleSub(s.id)}
                    className={`relative h-5 w-9 rounded-full transition-colors ${s.active ? "bg-emerald-500" : "bg-slate-600"}`}
                  >
                    <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${s.active ? "left-4" : "left-0.5"}`} />
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <PanelHeader icon={<Send className="h-[18px] w-[18px]" />} title="Telegram Bot" subtitle="@AIOScontrol_bot" />
            <div className="space-y-2 text-xs">
              {[
                "/start — register chat",
                "/olx_sub <query> [min max]",
                "/olx_latest <query> [N]",
                "/olx_analytics <query>",
                "/olx_unsub [query]",
              ].map((c) => (
                <div key={c} className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-2 font-mono text-slate-300">
                  <span className="text-indigo-400">›</span> {c}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
