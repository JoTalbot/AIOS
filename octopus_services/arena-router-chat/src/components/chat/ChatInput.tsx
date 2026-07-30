"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  Loader2,
  Paperclip,
  Settings2,
  Square,
  Send,
  X,
  Image as ImageIcon,
  FileText,
} from "lucide-react";
import { AGENT_PRESETS, PRESET_BY_ID } from "@/lib/chat/types";
import type { AgentPreset, Attachment } from "@/lib/chat/types";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: (attachments: Attachment[]) => void;
  onStop: () => void;
  loading: boolean;
  systemPrompt: string;
  onSystemPromptChange: (v: string) => void;
  agentPresetId: string;
  onAgentPresetChange: (id: string) => void;
  disabled?: boolean;
}

const ALLOWED_MIME = "image/png,image/jpeg,image/webp,image/gif,application/pdf";
const MAX_FILE_SIZE = 20 * 1024 * 1024;

export function ChatInput({
  value,
  onChange,
  onSend,
  onStop,
  loading,
  systemPrompt,
  onSystemPromptChange,
  agentPresetId,
  onAgentPresetChange,
  disabled,
}: Props) {
  const [showSettings, setShowSettings] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activePreset = PRESET_BY_ID.get(agentPresetId);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 240) + "px";
  }, [value]);

  const handleFiles = useCallback(async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (!files.length) return;
    setUploadError(null);

    // Basic client checks
    for (const f of files) {
      if (!ALLOWED_MIME.split(",").includes(f.type) && f.type !== "") {
        setUploadError(`Непідтримуваний тип файлу: ${f.name} (${f.type}). Дозволено PNG/JPG/WebP/GIF/PDF.`);
        return;
      }
      if (f.size > MAX_FILE_SIZE) {
        setUploadError(`Файл занадто великий: ${f.name} (${(f.size/1024/1024).toFixed(1)} МБ). Макс. 20 МБ.`);
        return;
      }
    }

    setUploading(true);
    try {
      const fd = new FormData();
      for (const f of files) fd.append("file", f, f.name);
      const res = await fetch("/chat/api/upload", { method: "POST", body: fd });
      const j = await res.json();
      if (!res.ok || !j.ok) {
        throw new Error(j?.error || `Upload failed: ${res.status}`);
      }
      setAttachments((prev) => [...prev, ...j.files]);
    } catch (e: any) {
      setUploadError(e?.message || String(e));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, []);

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData.items || []);
    const files: File[] = [];
    for (const it of items) {
      if (it.kind === "file") {
        const f = it.getAsFile();
        if (f) files.push(f);
      }
    }
    if (files.length) {
      e.preventDefault();
      void handleFiles(files);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !loading && (value.trim() || attachments.length)) {
      e.preventDefault();
      send();
    }
  };

  const send = () => {
    if (loading) return;
    if (!value.trim() && !attachments.length) return;
    onSend(attachments);
    setAttachments([]);
  };

  return (
    <div className="border-t bg-background/80 backdrop-blur p-3 space-y-2">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1">Agent:</span>
        {AGENT_PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => onAgentPresetChange(p.id)}
            className={`text-xs px-2 py-1 rounded-full border transition ${
              p.id === agentPresetId
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background hover:bg-muted border-border"
            }`}
            title={p.description}
          >
            {p.name}
          </button>
        ))}
      </div>

      {showSettings && (
        <div className="border rounded-md p-2 space-y-2 bg-muted/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">System prompt</span>
            {activePreset && (
              <Badge variant="outline" className="text-[10px]">
                Preset: {activePreset.name}
              </Badge>
            )}
          </div>
          <Textarea
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            placeholder="System prompt (shapes the assistant's behavior)"
            className="text-xs min-h-[60px] max-h-[120px]"
          />
          {activePreset?.starterPrompt && (
            <Button
              size="sm"
              variant="outline"
              className="text-xs h-6"
              onClick={() => onChange(activePreset.starterPrompt!)}
            >
              Use starter prompt
            </Button>
          )}
        </div>
      )}

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {attachments.map((a) => (
            <div
              key={a.id}
              className="relative flex items-center gap-2 pl-2 pr-7 py-1 border rounded-lg bg-muted/40 text-xs"
            >
              {a.kind === "image" ? (
                <div className="w-8 h-8 rounded overflow-hidden bg-black/5 grid place-items-center flex-shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={a.url} alt={a.name} className="w-full h-full object-cover" />
                </div>
              ) : a.kind === "pdf" ? (
                <FileText className="w-4 h-4 text-rose-600 flex-shrink-0" />
              ) : (
                <Paperclip className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              )}
              <span className="max-w-[160px] truncate">{a.name}</span>
              <span className="text-muted-foreground">
                {(a.size / 1024).toFixed(0)}KB
              </span>
              <button
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-destructive-foreground grid place-items-center hover:bg-destructive/80"
                onClick={() => removeAttachment(a.id)}
                title="Видалити"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
      {uploadError && (
        <p className="text-xs text-destructive">{uploadError}</p>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALLOWED_MIME}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
          }}
        />
        <Button
          size="icon"
          variant="outline"
          className="h-10 w-10"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || loading || uploading}
          title="Прикріпити файл (PNG/JPG/WebP/GIF/PDF до 20МБ)"
        >
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Paperclip className="w-4 h-4" />
          )}
        </Button>
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={onPaste}
            placeholder={
              activePreset?.starterPrompt
                ? `Message (${activePreset.name})… Shift+Enter нова строка. Скріншоти/фото/PDF через 📎 або Ctrl+V`
                : "Message… (Enter надсилання, Shift+Enter нова строка, 📎 для фото/PDF, Ctrl+V для скріншоту)"
            }
            disabled={disabled}
            className="min-h-[44px] max-h-[240px] resize-none pr-10"
            rows={1}
          />
        </div>
        <Button
          size="icon"
          variant="outline"
          className="h-10 w-10"
          onClick={() => setShowSettings((s) => !s)}
          title="System prompt settings"
        >
          {showSettings ? <ChevronDown className="w-4 h-4" /> : <Settings2 className="w-4 h-4" />}
        </Button>
        {loading ? (
          <Button
            size="icon"
            variant="destructive"
            className="h-10 w-10"
            onClick={onStop}
            title="Stop generation"
          >
            <Square className="w-4 h-4" />
          </Button>
        ) : (
          <Button
            size="icon"
            className="h-10 w-10"
            onClick={send}
            disabled={disabled || (!value.trim() && !attachments.length)}
            title="Send (Enter)"
          >
            <Send className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
