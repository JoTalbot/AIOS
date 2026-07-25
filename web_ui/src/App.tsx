import { useEffect, useState } from "react";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { CommandPalette } from "./components/layout/CommandPalette";
import { findItem, type ViewId } from "./components/layout/nav";
import { useLiveData } from "./data/useLiveData";
import { clockTime } from "./lib/format";
import { cn } from "./utils/cn";

import { Overview } from "./views/Overview";
import { Platforms } from "./views/Platforms";
import { OLX } from "./views/OLX";
import { Swarm } from "./views/Swarm";
import { Safety } from "./views/Safety";
import { Constitution } from "./views/Constitution";
import { Fleet } from "./views/Fleet";
import { Services } from "./views/Services";
import { Audit } from "./views/Audit";
import { KnowledgeGraph } from "./views/KnowledgeGraph";
import { MLRegistry } from "./views/MLRegistry";
import { Admin } from "./views/Admin";

export default function App() {
  const data = useLiveData(5000);
  const [view, setView] = useState<ViewId>("overview");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [clock, setClock] = useState(clockTime(new Date()));

  // Live clock
  useEffect(() => {
    const id = setInterval(() => setClock(clockTime(new Date())), 1000);
    return () => clearInterval(id);
  }, []);

  // Command palette shortcut
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((o) => !o);
      } else if (e.key === "Escape") {
        setCommandOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Scroll to top on view change
  useEffect(() => {
    document.querySelector("main")?.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }, [view]);

  const item = findItem(view);
  const navigate = (id: ViewId) => setView(id);
  const criticalCount = data.audit.filter((a) => a.severity === "critical" || a.severity === "warning").length;

  const renderView = () => {
    switch (view) {
      case "overview":
        return <Overview data={data} onNavigate={navigate} />;
      case "safety":
        return <Safety data={data} />;
      case "constitution":
        return <Constitution />;
      case "audit":
        return <Audit data={data} />;
      case "platforms":
        return <Platforms data={data} />;
      case "olx":
        return <OLX data={data} />;
      case "fleet":
        return <Fleet data={data} />;
      case "swarm":
        return <Swarm data={data} />;
      case "kg":
        return <KnowledgeGraph />;
      case "ml":
        return <MLRegistry />;
      case "services":
        return <Services data={data} />;
      case "admin":
        return <Admin />;
      default:
        return <Overview data={data} onNavigate={navigate} />;
    }
  };

  return (
    <div className="app-bg min-h-screen text-slate-200">
      <Sidebar
        active={view}
        onNavigate={navigate}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        health={data.health}
        version={data.stats.version}
        safety={data.stats.safety_score}
      />

      <div className={cn("transition-[padding] duration-300", collapsed ? "lg:pl-[76px]" : "lg:pl-[256px]")}>
        <Topbar
          title={item.label}
          subtitle={item.description}
          onMenu={() => setMobileOpen(true)}
          onOpenCommand={() => setCommandOpen(true)}
          wsConnected={data.wsConnected}
          health={data.health}
          clock={clock}
          tasksPerMin={data.stats.tasks_per_min}
          notifications={criticalCount}
        />
        <main className="mx-auto max-w-[1520px] p-4 sm:p-6">
          {data.error && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
              <span>{data.error}</span>
              <button onClick={data.refresh} className="rounded-lg bg-rose-400/10 px-2.5 py-1 font-semibold hover:bg-rose-400/20">Retry</button>
            </div>
          )}
          <div key={view} className="animate-fade-in">
            {renderView()}
          </div>
          <footer className="mt-10 flex flex-col items-center justify-between gap-2 border-t border-white/[0.05] py-6 text-[11px] text-slate-600 sm:flex-row">
            <span>
              AIOS Control Plane · v{data.stats.version} · {data.stats.runtime}
            </span>
            <span>Application Intelligence Operating System — self-evolving distributed runtime</span>
          </footer>
        </main>
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} onNavigate={navigate} />
    </div>
  );
}
