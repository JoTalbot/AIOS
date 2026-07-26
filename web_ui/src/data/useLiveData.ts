import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AgentProfile,
  AndroidDevice,
  AuditEvent,
  HealthStatus,
  LiveData,
  OlxAd,
  OlxSummary,
  PlatformInfo,
  SafetyData,
  SystemStats,
} from "../types";
import { apiUrl } from "../lib/api";
import {
  AGENT_ROSTER,
  AUDIT_TEMPLATES,
  DEVICE_ROSTER,
  PLATFORMS,
  SAFETY_METRIC_KEYS,
  SAMPLE_ADS,
  SERVICE_ROSTER,
  SUBSCRIPTIONS_SEED,
} from "./mockData";

/** Public shape consumed by every dashboard view. */
export interface UseLiveData extends LiveData {
  connectors: PlatformInfo[];
  ads: OlxAd[];
  error: string | null;
  refresh: () => void;
}

const SERIES_LENGTH = 24;
const BOOT_TIME = Date.now();

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function pushRolling(arr: number[], value: number, length = SERIES_LENGTH): number[] {
  const next = [...arr, value];
  return next.length > length ? next.slice(next.length - length) : next;
}

function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function seedSeries(base: number, spread: number): number[] {
  return Array.from({ length: SERIES_LENGTH }, () => Math.max(0, base + rand(-spread, spread)));
}

function initialStats(): SystemStats {
  return {
    version: "11.2.0",
    runtime: "Python 3.12 · asyncio",
    uptime_seconds: 0,
    total_tasks: 842_310,
    completed_tasks: 838_640,
    failed_tasks: 1_120,
    active_agents: AGENT_ROSTER.filter((a) => a.status === "executing").length,
    memory_nodes: 61_204,
    registered_capabilities: 428,
    constitutional_articles: 67,
    compliance_ratio: 0.994,
    safety_score: 0.972,
    api_routes: 186,
    tests_passed: 234,
    platforms: PLATFORMS.length,
    tasks_per_min: 46,
    p95_latency_ms: 118,
  };
}

function initialSafety(): SafetyData {
  return {
    safety_score: 0.972,
    status: "healthy",
    metrics: {
      "Ban Risk Index": 0.041,
      "Detection Probability": 0.028,
      "Rate-Limit Pressure": 0.18,
      "Anomaly Score": 0.052,
    },
    thresholds: {
      "Ban Risk Index": 0.15,
      "Detection Probability": 0.1,
      "Rate-Limit Pressure": 0.6,
      "Anomaly Score": 0.2,
    },
    incidents: [
      { id: uid("inc"), severity: "warning", description: "Instagram profile insta-01 briefly rate-limited; auto-throttled and recovered.", timestamp: Date.now() - 42 * 60_000, resolved: true },
      { id: uid("inc"), severity: "info", description: "Scheduled model registry sync completed with no drift detected.", timestamp: Date.now() - 3 * 3_600_000, resolved: true },
    ],
  };
}

function initialOlx(): OlxSummary {
  return { available: true, ads_total: 48_210, ads_active: 31_040, new_24h: 612, price_avg: 9840 };
}

function buildInitialState() {
  return {
    stats: initialStats(),
    series: {
      tasks: seedSeries(46, 8),
      compliance: seedSeries(99.4, 0.4),
      latency: seedSeries(118, 25),
      throughput: seedSeries(640, 90),
    } as LiveData["series"],
    services: SERVICE_ROSTER.map((s) => ({ ...s })),
    olx: initialOlx(),
    ads: SAMPLE_ADS.map((a) => ({ ...a })),
    audit: AUDIT_TEMPLATES.slice(0, 6).map((t, i) => ({
      id: uid("audit"),
      ts: Date.now() - i * 4 * 60_000,
      ...t,
    })) as AuditEvent[],
    agents: AGENT_ROSTER.map((a) => ({ ...a, trend: seedSeries(a.load, 10) })),
    devices: DEVICE_ROSTER.map((d) => ({ ...d, uptime: Math.floor(rand(600, 500_000)) })),
    connectors: PLATFORMS.map((p) => ({ ...p, trend: seedSeries(Math.max(4, p.actionsToday / 20), 4) })),
    safety: initialSafety(),
    subscriptions: SUBSCRIPTIONS_SEED.map((s) => ({ ...s })),
    health: "ok" as HealthStatus,
    wsConnected: false,
    tick: 0,
  };
}

