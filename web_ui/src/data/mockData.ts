import type { AgentProfile, AndroidDevice, OlxAd, PlatformInfo, ServiceInfo, Subscription } from "../types";

/**
 * Static seed data for the AIOS Control Plane dashboard.
 *
 * These are the baseline entities the live-data engine (see `useLiveData.ts`)
 * mutates on every tick to produce a continuously-evolving, realistic feed.
 * Counts and identifiers here are grounded in the actual repository surface
 * (9 marketplace/messenger connectors under `aios_cli`, roles mirrored from
 * `aios_core/ai_*.py` modules, systemd units used by the deploy scripts).
 */

export const PLATFORMS: PlatformInfo[] = [
  { id: "olx", name: "OLX", package: "ua.slando", status: "full", emoji: "🟢", color: "#22c55e", profiles: 14, actionsToday: 640, successRate: 97, region: "UA", trend: [] },
  { id: "rozetka", name: "Rozetka", package: "ua.com.rozetka.shop", status: "full", emoji: "🛒", color: "#0ea5e9", profiles: 6, actionsToday: 210, successRate: 95, region: "UA", trend: [] },
  { id: "instagram", name: "Instagram", package: "com.instagram.android", status: "full", emoji: "📸", color: "#e1306c", profiles: 9, actionsToday: 380, successRate: 92, region: "Global", trend: [] },
  { id: "facebook", name: "Facebook", package: "com.facebook.katana", status: "collector", emoji: "📘", color: "#1877f2", profiles: 4, actionsToday: 95, successRate: 88, region: "Global", trend: [] },
  { id: "tiktok", name: "TikTok", package: "com.zhiliaoapp.musically", status: "full", emoji: "🎵", color: "#25f4ee", profiles: 5, actionsToday: 260, successRate: 90, region: "Global", trend: [] },
  { id: "telegram", name: "Telegram Bot", package: "org.telegram.messenger", status: "messaging", emoji: "✈️", color: "#26a5e4", profiles: 1, actionsToday: 520, successRate: 99, region: "Global", trend: [] },
  { id: "viber", name: "Viber", package: "com.viber.voip", status: "messaging", emoji: "💜", color: "#7360f2", profiles: 2, actionsToday: 70, successRate: 96, region: "UA", trend: [] },
  { id: "whatsapp", name: "WhatsApp", package: "com.whatsapp", status: "messaging", emoji: "💬", color: "#25d366", profiles: 3, actionsToday: 150, successRate: 94, region: "Global", trend: [] },
  { id: "shafa", name: "Shafa", package: "com.shafa.android", status: "scaffold", emoji: "👗", color: "#fb7185", profiles: 1, actionsToday: 12, successRate: 80, region: "UA", trend: [] },
];

export const AGENT_ROSTER: AgentProfile[] = [
  { agent_id: "ag-orchestrator", name: "Orchestrator", role: "Multi-Agent Orchestrator", autonomy: 5, autonomy_label: "L5 · Full autonomy", status: "executing", completed_tasks: 18420, load: 62, trend: [] },
  { agent_id: "ag-swarm", name: "Swarm Coordinator", role: "Agent Swarm Manager", autonomy: 5, autonomy_label: "L5 · Full autonomy", status: "executing", completed_tasks: 22040, load: 58, trend: [] },
  { agent_id: "ag-olx", name: "OLX Scout", role: "Marketplace Agent", autonomy: 4, autonomy_label: "L4 · Supervised autonomy", status: "executing", completed_tasks: 15200, platform: "olx", load: 71, trend: [] },
  { agent_id: "ag-social", name: "Social Runner", role: "Social Media Agent", autonomy: 3, autonomy_label: "L3 · Guarded autonomy", status: "executing", completed_tasks: 7360, platform: "instagram", load: 44, trend: [] },
  { agent_id: "ag-engineer", name: "Engineer", role: "AI Engineer", autonomy: 4, autonomy_label: "L4 · Supervised autonomy", status: "thinking", completed_tasks: 9130, load: 35, trend: [] },
  { agent_id: "ag-researcher", name: "Researcher", role: "AI Researcher", autonomy: 4, autonomy_label: "L4 · Supervised autonomy", status: "thinking", completed_tasks: 6210, load: 29, trend: [] },
  { agent_id: "ag-safety", name: "Sentinel", role: "AI Safety Officer", autonomy: 3, autonomy_label: "L3 · Guarded autonomy", status: "executing", completed_tasks: 4310, load: 21, trend: [] },
  { agent_id: "ag-advisor", name: "Advisor", role: "AI Advisor", autonomy: 3, autonomy_label: "L3 · Guarded autonomy", status: "idle", completed_tasks: 2890, load: 8, trend: [] },
  { agent_id: "ag-pm", name: "Product Manager", role: "AI Product Manager", autonomy: 2, autonomy_label: "L2 · Assisted autonomy", status: "idle", completed_tasks: 1540, load: 5, trend: [] },
  { agent_id: "ag-kg", name: "Curator", role: "Knowledge Graph Curator", autonomy: 2, autonomy_label: "L2 · Assisted autonomy", status: "blocked", completed_tasks: 980, load: 12, trend: [] },
];

