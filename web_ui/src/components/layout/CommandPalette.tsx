import { useEffect, useRef, useState } from "react";
import { Search, CornerDownLeft } from "lucide-react";
import { ALL_ITEMS, type ViewId } from "./nav";
import { cn } from "../../utils/cn";

export function CommandPalette({
  open,
  onClose,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  onNavigate: (id: ViewId) => void;
}) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = ALL_ITEMS.filter(
    (i) => q === "" || i.label.toLowerCase().includes(q.toLowerCase()) || i.description.toLowerCase().includes(q.toLowerCase())
  );

  useEffect(() => {
    if (open) {
      setQ("");
      setSel(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    setSel(0);
  }, [q]);

  if (!open) return null;

  const choose = (id: ViewId) => {
    onNavigate(id);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="glass-strong animate-slide-up relative w-full max-w-xl overflow-hidden rounded-2xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-4">
          <Search className="h-4 w-4 text-slate-500" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setSel((s) => Math.min(results.length - 1, s + 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setSel((s) => Math.max(0, s - 1));
              } else if (e.key === "Enter" && results[sel]) {
                choose(results[sel].id);
              }
            }}
            placeholder="Jump to a view…"
            className="w-full bg-transparent py-4 text-sm text-slate-100 outline-none placeholder:text-slate-600"
          />
          <kbd className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-500">ESC</kbd>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {results.map((item, i) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onMouseEnter={() => setSel(i)}
                onClick={() => choose(item.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                  sel === i ? "bg-indigo-500/15 ring-1 ring-inset ring-indigo-400/30" : "hover:bg-white/[0.03]"
                )}
              >
                <div className={cn("grid h-8 w-8 place-items-center rounded-lg", sel === i ? "bg-indigo-500/20 text-indigo-300" : "bg-white/[0.04] text-slate-400")}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-slate-100">{item.label}</div>
                  <div className="truncate text-[11px] text-slate-500">{item.description}</div>
                </div>
                {sel === i && <CornerDownLeft className="h-3.5 w-3.5 text-slate-500" />}
              </button>
            );
          })}
          {results.length === 0 && (
            <div className="py-10 text-center text-sm text-slate-500">No views match “{q}”.</div>
          )}
        </div>
      </div>
    </div>
  );
}
