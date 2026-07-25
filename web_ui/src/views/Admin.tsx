import { useEffect, useState } from "react";
import { KeyRound, DatabaseBackup, Plus, CheckCircle2, ShieldCheck, Trash2, RefreshCw, HardDrive, Clock } from "lucide-react";
import { Card, PanelHeader, Badge, IconButton } from "../components/ui/primitives";
import { apiGet, apiPost } from "../lib/api";
import type { Backup } from "../types";

interface LiveBackup extends Backup {
  checksum?: string;
  tables?: number;
}

export function Admin() {
  const [backups, setBackups] = useState<LiveBackup[]>([]);
  const [token, setToken] = useState(() => window.sessionStorage.getItem("aios_control_token") || "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadBackups = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await apiGet<{ backups: LiveBackup[] }>("api/backups");
      setBackups(result.backups || []);
      setToken(window.sessionStorage.getItem("aios_control_token") || token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { loadBackups(); }, []);

  const saveToken = () => {
    if (token.trim()) {
      window.sessionStorage.setItem("aios_control_token", token.trim());
      setMessage("Control token stored for this browser tab only.");
      loadBackups();
    } else {
      window.sessionStorage.removeItem("aios_control_token");
      setMessage("Control token cleared.");
    }
  };

  const createBackup = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await apiPost<{ ok: boolean; backup: LiveBackup }>("api/backups", { action: "create", label: "dashboard" });
      setBackups((items) => [result.backup, ...items]);
      setMessage(`Backup ${result.backup.id} created and checksummed.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (id: string) => {
    setBusy(true);
    try {
      const result = await apiPost<{ verified: boolean }>("api/backups", { action: "verify", backup_id: id });
      setBackups((items) => items.map((b) => b.id === id ? { ...b, verified: result.verified } : b));
      setMessage(result.verified ? `${id} passed integrity verification.` : `${id} failed verification.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const totalSize = backups.reduce((sum, item) => sum + item.size_mb, 0);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Control auth", value: token ? "Loaded" : "Required", icon: ShieldCheck, tone: token ? "emerald" : "amber" },
          { label: "Backups", value: backups.length, icon: DatabaseBackup, tone: "indigo" },
          { label: "Verified", value: backups.filter((b) => b.verified).length, icon: CheckCircle2, tone: "emerald" },
          { label: "Backup storage", value: `${totalSize.toFixed(2)} MB`, icon: HardDrive, tone: "cyan" },
        ].map((item) => (
          <Card key={item.label} className="flex items-center gap-3 p-4">
            <div className={`grid h-10 w-10 place-items-center rounded-xl bg-${item.tone}-500/10 text-${item.tone}-300`}><item.icon className="h-5 w-5" /></div>
            <div><div className="text-xl font-extrabold tabular text-white">{item.value}</div><div className="text-[11px] uppercase tracking-wide text-slate-500">{item.label}</div></div>
          </Card>
        ))}
      </div>

      {message && <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-xs text-slate-300">{message}</div>}

      <Card>
        <PanelHeader icon={<KeyRound className="h-[18px] w-[18px]" />} title="Control Access" subtitle="Required for service, Android, model, collector and backup mutations" />
        <div className="flex flex-col gap-3 sm:flex-row">
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste control token" className="min-w-0 flex-1 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2.5 font-mono text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-400/50" />
          <button onClick={saveToken} className="rounded-xl bg-indigo-500/90 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500">Save for tab</button>
          <button onClick={() => { setToken(""); window.sessionStorage.removeItem("aios_control_token"); setMessage("Control token cleared."); }} className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-white/[0.04] px-4 py-2.5 text-xs font-medium text-slate-300 ring-1 ring-inset ring-white/10"><Trash2 className="h-3.5 w-3.5" /> Clear</button>
        </div>
        <p className="mt-3 text-[11px] text-slate-500">The token is never persisted by the dashboard; it remains in sessionStorage and is sent only as the X-AIOS-Control-Token header.</p>
      </Card>

      <Card>
        <PanelHeader icon={<DatabaseBackup className="h-[18px] w-[18px]" />} title="SQLite Backups" subtitle="Live online backups with SHA-256 integrity checks" action={
          <div className="flex gap-2">
            <IconButton disabled={busy} onClick={loadBackups} title="Refresh"><RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} /></IconButton>
            <button disabled={busy} onClick={createBackup} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-500/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"><Plus className="h-3.5 w-3.5" /> Create backup</button>
          </div>
        } />
        <div className="space-y-2">
          {backups.map((backup) => (
            <div key={backup.id} className="grid grid-cols-12 items-center gap-3 rounded-xl bg-white/[0.02] p-3 ring-1 ring-inset ring-white/[0.04]">
              <div className="col-span-12 min-w-0 sm:col-span-5">
                <div className="truncate font-mono text-xs font-semibold text-slate-200">{backup.id}</div>
                <div className="mt-1 inline-flex items-center gap-1 text-[10px] text-slate-500"><Clock className="h-3 w-3" /> {new Date(backup.created).toLocaleString()}</div>
              </div>
              <div className="col-span-4 sm:col-span-2"><Badge tone="slate">{backup.kind}</Badge></div>
              <div className="col-span-4 text-xs tabular text-slate-400 sm:col-span-2">{backup.size_mb.toFixed(3)} MB</div>
              <div className="col-span-2 sm:col-span-2">{backup.verified === true ? <Badge tone="emerald">verified</Badge> : backup.verified === false ? <Badge tone="rose">failed</Badge> : <Badge tone="slate">unchecked</Badge>}</div>
              <div className="col-span-2 text-right sm:col-span-1"><IconButton disabled={busy} tone="emerald" onClick={() => verify(backup.id)} title="Verify"><CheckCircle2 className="h-4 w-4" /></IconButton></div>
            </div>
          ))}
          {!backups.length && <div className="py-12 text-center text-sm text-slate-500">No backups yet. Create the first verified snapshot.</div>}
        </div>
      </Card>
    </div>
  );
}