type EngineState = ReturnType<typeof buildInitialState>;

function advance(prev: EngineState): EngineState {
  const tasksInc = Math.round(rand(28, 62));
  const failInc = Math.random() < 0.08 ? Math.round(rand(0, 2)) : 0;

  const agents: AgentProfile[] = prev.agents.map((a) => {
    let status = a.status;
    if (Math.random() < 0.12) {
      const pool: AgentProfile["status"][] = ["executing", "thinking", "idle", "executing", "executing", "blocked"];
      status = pool[Math.floor(Math.random() * pool.length)];
    }
    const load = clamp(a.load + rand(-8, 8), 3, 96);
    const completed = a.completed_tasks + (status === "executing" ? Math.round(rand(1, 6)) : 0);
    return { ...a, status, load: Math.round(load), completed_tasks: completed, trend: pushRolling(a.trend, load, 16) };
  });

  const connectors: PlatformInfo[] = prev.connectors.map((p) => {
    const delta = p.status === "scaffold" ? rand(0, 2) : rand(2, 26);
    const actionsToday = Math.max(0, Math.round(p.actionsToday + delta));
    const successRate = Math.round(clamp(p.successRate + rand(-1.2, 1.2), 74, 99.6) * 10) / 10;
    return { ...p, actionsToday, successRate, trend: pushRolling(p.trend, delta, 16) };
  });

  const devices: AndroidDevice[] = prev.devices.map((d) => {
    let status = d.status;
    let battery = d.battery;
    if (status !== "offline") {
      battery = clamp(battery - rand(0, 0.6), 0, 100);
      if (battery < 5 && Math.random() < 0.3) status = "offline";
    } else if (Math.random() < 0.05) {
      status = "online";
      battery = clamp(battery + rand(20, 60), 0, 100);
    }
    if (status === "online" && Math.random() < 0.15) status = "busy";
    else if (status === "busy" && Math.random() < 0.25) status = "online";
    return { ...d, status, battery: Math.round(battery), uptime: status === "offline" ? d.uptime : d.uptime + 5 };
  });

  const stats: SystemStats = {
    ...prev.stats,
    uptime_seconds: Math.floor((Date.now() - BOOT_TIME) / 1000) + 6_700_000,
    total_tasks: prev.stats.total_tasks + tasksInc,
    completed_tasks: prev.stats.completed_tasks + Math.max(0, tasksInc - failInc),
    failed_tasks: prev.stats.failed_tasks + failInc,
    active_agents: agents.filter((a) => a.status === "executing").length,
    memory_nodes: prev.stats.memory_nodes + Math.round(rand(0, 14)),
    compliance_ratio: clamp(prev.stats.compliance_ratio + rand(-0.001, 0.0012), 0.97, 1),
    safety_score: clamp(prev.stats.safety_score + rand(-0.004, 0.004), 0.85, 0.999),
    tasks_per_min: tasksInc * (60_000 / 5000),
    p95_latency_ms: Math.round(clamp(prev.stats.p95_latency_ms + rand(-12, 12), 60, 260)),
  };

  const safetyMetrics: Record<string, number> = {};
  for (const key of SAFETY_METRIC_KEYS) {
    const base = prev.safety.metrics[key] ?? 0.05;
    safetyMetrics[key] = clamp(base + rand(-0.006, 0.006), 0.005, 0.5);
  }
  const worstRatio = Math.max(...SAFETY_METRIC_KEYS.map((k) => safetyMetrics[k] / (prev.safety.thresholds[k] ?? 1)));
  const safetyStatus: SafetyData["status"] = worstRatio > 0.85 ? "critical" : worstRatio > 0.55 ? "warning" : "healthy";

  let incidents = prev.safety.incidents;
  if (safetyStatus !== "healthy" && Math.random() < 0.2) {
    incidents = [
      { id: uid("inc"), severity: safetyStatus === "critical" ? "critical" : "warning", description: "Elevated rate-limit pressure detected on an active connector; auto-throttling engaged.", timestamp: Date.now(), resolved: false },
      ...incidents,
    ].slice(0, 20);
  }

  const olx: OlxSummary = {
    available: true,
    ads_total: prev.olx.ads_total + Math.round(rand(0, 9)),
    ads_active: Math.max(0, Math.round(prev.olx.ads_active + rand(-6, 12))),
    new_24h: Math.max(0, Math.round(prev.olx.new_24h + rand(-4, 6))),
    price_avg: Math.round(clamp(prev.olx.price_avg + rand(-60, 60), 500, 80_000)),
  };

  let audit = prev.audit;
  if (Math.random() < 0.55) {
    const template = AUDIT_TEMPLATES[Math.floor(Math.random() * AUDIT_TEMPLATES.length)];
    const event: AuditEvent = { id: uid("audit"), ts: Date.now(), ...template };
    audit = [event, ...prev.audit].slice(0, 200);
  }

  let subscriptions = prev.subscriptions;
  if (Math.random() < 0.15) {
    subscriptions = prev.subscriptions.map((s) => (s.active && Math.random() < 0.4 ? { ...s, matches: s.matches + 1 } : s));
  }

  const health: HealthStatus = safetyStatus === "critical" ? "error" : safetyStatus === "warning" ? "degraded" : "ok";

  return {
    stats,
    series: {
      tasks: pushRolling(prev.series.tasks, tasksInc),
      compliance: pushRolling(prev.series.compliance, stats.compliance_ratio * 100),
      latency: pushRolling(prev.series.latency, stats.p95_latency_ms),
      throughput: pushRolling(prev.series.throughput, connectors.reduce((a, p) => a + p.actionsToday, 0)),
    },
    services: prev.services.map((s) => (s.active ? { ...s, cpu: Math.round(clamp(s.cpu + rand(-3, 3), 0, 95)) } : s)),
    olx,
    ads: prev.ads,
    audit,
    agents,
    devices,
    connectors,
    safety: { safety_score: stats.safety_score, status: safetyStatus, metrics: safetyMetrics, thresholds: prev.safety.thresholds, incidents },
    subscriptions,
    health,
    wsConnected: prev.wsConnected,
    tick: prev.tick + 1,
  };
}

