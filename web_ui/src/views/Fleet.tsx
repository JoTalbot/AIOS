import { useEffect, useState } from "react";
import {
  Smartphone, Battery, MapPin, Power, RotateCw, Camera, Clock, Cpu, HardDrive, Wifi,
  Home, Undo2, Play,
} from "lucide-react";
import { Card, PanelHeader, Badge, Progress, IconButton, StatusPill } from "../components/ui/primitives";
import { formatTime } from "../lib/format";
import { PLATFORMS } from "../data/mockData";
import { apiGet, apiPost } from "../lib/api";
import { cn } from "../utils/cn";
import type { AndroidDevice } from "../types";
import type { UseLiveData } from "../data/useLiveData";

const STATUS_TONE: Record<AndroidDevice["status"], any> = { online: "emerald", busy: "amber", offline: "slate" };
const STATUS_LABEL: Record<AndroidDevice["status"], string> = { online: "Online · idle", busy: "Busy · executing", offline: "Offline" };

function platformEmoji(id: string) {
  return PLATFORMS.find((p) => p.id === id)?.emoji ?? "📱";
}

export function Fleet({ data }: { data: UseLiveData }) {
  const devices = data.devices;
  const [selSerial, setSelSerial] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [screen, setScreen] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState({ width: 1080, height: 2280 });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selSerial && devices[0]) setSelSerial(devices[0].serial);
    if (selSerial && devices.length && !devices.some((d) => d.serial === selSerial)) setSelSerial(devices[0].serial);
  }, [devices, selSerial]);

  const selected = devices.find((d) => d.serial === selSerial) ?? devices[0];
  const online = devices.filter((d) => d.status !== "offline").length;
  const executing = devices.filter((d) => d.status === "busy").length;

  const action = async (name: string, args: Record<string, unknown> = {}) => {
    const serial = String(args.serial || selected?.serial || "");
    if (!serial) return;
    setMessage(null);
    try {
      const result = await apiPost<{ ok: boolean; error?: string }>("api/android/action", { action: name, serial, ...args });
      if (!result.ok) throw new Error(result.error || `${name} failed`);
      setMessage(`${name} completed on ${serial}`);
      window.setTimeout(() => data.refresh(), 500);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  };

  const capture = async (serial = selected?.serial) => {
    if (!serial) return;
    setSelSerial(serial);
    setCapturing(true);
    setMessage(null);
    try {
      const result = await apiGet<{ ok: boolean; image?: string; error?: string }>(`api/android/screenshot?serial=${encodeURIComponent(serial)}`);
      if (!result.ok || !result.image) throw new Error(result.error || "Screenshot failed");
      setScreen(result.image);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setCapturing(false);
    }
  };

  const tapScreen = async (event: React.MouseEvent<HTMLImageElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.round((event.clientX - rect.left) / rect.width * imageSize.width);
    const y = Math.round((event.clientY - rect.top) / rect.height * imageSize.height);
    await action("tap", { x, y });
    window.setTimeout(() => capture(), 450);
  };

  const reboot = async (serial = selected?.serial) => {
    if (!serial || !window.confirm(`Reboot ${serial}?`)) return;
    await action("shell", { serial, command: "reboot" });
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Devices in pool", value: devices.length, icon: Smartphone, tone: "indigo" },
          { label: "Online", value: online, icon: Wifi, tone: "emerald" },
          { label: "Executing", value: executing, icon: Cpu, tone: "amber" },
          { label: "Hosts", value: new Set(devices.map((d) => d.host)).size, icon: HardDrive, tone: "cyan" },
        ].map((s) => (
          <Card key={s.label} className="flex items-center gap-3 p-4">
            <div className={`grid h-10 w-10 place-items-center rounded-xl bg-${s.tone}-500/10 text-${s.tone}-300`}><s.icon className="h-5 w-5" /></div>
            <div><div className="text-xl font-extrabold tabular text-white">{s.value}</div><div className="text-[11px] uppercase tracking-wide text-slate-500">{s.label}</div></div>
          </Card>
        ))}
      </div>

      {message && <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-xs text-slate-300">{message}</div>}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <PanelHeader icon={<Smartphone className="h-[18px] w-[18px]" />} title="Device Pool" subtitle="Live ADB devices · screenshot, power and remote input" />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {devices.map((d) => {
              const isSel = d.serial === selected?.serial;
              return (
                <div key={d.serial} onClick={() => setSelSerial(d.serial)} className={cn("cursor-pointer rounded-2xl border p-4 transition-all", isSel ? "border-indigo-400/40 bg-indigo-500/[0.07]" : "border-white/[0.06] bg-white/[0.02] hover:border-white/15")}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-white/[0.04] text-lg ring-1 ring-inset ring-white/[0.06]">
                        {platformEmoji(d.platform)}
                        <span className={cn("absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-[#0d1220]", `bg-${STATUS_TONE[d.status]}-400`)} />
                      </div>
                      <div><div className="text-sm font-bold text-white">{d.model}</div><div className="font-mono text-[10px] text-slate-500">{d.serial}</div></div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <StatusPill tone={STATUS_TONE[d.status]} label={STATUS_LABEL[d.status]} />
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-500"><Battery className={cn("h-3.5 w-3.5", d.battery < 20 ? "text-rose-400" : "text-slate-400")} /><span className="tabular font-medium text-slate-300">{d.battery}%</span></span>
                  </div>
                  <Progress value={d.battery} tone={d.battery < 20 ? "rose" : "emerald"} className="mt-2" />
                  <div className="mt-3 flex items-center justify-between border-t border-white/[0.05] pt-2.5 text-[11px] text-slate-500">
                    <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {d.host}</span><span className="inline-flex items-center gap-1 font-mono">{d.profile}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                    <IconButton onClick={() => action("power", { serial: d.serial })} title="Power key"><Power className="h-4 w-4" /></IconButton>
                    <IconButton onClick={() => reboot(d.serial)} title="Reboot"><RotateCw className="h-4 w-4" /></IconButton>
                    <IconButton onClick={() => capture(d.serial)} title="Screenshot"><Camera className="h-4 w-4" /></IconButton>
                  </div>
                </div>
              );
            })}
            {!devices.length && <div className="col-span-full py-12 text-center text-sm text-slate-500">No online ADB devices detected.</div>}
          </div>
        </Card>

        <Card>
          <PanelHeader icon={<Camera className="h-[18px] w-[18px]" />} title="Live Screen" subtitle={selected?.serial || "No device"} action={
            <button disabled={!selected || capturing} onClick={() => capture()} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-500/90 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"><Camera className="h-3.5 w-3.5" /> Capture</button>
          } />
          <div className="mx-auto w-full max-w-[250px]">
            <div className="relative rounded-[2rem] border-[6px] border-[#1a2236] bg-black p-2 shadow-2xl">
              <div className="absolute left-1/2 top-2 z-10 h-1.5 w-12 -translate-x-1/2 rounded-full bg-[#1a2236]" />
              <div className={cn("relative aspect-[9/19] overflow-hidden rounded-[1.5rem] bg-gradient-to-b from-slate-900 to-slate-950", capturing && "shimmer")}>
                {screen ? (
                  <img src={screen} alt={`Screen of ${selected?.serial}`} onLoad={(e) => setImageSize({ width: e.currentTarget.naturalWidth, height: e.currentTarget.naturalHeight })} onClick={tapScreen} className="h-full w-full cursor-crosshair object-contain" />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-3 p-4 text-center">
                    <div className="text-4xl">{selected ? platformEmoji(selected.platform) : "📵"}</div>
                    <div className="text-xs font-bold text-white">{selected ? "Capture live screen" : "No device"}</div>
                    {selected && <Badge tone={STATUS_TONE[selected.status]}>{STATUS_LABEL[selected.status]}</Badge>}
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-2">
            <IconButton disabled={!selected} onClick={() => action("home")} title="Home"><Home className="h-4 w-4" /></IconButton>
            <IconButton disabled={!selected} onClick={() => action("back")} title="Back"><Undo2 className="h-4 w-4" /></IconButton>
            <IconButton disabled={!selected} onClick={() => action("launch", { package: "ua.slando" })} title="Launch OLX"><Play className="h-4 w-4" /></IconButton>
            <IconButton disabled={!selected} onClick={() => action("power")} title="Power key"><Power className="h-4 w-4" /></IconButton>
          </div>
          {selected && <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-white/[0.02] p-2.5 ring-1 ring-inset ring-white/[0.04]"><div className="flex items-center gap-1 text-slate-500"><Clock className="h-3 w-3" /> Uptime</div><div className="mt-0.5 font-semibold tabular text-slate-200">{selected.uptime ? formatTime(selected.uptime) : "live"}</div></div>
            <div className="rounded-lg bg-white/[0.02] p-2.5 ring-1 ring-inset ring-white/[0.04]"><div className="flex items-center gap-1 text-slate-500"><Cpu className="h-3 w-3" /> Profile</div><div className="mt-0.5 truncate font-mono text-[11px] text-slate-200">{selected.profile}</div></div>
          </div>}
        </Card>
      </div>
    </div>
  );
}
