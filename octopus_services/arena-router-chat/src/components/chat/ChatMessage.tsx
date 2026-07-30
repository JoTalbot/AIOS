"use client";

import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Brain,
  Check,
  CircleX,
  Clock,
  Copy,
  FileText,
  RefreshCw,
  Sparkles,
  User,
} from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/lib/chat/types";
import { findModel } from "@/lib/arena/models";

interface Props {
  message: ChatMessageType;
  onRegenerate?: () => void;
  canRegenerate?: boolean;
}


// ── Multimodal user content (text + images + files) ─────────────────────
function UserContent({ message }: { message: ChatMessageType }) {
  const parts: Array<{ kind: "text"; text: string } | { kind: "image"; url: string; name?: string } | { kind: "file"; url: string; name: string; mime: string }> = [];
  if (typeof message.content === "string") {
    if (message.content.trim()) parts.push({ kind: "text", text: message.content });
  } else if (Array.isArray(message.content)) {
    for (const p of message.content) {
      if (p.type === "text" && p.text.trim()) parts.push({ kind: "text", text: p.text });
      else if (p.type === "image_url") parts.push({ kind: "image", url: p.image_url.url });
      else if (p.type === "file") parts.push({ kind: "file", url: p.file.url, name: p.file.name, mime: p.file.mime });
    }
  }
  // also render legacy attachments if present
  const legacy = (message as any).attachments as Array<{ kind: string; url: string; name: string; mime: string }> | undefined;
  if (legacy && Array.isArray(legacy)) {
    for (const a of legacy) {
      if (a.kind === "image") parts.push({ kind: "image", url: a.url, name: a.name });
      else parts.push({ kind: "file", url: a.url, name: a.name, mime: a.mime });
    }
  }
  return (
    <div className="space-y-2">
      {parts.some(p => p.kind === "image") && (
        <div className="grid grid-cols-2 gap-1.5">
          {parts.filter(p => p.kind === "image").map((p, i) =>
            p.kind === "image" ? (
              <a key={i} href={p.url} target="_blank" rel="noopener noreferrer" className="block rounded-lg overflow-hidden bg-black/10">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.url} alt={p.name || "attachment"} className="w-full h-auto max-h-64 object-cover" />
              </a>
            ) : null
          )}
        </div>
      )}
      {parts.filter(p => p.kind === "file").map((p, i) =>
        p.kind === "file" ? (
          <a key={`f${i}`} href={p.url} target="_blank" rel="noopener noreferrer"
             className="flex items-center gap-2 rounded-lg bg-black/5 px-3 py-2 text-xs no-underline hover:bg-black/10">
            <FileText className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span className="truncate">{p.name}</span>
          </a>
        ) : null
      )}
      {parts.filter(p => p.kind === "text").map((p, i) =>
        p.kind === "text" ? (
          <p key={`t${i}`} className="whitespace-pre-wrap break-words text-sm">{p.text}</p>
        ) : null
      )}
    </div>
  );
}

function ChatMessageImpl({ message, onRegenerate, canRegenerate }: Props) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const model = message.model ? findModel(message.model) : undefined;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be blocked in some contexts */
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} group`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg grid place-items-center text-xs font-bold ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      {/* Bubble */}
      <div className={`flex-1 min-w-0 max-w-[85%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        {/* Header: model + elapsed */}
        {isAssistant && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {model ? (
              <Badge variant="outline" className="text-[10px] gap-1">
                {model.thinking && <Brain className="w-2.5 h-2.5" />}
                {model.id}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px]">assistant</Badge>
            )}
            {message.elapsed_ms != null && (
              <span className="flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                {(message.elapsed_ms / 1000).toFixed(1)}s
              </span>
            )}
            {message.streaming && (
              <span className="flex items-center gap-1 text-primary animate-pulse">
                <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                streaming…
              </span>
            )}
          </div>
        )}

        {/* Content */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-muted/50 rounded-tl-sm"
          } ${message.error ? "border border-destructive/40 bg-destructive/5" : ""}`}
        >
          {isUser ? (
            <UserContent message={message} />
          ) : message.error ? (
            <div className="flex items-start gap-2 text-sm text-destructive">
              <CircleX className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Generation failed</p>
                <p className="text-xs opacity-80">{message.error}</p>
              </div>
            </div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none break-words">
              <ReactMarkdown
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code
                          className="px-1 py-0.5 rounded bg-muted-foreground/15 text-xs font-mono"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }
                    return (
                      <SyntaxHighlighter

                        style={oneDark as any}
                        language={match?.[1] ?? "text"}
                        PreTag="div"
                        customStyle={{
                          margin: 0,
                          borderRadius: "0.5rem",
                          fontSize: "0.75rem",
                        }}
                        codeTagProps={{ style: { fontFamily: "var(--font-geist-mono), monospace" } }}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    );
                  },
                  a: ({ children, ...props }) => (
                    <a
                      {...props}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline underline-offset-2"
                    >
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content || (message.streaming ? "…" : "(empty)")}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer: actions */}
        {isAssistant && !message.streaming && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => void copy()}>
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? "Copied" : "Copy"}
            </Button>
            {canRegenerate && onRegenerate && (
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs"
                onClick={onRegenerate}
              >
                <RefreshCw className="w-3 h-3" />
                Regenerate
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export const ChatMessage = memo(ChatMessageImpl);