/**
 * Drives the AIOS Control Plane dashboard.
 *
 * Runs a self-contained, continuously-evolving telemetry simulation seeded
 * from real repository metrics (module counts, test counts, constitution
 * article count, connector roster) so every view has realistic live data
 * out of the box. Opportunistically opens a WebSocket to `/ws/dashboard`
 * (the real event bus in `aios_core/ws_dashboard.py`) and, when reachable,
 * folds genuine price-drop / autowatch events into the audit stream —
 * without that backend running, the dashboard still functions fully on
 * the simulation alone.
 */
export function useLiveData(intervalMs = 5000): UseLiveData {
  const [state, setState] = useState<EngineState>(() => buildInitialState());
  const [error] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setState((prev) => advance(prev)), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    const connect = () => {
      if (cancelled) return;
      let socket: WebSocket;
      try {
        const httpUrl = new URL(apiUrl("ws/dashboard"));
        httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
        socket = new WebSocket(httpUrl.toString());
      } catch {
        return;
      }
      wsRef.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        setState((prev) => ({ ...prev, wsConnected: true }));
      };
      socket.onclose = () => {
        if (cancelled) return;
        setState((prev) => ({ ...prev, wsConnected: false }));
        retryTimer = window.setTimeout(connect, 15_000);
      };
      socket.onerror = () => {
        socket.close();
      };
      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string);
          if (!msg?.type || msg.type === "pong") return;
          const detail = typeof msg.payload === "object" ? JSON.stringify(msg.payload).slice(0, 140) : String(msg.payload ?? "");
          const entry: AuditEvent = {
            id: uid("ws"),
            ts: msg.timestamp ? msg.timestamp * 1000 : Date.now(),
            type: "platform",
            actor: msg.source || "event-bus",
            action: String(msg.type).replace(/_/g, " "),
            detail,
            severity: "info",
          };
          setState((prev) => ({ ...prev, audit: [entry, ...prev.audit].slice(0, 200) }));
        } catch {
          // ignore malformed frames
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, []);

  const refresh = useCallback(() => {
    setState((prev) => advance(prev));
  }, []);

  return { ...state, ads: state.ads, error, refresh };
}