export const DEVICE_ROSTER: AndroidDevice[] = [
  { serial: "emu-5554", model: "Pixel 7 (API 34)", host: "hcloud-cax31-1", status: "online", profile: "olx-main", battery: 100, platform: "olx", uptime: 0 },
  { serial: "emu-5556", model: "Pixel 6 (API 33)", host: "hcloud-cax31-1", status: "busy", profile: "insta-01", battery: 84, platform: "instagram", uptime: 0 },
  { serial: "emu-5558", model: "Galaxy S22 (API 33)", host: "hcloud-cax31-2", status: "online", profile: "rozetka-01", battery: 91, platform: "rozetka", uptime: 0 },
  { serial: "emu-5560", model: "Pixel 5 (API 31)", host: "hcloud-cax31-2", status: "offline", profile: "tiktok-01", battery: 12, platform: "tiktok", uptime: 0 },
  { serial: "emu-5562", model: "Pixel 7 Pro (API 34)", host: "hcloud-cax41-1", status: "busy", profile: "fb-collector", battery: 76, platform: "facebook", uptime: 0 },
  { serial: "emu-5564", model: "Galaxy A54 (API 33)", host: "hcloud-cax41-1", status: "online", profile: "shafa-scaffold", battery: 63, platform: "shafa", uptime: 0 },
];

export const SERVICE_ROSTER: ServiceInfo[] = [
  { name: "aios-api", label: "AIOS REST API", port: 8080, state: "active", active: true, since: new Date(Date.now() - 3 * 86400_000).toISOString(), cpu: 6, mem: 340 },
  { name: "aios-dash", label: "Control Plane Dashboard", port: 5173, state: "active", active: true, since: new Date(Date.now() - 3 * 86400_000).toISOString(), cpu: 3, mem: 120 },
  { name: "aios-orchestrator", label: "Multi-Agent Orchestrator", state: "active", active: true, since: new Date(Date.now() - 3 * 86400_000).toISOString(), cpu: 18, mem: 890 },
  { name: "aios-collector", label: "OLX Collector", state: "active", active: true, since: new Date(Date.now() - 2 * 86400_000).toISOString(), cpu: 9, mem: 210 },
  { name: "aios-bot", label: "Telegram Bot", state: "active", active: true, since: new Date(Date.now() - 2 * 86400_000).toISOString(), cpu: 2, mem: 95 },
  { name: "postgres", label: "PostgreSQL", port: 5432, state: "active", active: true, since: new Date(Date.now() - 12 * 86400_000).toISOString(), cpu: 11, mem: 640 },
  { name: "redis", label: "Redis Cache", port: 6379, state: "active", active: true, since: new Date(Date.now() - 12 * 86400_000).toISOString(), cpu: 1, mem: 64 },
  { name: "emulator", label: "Android Emulator Pool", state: "active", active: true, since: new Date(Date.now() - 5 * 86400_000).toISOString(), cpu: 24, mem: 2100 },
];

