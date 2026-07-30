"use client";

import { useMemo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Brain, Image as ImageIcon, Search } from "lucide-react";

export interface ModelEntry {
  id: string;
  arena: {
    label: string;
    provider: string;
    description?: string;
    thinking?: boolean;
    vision?: boolean;
  };
}

interface Props {
  models: ModelEntry[];
  value: string;
  onChange: (id: string) => void;
}

/**
 * Searchable model picker.
 *
 * The trigger shows the current model id. When opened, the dropdown shows a
 * search box and the full list grouped by provider. The picker is fully
 * keyboard-navigable via the underlying Select component.
 */
export function ModelPicker({ models, value, onChange }: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) return models;
    const q = query.toLowerCase();
    return models.filter(
      (m) =>
        m.id.toLowerCase().includes(q) ||
        m.arena.provider.toLowerCase().includes(q) ||
        m.arena.label.toLowerCase().includes(q),
    );
  }, [models, query]);

  const grouped = useMemo(() => {
    const providers = Array.from(new Set(filtered.map((m) => m.arena.provider))).sort();
    return providers.map((p) => ({
      provider: p,
      models: filtered.filter((m) => m.arena.provider === p),
    }));
  }, [filtered]);

  const current = models.find((m) => m.id === value);

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="min-w-[200px]">
        <SelectValue placeholder="Pick a model">
          {current && (
            <span className="flex items-center gap-2">
              {current.arena.thinking && <Brain className="w-3 h-3 text-muted-foreground" />}
              {current.arena.vision && <ImageIcon className="w-3 h-3 text-muted-foreground" />}
              <span className="truncate">{current.id}</span>
            </span>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="max-h-96">
        {/* Search box inside the dropdown */}
        <div className="p-2 border-b sticky top-0 bg-background z-10">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search models…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-8 pl-8 text-xs"
              // Prevent the Select from closing when interacting with the search input.
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => e.stopPropagation()}
            />
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {grouped.length === 0 && (
            <div className="p-4 text-center text-xs text-muted-foreground">
              No models match &quot;{query}&quot;
            </div>
          )}
          {grouped.map((g) => (
            <SelectGroup key={g.provider}>
              <SelectLabel className="text-xs text-muted-foreground">
                {g.provider} ({g.models.length})
              </SelectLabel>
              {g.models.map((m) => (
                <SelectItem key={m.id} value={m.id} className="text-xs">
                  <span className="flex items-center gap-2">
                    {m.id}
                    {m.arena.thinking && (
                      <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5 gap-0.5">
                        <Brain className="w-2 h-2" />thinking
                      </Badge>
                    )}
                    {m.arena.vision && (
                      <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5 gap-0.5">
                        <ImageIcon className="w-2 h-2" />vision
                      </Badge>
                    )}
                  </span>
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </div>
      </SelectContent>
    </Select>
  );
}