export const SUBSCRIPTIONS_SEED: Subscription[] = [
  { id: "sub-1", chat_id: 100200300, query: "iphone 13", min: 12000, max: 22000, matches: 34, active: true },
  { id: "sub-2", chat_id: 100200300, query: "велосипед", min: 3000, max: 9000, matches: 11, active: true },
  { id: "sub-3", chat_id: 554433221, query: "macbook air", min: 0, max: 35000, matches: 6, active: false },
];

export const SAMPLE_ADS: OlxAd[] = [
  { id: "olx-1", title: "iPhone 13 128GB, ідеальний стан", price_value: 17800, price_currency: "UAH", city: "Kropyvnytskyi", query: "iphone 13", business: false, url: "https://www.olx.ua/", published: Date.now() - 3 * 60_000 },
  { id: "olx-2", title: "Велосипед гірський Trek 27.5", price_value: 6200, price_currency: "UAH", city: "Kyiv", query: "велосипед", business: false, url: "https://www.olx.ua/", published: Date.now() - 11 * 60_000 },
  { id: "olx-3", title: "MacBook Air M1 2020 8/256", price_value: 24900, price_currency: "UAH", city: "Odesa", query: "macbook air", business: true, url: "https://www.olx.ua/", published: Date.now() - 24 * 60_000 },
  { id: "olx-4", title: "PlayStation 5 + 2 джойстики", price_value: 15800, price_currency: "UAH", city: "Lviv", query: "playstation 5", business: false, url: "https://www.olx.ua/", published: Date.now() - 40 * 60_000 },
  { id: "olx-5", title: "Дриль ударний Bosch, нова", price_value: 1900, price_currency: "UAH", city: "Kropyvnytskyi", query: "дриль", business: true, url: "https://www.olx.ua/", published: Date.now() - 62 * 60_000 },
  { id: "olx-6", title: "Квартира 2-к, центр, ремонт", price_value: 32000, price_currency: "UAH", city: "Kropyvnytskyi", query: "квартира", business: true, url: "https://www.olx.ua/", published: Date.now() - 90 * 60_000 },
];

export const SAFETY_METRIC_KEYS = ["Ban Risk Index", "Detection Probability", "Rate-Limit Pressure", "Anomaly Score"] as const;

export const AUDIT_TEMPLATES: Array<{ type: import("../types").AuditEvent["type"]; actor: string; action: string; detail: string; severity: import("../types").Severity }> = [
  { type: "compliance", actor: "Tula Scanner", action: "Constitution check passed", detail: "All 67 articles validated on latest commit", severity: "success" },
  { type: "agent", actor: "Orchestrator", action: "Task delegated", detail: "Assigned scraping batch to OLX Scout", severity: "info" },
  { type: "platform", actor: "OLX Collector", action: "Collection cycle complete", detail: "Fetched new listings for 6 saved searches", severity: "success" },
  { type: "security", actor: "Sentinel", action: "Rate-limit guard engaged", detail: "Throttled Instagram profile insta-01 for 90s", severity: "warning" },
  { type: "system", actor: "aios-api", action: "Health check", detail: "All services reporting nominal", severity: "info" },
  { type: "approval", actor: "Human reviewer", action: "Action approved", detail: "Manual approval granted for bulk relist", severity: "success" },
  { type: "agent", actor: "Swarm Coordinator", action: "Agent rebalanced", detail: "Shifted load from Engineer to Researcher", severity: "info" },
  { type: "security", actor: "Constitutional Engine", action: "Law veto triggered", detail: "Blocked action violating Article XIV (rate limits)", severity: "critical" },
  { type: "platform", actor: "TikTok Agent", action: "Post published", detail: "Scheduled reel published to tiktok-01", severity: "success" },
  { type: "system", actor: "Backup Manager", action: "Snapshot verified", detail: "SHA-256 integrity check passed", severity: "success" },
];
