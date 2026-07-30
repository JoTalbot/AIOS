"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Toaster } from "@/components/ui/toaster";
import { useToast } from "@/hooks/use-toast";
import {
  Activity,
  CircleCheck,
  CircleDot,
  CircleX,
  KeyRound,
  Loader2,
  LogIn,
  Menu,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Server,
  Shield,
  Sparkles,
  Camera,
  X,
} from "lucide-react";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ModelPicker, type ModelEntry } from "@/components/chat/ModelPicker";
import { ConversationSidebar } from "@/components/chat/ConversationSidebar";
import { ChatInput } from "@/components/chat/ChatInput";
import { WebcamPanel } from "@/components/chat/WebcamPanel";
import type { Conversation, ChatMessage as ChatMessageType } from "@/lib/chat/types";
import { PRESET_BY_ID } from "@/lib/chat/types";
import {
  loadConversations,
  mergeConversations,
  saveConversations,
  fetchConversationsFromServer,
  saveConversationsToServer,
  loadActiveConversationId,
  saveActiveConversationId,
  newId,
  deriveTitle,
} from "@/lib/chat/storage";

interface SessionStatus {
  has_saved_session: boolean;
  logged_in: boolean;
  user_identifier?: string;
  last_verified_at?: string;
  last_error?: string;
}

interface QueueSnapshot {
  busy: boolean;
  current_task_id: string | null;
  pending: number;
}

const LS_API_KEY = "arena_proxy_api_key";

export default function Home() {
  const { toast } = useToast();

  // ─── Core state ──────────────────────────────────────────────────────
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stopRequested, setStopRequested] = useState(false);
  const [agentPresetId, setAgentPresetId] = useState("general");

  // ─── Sidebar / panel visibility ──────────────────────────────────────
  const [showConversations, setShowConversations] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showWebcam, setShowWebcam] = useState(false);

  // ─── Auth / session / queue state ────────────────────────────────────
  const [authRequired, setAuthRequired] = useState<boolean>(false);
  const [apiKey, setApiKey] = useState<string>("");
  const [apiKeySaved, setApiKeySaved] = useState<boolean>(false);
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [queueState, setQueueState] = useState<QueueSnapshot | null>(null);
  const [captchaEnabled, setCaptchaEnabled] = useState<boolean>(false);
  const [captchaService, setCaptchaService] = useState<string>("2captcha");
  const [refreshingSession, setRefreshingSession] = useState(false);
  const [loginInProgress, setLoginInProgress] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);

  // ─── Auth headers helper ─────────────────────────────────────────────
  const authHeaders = useCallback(
    (extra: Record<string, string> = {}): Record<string, string> => {
      const h: Record<string, string> = { ...extra };
      if (authRequired && apiKey) {
        h["Authorization"] = `Bearer ${apiKey}`;
      }
      return h;
    },
    [authRequired, apiKey],
  );

  const authFetch = useCallback(
    async (url: string, init?: RequestInit): Promise<Response> => {
      const headers = authHeaders(
        (init?.headers as Record<string, string>) ?? {},
      );
      return fetch(url, { ...init, headers });
    },
    [authHeaders],
  );

  // ─── Initial load ────────────────────────────────────────────────────
  useEffect(() => {
    void (async () => {
      try {
        const r = await fetch("/chat/api/auth/status");
        const j = await r.json();
        setAuthRequired(j.auth_required === true);
      } catch {
        /* ignore */
      }
    })();
    const savedKey = typeof window !== "undefined" ? localStorage.getItem(LS_API_KEY) ?? "" : "";
    setApiKey(savedKey);
    setApiKeySaved(savedKey.length > 0);
    (async () => {
      const localConv = loadConversations();
      const fromServer = await fetchConversationsFromServer(savedKey);
      if (fromServer !== null) {
        // Merge: migrate old localStorage history into server store.
        const merged = mergeConversations(fromServer, localConv);
        setConversations(merged);
        saveConversations(merged);
        // Persist the merged set back to the server (debounced save-effect
        // handles it, but force a flush so migration is durable on first hit).
        if (merged.length > fromServer.length) {
          void saveConversationsToServer(merged, savedKey);
        }
      } else {
        setConversations(localConv);
      }
    })();
    const savedActive = loadActiveConversationId();
    if (savedActive) setActiveId(savedActive);
  }, []);

  useEffect(() => {
    if (!authRequired) return;
    if (!apiKeySaved) return;
    void fetchModels();
    void fetchSession();
  }, [authRequired, apiKeySaved]);

  useEffect(() => {
    if (!authRequired) {
      void fetchModels();
      void fetchSession();
    }
  }, [authRequired]);

  useEffect(() => {
    void fetchQueue();
    void fetchCaptchaStatus();
    const id = setInterval(fetchQueue, 5000);
    return () => clearInterval(id);
  }, []);

  // Persist conversations: localStorage cache (instant) + server (debounced).
  useEffect(() => {
    saveConversations(conversations);
    const t = setTimeout(() => {
      void saveConversationsToServer(conversations, apiKey);
    }, 800);
    return () => clearTimeout(t);
  }, [conversations, apiKey]);
  useEffect(() => {
    saveActiveConversationId(activeId);
  }, [activeId]);

  // ─── Data fetchers ───────────────────────────────────────────────────
  const fetchModels = useCallback(async () => {
    try {
      const r = await authFetch("/chat/api/v1/models");
      if (r.status === 401) return;
      const j = await r.json();
      setModels(j.data ?? []);
    } catch {
      /* ignore */
    }
  }, [authFetch]);

  const fetchSession = useCallback(async () => {
    setRefreshingSession(true);
    try {
      const r = await authFetch("/chat/api/session");
      if (r.status === 401) {
        setSession({ has_saved_session: false, logged_in: false, last_error: "API key required" });
        return;
      }
      const j = await r.json();
      setSession(j);
    } catch (e) {
      setSession({
        has_saved_session: false,
        logged_in: false,
        last_error: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setRefreshingSession(false);
    }
  }, [authFetch]);

  const fetchQueue = useCallback(async () => {
    try {
      const r = await fetch("/chat/api/health");
      const j = await r.json();
      setQueueState(j.queue);
    } catch {
      /* ignore */
    }
  }, []);

  const fetchCaptchaStatus = useCallback(async () => {
    try {
      const r = await fetch("/chat/api/captcha/status");
      const j = await r.json();
      setCaptchaEnabled(j.enabled === true);
      setCaptchaService(j.service || "2captcha");
    } catch {
      /* ignore */
    }
  }, []);

  // ─── Auth helpers ────────────────────────────────────────────────────
  const saveApiKey = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(LS_API_KEY, apiKeyInput);
      setApiKey(apiKeyInput);
      setApiKeySaved(true);
      setApiKeyInput("");
      toast({ title: "API key saved" });
    }
  }, [apiKeyInput, toast]);

  const clearApiKey = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(LS_API_KEY);
    }
    setApiKey("");
    setApiKeySaved(false);
    toast({ title: "API key cleared" });
  }, [toast]);

  // ─── Google bridge login ─────────────────────────────────────────────
  const googleLogin = useCallback(async () => {
    setLoginInProgress(true);
    try {
      const r = await authFetch("/chat/api/session?action=google_login", { method: "POST" });
      const j = await r.json().catch(() => ({}));
      if (r.ok && j.ok) {
        toast({
          title: "Logged in via Google bridge",
          description: j.user_identifier ? `Account: ${j.user_identifier}` : "Session saved.",
        });
        await fetchSession();
      } else {
        toast({
          title: "Google bridge login failed",
          description: j.error ?? `HTTP ${r.status}`,
          variant: "destructive",
        });
      }
    } catch (e) {
      toast({
        title: "Google bridge login failed",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoginInProgress(false);
    }
  }, [authFetch, toast, fetchSession]);

  // ─── Conversation management ─────────────────────────────────────────
  const activeConversation = activeId
    ? conversations.find((c) => c.id === activeId) ?? null
    : null;

  const createConversation = useCallback((): Conversation => {
    const preset = PRESET_BY_ID.get(agentPresetId);
    const conv: Conversation = {
      id: newId(),
      title: "New chat",
      messages: [],
      model: preset?.suggestedModel ?? (models[0]?.id ?? "gpt-5.2"),
      systemPrompt: preset?.systemPrompt,
      agentPresetId: agentPresetId,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    return conv;
  }, [agentPresetId, models]);

  const updateConversation = useCallback(
    (id: string, patch: Partial<Conversation>) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, ...patch, updatedAt: Date.now() } : c,
        ),
      );
    },
    [],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (activeId === id) {
          setActiveId(next[0]?.id ?? null);
        }
        return next;
      });
    },
    [activeId],
  );

  const renameConversation = useCallback(
    (id: string, title: string) => {
      updateConversation(id, { title });
    },
    [updateConversation],
  );

  const newChat = useCallback(() => {
    createConversation();
    setInput("");
  }, [createConversation]);

  // ─── Send message + stream response ──────────────────────────────────
  // ─── Webcam photo capture → send as message ─────────────────────
  const handleWebcamCapture = useCallback(
    (dataUrl: string) => {
      let conv = activeConversation;
      if (!conv) {
        conv = createConversation();
      }
      const convId = conv.id;
      const userMsg: ChatMessageType = {
        id: newId(),
        role: "user",
        content: `![photo](${dataUrl})`,
        timestamp: Date.now(),
      };
      const newTitle =
        conv.messages.length === 0 ? "Photo" : conv.title;
      updateConversation(convId, {
        messages: [...conv.messages, userMsg],
        title: newTitle,
      });
    },
    [activeConversation, createConversation, updateConversation],
  );

  const sendMessage = useCallback(async (attachments: Array<{id:string;name:string;size:number;mime:string;url:string;kind:string}> = []) => {
    if ((!input.trim() && attachments.length === 0) || loading) return;
    let conv = activeConversation;
    if (!conv) {
      conv = createConversation();
    }
    const convId = conv.id;

    const trimmed = input.trim();
    const parts: any[] = [];
    if (trimmed) parts.push({ type: "text", text: trimmed });
    for (const a of attachments) {
      if (a.kind === "image") parts.push({ type: "image_url", image_url: { url: a.url } });
      else parts.push({ type: "file", file: { url: a.url, name: a.name, mime: a.mime, size: a.size } });
    }
    const userMsg: ChatMessageType = {
      id: newId(),
      role: "user",
      content: parts.length > 1 || attachments.length > 0 ? parts : (parts[0]?.text ?? ""),
      attachments: attachments.length ? attachments : undefined,
      timestamp: Date.now(),
    };

    const assistantMsg: ChatMessageType = {
      id: newId(),
      role: "assistant",
      content: "",
      model: conv.model,
      timestamp: Date.now(),
      streaming: true,
    };

    const newMessages = [...conv.messages, userMsg, assistantMsg];
    const newTitle = conv.messages.length === 0 ? deriveTitle(trimmed || (attachments[0]?.name ?? 'attachment')) : conv.title;

    updateConversation(convId, {
      messages: newMessages,
      title: newTitle,
    });
    setInput("");
    setLoading(true);
    setStopRequested(false);
    const startTime = Date.now();

    // Build the messages payload for the API.
    const apiMessages: Array<{ role: string; content: string }> = [];
    if (conv.systemPrompt) {
      apiMessages.push({ role: "system", content: conv.systemPrompt });
    }
    const toText = (c: any): string =>
        typeof c === "string" ? c
        : Array.isArray(c) ? c.map((p: any) => p.type === "text" ? p.text : (p.type === "image_url" ? "[image]" : "[file]")).join("\n")
        : String(c);
    for (const m of [...conv.messages, userMsg]) {
      if (m.role === "user" || m.role === "assistant") {
        apiMessages.push({ role: m.role, content: toText(m.content) });
      }
    }
    // Add attachment parts to the LAST user message (the one we just sent).
    if (attachments.length || parts.length > 1) {
      const last = apiMessages[apiMessages.length - 1];
      const lastParts: any[] = [];
      if (trimmed) lastParts.push({ type: "text", text: trimmed });
      for (const a of attachments) {
        if (a.kind === "image") lastParts.push({ type: "image_url", image_url: { url: a.url } });
        else lastParts.push({ type: "file", file: { url: a.url, name: a.name, mime: a.mime } });
      }
      last.content = lastParts;
    }

    try {
      const r = await authFetch("/chat/api/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: conv.model,
          messages: apiMessages,
          stream: true,
        }),
      });

      if (!r.ok || !r.body) {
        const j = await r.json().catch(() => ({}));
        const errMsg = j?.error?.message ?? `HTTP ${r.status}`;
        updateConversation(convId, {
          messages: newMessages.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, streaming: false, error: errMsg, elapsed_ms: Date.now() - startTime }
              : m,
          ),
        });
        toast({
          title: "Request failed",
          description: errMsg,
          variant: "destructive",
        });
        setLoading(false);
        return;
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let acc = "";

      while (true) {
        if (stopRequested) {
          reader.cancel();
          break;
        }
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        while (true) {
          const idx = buffer.indexOf("\n\n");
          if (idx < 0) break;
          const event = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          for (const line of event.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") continue;
            try {
              const obj = JSON.parse(data);
              const delta = obj?.choices?.[0]?.delta?.content ?? "";
              if (delta) {
                acc += delta;
                // Update the assistant message in real time.
                setConversations((prev) =>
                  prev.map((c) =>
                    c.id === convId
                      ? {
                          ...c,
                          messages: c.messages.map((m) =>
                            m.id === assistantMsg.id ? { ...m, content: acc } : m,
                          ),
                          updatedAt: Date.now(),
                        }
                      : c,
                  ),
                );
              }
            } catch {
              /* ignore parse errors */
            }
          }
        }
      }

      // Finalize: mark as not streaming.
      const finalElapsed = Date.now() - startTime;
      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantMsg.id
                    ? {
                        ...m,
                        streaming: false,
                        elapsed_ms: finalElapsed,
                        content: acc || m.content || "(no response)",
                      }
                    : m,
                ),
                updatedAt: Date.now(),
              }
            : c,
        ),
      );
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Network error";
      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantMsg.id
                    ? {
                        ...m,
                        streaming: false,
                        error: errMsg,
                        elapsed_ms: Date.now() - startTime,
                      }
                    : m,
                ),
              }
            : c,
        ),
      );
      toast({
        title: "Network error",
        description: errMsg,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setStopRequested(false);
      void fetchQueue();
    }
  }, [input, loading, activeConversation, createConversation, updateConversation, authFetch, toast, fetchQueue, stopRequested]);

  const stopGeneration = useCallback(() => {
    setStopRequested(true);
  }, []);

  // ─── Regenerate last assistant message ───────────────────────────────
  const regenerate = useCallback(
    async (messageId: string) => {
      if (!activeConversation || loading) return;
      const conv = activeConversation;
      const msgIdx = conv.messages.findIndex((m) => m.id === messageId);
      if (msgIdx < 0) return;

      // Find the user message that triggered this assistant message.
      const userMsg = conv.messages[msgIdx - 1];
      if (!userMsg || userMsg.role !== "user") return;

      // Truncate messages up to (and including) the user message, then add a fresh assistant placeholder.
      const kept = conv.messages.slice(0, msgIdx);
      const newAssistant: ChatMessageType = {
        id: newId(),
        role: "assistant",
        content: "",
        model: conv.model,
        timestamp: Date.now(),
        streaming: true,
      };
      const newMessages = [...kept, newAssistant];
      updateConversation(conv.id, { messages: newMessages });

      setLoading(true);
      setStopRequested(false);
      const startTime = Date.now();

      const apiMessages: Array<{ role: string; content: string }> = [];
      if (conv.systemPrompt) {
        apiMessages.push({ role: "system", content: conv.systemPrompt });
      }
      for (const m of kept) {
        if (m.role === "user" || m.role === "assistant") {
          apiMessages.push({ role: m.role, content: m.content });
        }
      }

      try {
        const r = await authFetch("/chat/api/v1/chat/completions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: conv.model,
            messages: apiMessages,
            stream: true,
          }),
        });
        if (!r.ok || !r.body) {
          const j = await r.json().catch(() => ({}));
          const errMsg = j?.error?.message ?? `HTTP ${r.status}`;
          setConversations((prev) =>
            prev.map((c) =>
              c.id === conv.id
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === newAssistant.id
                        ? { ...m, streaming: false, error: errMsg, elapsed_ms: Date.now() - startTime }
                        : m,
                    ),
                  }
                : c,
            ),
          );
          setLoading(false);
          return;
        }

        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let acc = "";

        while (true) {
          if (stopRequested) {
            reader.cancel();
            break;
          }
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          while (true) {
            const idx = buffer.indexOf("\n\n");
            if (idx < 0) break;
            const event = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            for (const line of event.split("\n")) {
              if (!line.startsWith("data: ")) continue;
              const data = line.slice(6).trim();
              if (data === "[DONE]") continue;
              try {
                const obj = JSON.parse(data);
                const delta = obj?.choices?.[0]?.delta?.content ?? "";
                if (delta) {
                  acc += delta;
                  setConversations((prev) =>
                    prev.map((c) =>
                      c.id === conv.id
                        ? {
                            ...c,
                            messages: c.messages.map((m) =>
                              m.id === newAssistant.id ? { ...m, content: acc } : m,
                            ),
                          }
                        : c,
                    ),
                  );
                }
              } catch {
                /* ignore */
              }
            }
          }
        }
        const finalElapsed = Date.now() - startTime;
        setConversations((prev) =>
          prev.map((c) =>
            c.id === conv.id
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === newAssistant.id
                      ? {
                          ...m,
                          streaming: false,
                          elapsed_ms: finalElapsed,
                          content: acc || m.content || "(no response)",
                        }
                      : m,
                  ),
                }
              : c,
          ),
        );
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : "Network error";
        setConversations((prev) =>
          prev.map((c) =>
            c.id === conv.id
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === newAssistant.id
                      ? { ...m, streaming: false, error: errMsg, elapsed_ms: Date.now() - startTime }
                      : m,
                  ),
                }
              : c,
          ),
        );
      } finally {
        setLoading(false);
        setStopRequested(false);
      }
    },
    [activeConversation, loading, authFetch, stopRequested],
  );

  // ─── Auto-scroll to bottom on new messages ───────────────────────────
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [activeConversation?.messages]);

  // ─── When agent preset changes, update the active conversation's prompt ──
  const onAgentPresetChange = useCallback(
    (id: string) => {
      setAgentPresetId(id);
      const preset = PRESET_BY_ID.get(id);
      if (activeConversation && preset) {
        updateConversation(activeConversation.id, {
          systemPrompt: preset.systemPrompt,
          agentPresetId: id,
          model: preset.suggestedModel,
        });
      }
    },
    [activeConversation, updateConversation],
  );

  // ─── System prompt for the active conversation ───────────────────────
  const activeSystemPrompt = activeConversation?.systemPrompt ?? "";
  const setActiveSystemPrompt = useCallback(
    (v: string) => {
      if (activeConversation) {
        updateConversation(activeConversation.id, { systemPrompt: v });
      }
    },
    [activeConversation, updateConversation],
  );

  // ─── Render ──────────────────────────────────────────────────────────
  const isBlocked = !session?.logged_in;

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
      {/* Header */}
      <header className="border-b flex-shrink-0 bg-background/95 backdrop-blur z-30">
        <div className="px-3 py-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 lg:hidden"
              onClick={() => setShowConversations((s) => !s)}
            >
              <Menu className="w-4 h-4" />
            </Button>
            <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center font-bold text-xs">
              AR
            </div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-semibold leading-tight">Arena Router Chat</h1>
              <p className="text-[10px] text-muted-foreground leading-tight">
                {models.length} models · {session?.logged_in ? "connected" : "not logged in"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {authRequired && (
              <Badge variant={apiKeySaved ? "default" : "destructive"} className="gap-1 text-[10px]">
                <KeyRound className="w-2.5 h-2.5" />
                {apiKeySaved ? "key set" : "key needed"}
              </Badge>
            )}
            <Badge variant={session?.logged_in ? "default" : "secondary"} className="gap-1 text-[10px]">
              {session?.logged_in ? <CircleCheck className="w-2.5 h-2.5" /> : <CircleX className="w-2.5 h-2.5" />}
              {session?.logged_in ? "in" : "out"}
            </Badge>
            {queueState?.busy && (
              <Badge variant="secondary" className="gap-1 text-[10px] animate-pulse">
                <CircleDot className="w-2.5 h-2.5" />
                busy
              </Badge>
            )}
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              onClick={() => setShowRightPanel((s) => !s)}
              title={showRightPanel ? "Hide panel" : "Show panel"}
            >
              {showRightPanel ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversations sidebar */}
        {showConversations && (
          <aside className="w-60 border-r flex-shrink-0 bg-muted/20 hidden lg:flex flex-col">
            <ConversationSidebar
              conversations={conversations}
              activeId={activeId}
              onSelect={setActiveId}
              onNew={newChat}
              onDelete={deleteConversation}
              onRename={renameConversation}
            />
          </aside>
        )}

        {/* Mobile drawer */}
        {showConversations && (
          <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setShowConversations(false)}>
            <aside
              className="absolute left-0 top-0 bottom-0 w-72 bg-background border-r flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-2 border-b">
                <span className="text-sm font-medium">Conversations</span>
                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setShowConversations(false)}>
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
              <ConversationSidebar
                conversations={conversations}
                activeId={activeId}
                onSelect={(id) => {
                  setActiveId(id);
                  setShowConversations(false);
                }}
                onNew={() => {
                  newChat();
                  setShowConversations(false);
                }}
                onDelete={deleteConversation}
                onRename={renameConversation}
              />
            </aside>
          </div>
        )}

        {/* Chat area */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Top bar: model picker + new chat */}
          <div className="border-b px-3 py-2 flex items-center gap-2 bg-background">
            <ModelPicker
              models={models}
              value={activeConversation?.model ?? (models[0]?.id ?? "")}
              onChange={(id) => {
                if (activeConversation) {
                  updateConversation(activeConversation.id, { model: id });
                }
              }}
            />
            <Button size="sm" variant="outline" onClick={newChat} className="gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              New
            </Button>
            <Button size="sm" variant={showWebcam ? "default" : "outline"} onClick={() => setShowWebcam(s => !s)} className="gap-1.5" title="Toggle webcam">
              <Camera className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Cam</span>
            </Button>
            <div className="flex-1" />
            {activeConversation && (
              <span className="text-xs text-muted-foreground hidden sm:inline">
                {activeConversation.messages.length} messages
              </span>
            )}
          </div>

          {/* Messages */}
          <div ref={scrollAreaRef} className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto p-4 space-y-4">
              {!activeConversation || activeConversation.messages.length === 0 ? (
                <EmptyState
                  hasModels={models.length > 0}
                  isBlocked={isBlocked}
                  onNew={newChat}
                />
              ) : (
                activeConversation.messages.map((m, idx) => (
                  <ChatMessage
                    key={m.id}
                    message={m}
                    canRegenerate={
                      m.role === "assistant" &&
                      !m.streaming &&
                      idx === activeConversation.messages.length - 1
                    }
                    onRegenerate={() => void regenerate(m.id)}
                  />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Blocked banner */}
          {isBlocked && (
            <div className="border-t border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400 flex items-center gap-2">
              <LogIn className="w-3.5 h-3.5 flex-shrink-0" />
              <span>
                Not logged in to arena.ai. Open the right panel and click &quot;Login with Google&quot; to enable chat.
              </span>
            </div>
          )}

          {/* Webcam panel */}
          {showWebcam && (
            <WebcamPanel onCapture={handleWebcamCapture} />
          )}

          {/* Input */}
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={(atts) => void sendMessage(atts)}
            onStop={stopGeneration}
            loading={loading}
            systemPrompt={activeSystemPrompt}
            onSystemPromptChange={setActiveSystemPrompt}
            agentPresetId={activeConversation?.agentPresetId ?? agentPresetId}
            onAgentPresetChange={onAgentPresetChange}
            disabled={isBlocked}
          />
        </main>

        {/* Right panel: auth + session + queue */}
        {showRightPanel && (
          <aside className="w-72 border-l flex-shrink-0 bg-muted/20 hidden lg:flex flex-col overflow-y-auto">
            <RightPanel
              authRequired={authRequired}
              apiKeySaved={apiKeySaved}
              apiKeyInput={apiKeyInput}
              setApiKeyInput={setApiKeyInput}
              saveApiKey={saveApiKey}
              clearApiKey={clearApiKey}
              session={session}
              refreshingSession={refreshingSession}
              onRefreshSession={() => void fetchSession()}
              onGoogleLogin={() => void googleLogin()}
              loginInProgress={loginInProgress}
              queueState={queueState}
              modelsCount={models.length}
              captchaEnabled={captchaEnabled}
              captchaService={captchaService}
            />
          </aside>
        )}
      </div>
      <Toaster />
    </div>
  );
}

// ─── Empty state ────────────────────────────────────────────────────────
function EmptyState({
  hasModels,
  isBlocked,
  onNew,
}: {
  hasModels: boolean;
  isBlocked: boolean;
  onNew: () => void;
}) {
  if (!hasModels) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading models…</p>
      </div>
    );
  }
  if (isBlocked) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center max-w-md">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 grid place-items-center">
          <LogIn className="w-7 h-7 text-amber-600" />
        </div>
        <h2 className="text-lg font-semibold">Login required</h2>
        <p className="text-sm text-muted-foreground">
          arena.ai requires login to use Direct Chat. Click &quot;Login with Google&quot; in the right panel — it uses your existing Google session and takes ~30 seconds.
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center max-w-lg">
      <div className="w-14 h-14 rounded-2xl bg-primary/10 grid place-items-center">
        <Sparkles className="w-7 h-7 text-primary" />
      </div>
      <div>
        <h2 className="text-xl font-semibold">Start a conversation</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Pick a model above, choose an agent preset below, and start chatting. All 131 models from arena.ai are available.
        </p>
      </div>
      <Button onClick={onNew} className="gap-2">
        <Sparkles className="w-4 h-4" />
        New chat
      </Button>
    </div>
  );
}

// ─── Right panel ────────────────────────────────────────────────────────
function RightPanel({
  authRequired,
  apiKeySaved,
  apiKeyInput,
  setApiKeyInput,
  saveApiKey,
  clearApiKey,
  session,
  refreshingSession,
  onRefreshSession,
  onGoogleLogin,
  loginInProgress,
  queueState,
  modelsCount,
  captchaEnabled,
  captchaService,
}: {
  authRequired: boolean;
  apiKeySaved: boolean;
  apiKeyInput: string;
  setApiKeyInput: (v: string) => void;
  saveApiKey: () => void;
  clearApiKey: () => void;
  session: SessionStatus | null;
  refreshingSession: boolean;
  onRefreshSession: () => void;
  onGoogleLogin: () => void;
  loginInProgress: boolean;
  queueState: QueueSnapshot | null;
  modelsCount: number;
  captchaEnabled: boolean;
  captchaService: string;
}) {
  return (
    <div className="p-3 space-y-4 text-sm">
      {/* API key */}
      {authRequired && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold flex items-center gap-1.5">
            <KeyRound className="w-3 h-3" />
            API Key
          </h3>
          {apiKeySaved ? (
            <div className="flex items-center justify-between">
              <Badge variant="default" className="text-[10px]">
                <CircleCheck className="w-2.5 h-2.5 mr-1" />
                set
              </Badge>
              <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={clearApiKey}>
                Clear
              </Button>
            </div>
          ) : (
            <div className="space-y-1.5">
              <input
                type="password"
                placeholder="sk-…"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                className="w-full h-8 px-2 text-xs rounded border bg-background"
              />
              <Button size="sm" className="w-full h-7 text-xs" onClick={saveApiKey}>
                Save key
              </Button>
            </div>
          )}
        </section>
      )}

      <Separator />

      {/* Session */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold flex items-center gap-1.5">
          <Server className="w-3 h-3" />
          Session
        </h3>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant={session?.logged_in ? "default" : "secondary"} className="text-[10px]">
              {session?.logged_in ? "logged in" : "anonymous"}
            </Badge>
          </div>
          {session?.user_identifier && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">User</span>
              <span className="font-mono text-[10px] truncate max-w-[140px]">{session.user_identifier}</span>
            </div>
          )}
          {session?.last_verified_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Verified</span>
              <span className="text-[10px]">
                {new Date(session.last_verified_at).toLocaleTimeString()}
              </span>
            </div>
          )}
        </div>
        <Button
          size="sm"
          className="w-full gap-1.5"
          onClick={onGoogleLogin}
          disabled={loginInProgress}
        >
          {loginInProgress ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
          )}
          {loginInProgress ? "Logging in…" : "Login with Google"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="w-full text-xs"
          onClick={onRefreshSession}
          disabled={refreshingSession}
        >
          <RefreshCw className={`w-3 h-3 mr-1 ${refreshingSession ? "animate-spin" : ""}`} />
          Refresh status
        </Button>
        {session?.last_error && (
          <p className="text-[10px] text-destructive border border-destructive/30 rounded p-1.5 bg-destructive/5">
            {session.last_error}
          </p>
        )}
      </section>

      <Separator />

      {/* Queue */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold flex items-center gap-1.5">
          <Activity className="w-3 h-3" />
          Queue
        </h3>
        <div className="text-xs space-y-1">
          <div className="flex items-center gap-1.5">
            <CircleDot
              className={`w-2.5 h-2.5 ${queueState?.busy ? "text-primary animate-pulse" : "text-muted-foreground"}`}
            />
            {queueState?.busy ? "Processing request…" : "Idle"}
          </div>
          {queueState?.pending ? (
            <div className="text-muted-foreground">{queueState.pending} pending</div>
          ) : null}
        </div>
      </section>

      <Separator />

      {/* CAPTCHA solver */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold flex items-center gap-1.5">
          <Shield className="w-3 h-3" />
          CAPTCHA solver
        </h3>
        {captchaEnabled ? (
          <>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="default" className="text-[10px] gap-1">
                <CircleCheck className="w-2.5 h-2.5" />
                enabled
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Service</span>
              <span className="font-mono text-[10px]">{captchaService}</span>
            </div>
            <p className="text-[10px] text-muted-foreground">
              reCAPTCHA challenges from arena.ai will be auto-solved (~$0.003 per solve).
            </p>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="secondary" className="text-[10px] gap-1">
                <CircleX className="w-2.5 h-2.5" />
                disabled
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Set <code className="text-[10px]">ANTI_CAPTCHA_API_KEY</code> in{" "}
              <code className="text-[10px]">.env</code> to enable auto-solving of reCAPTCHA challenges. Get a key from{" "}
              <a href="https://2captcha.com" target="_blank" rel="noopener noreferrer" className="underline text-primary">
                2captcha.com
              </a>{" "}
              (~$3/1000 solves),{" "}
              <a href="https://anti-captcha.com" target="_blank" rel="noopener noreferrer" className="underline text-primary">
                anti-captcha.com
              </a>{" "}
              or{" "}
              <a href="https://capsolver.com" target="_blank" rel="noopener noreferrer" className="underline text-primary">
                capsolver.com
              </a>.
            </p>
          </>
        )}
      </section>

      <Separator />

      {/* Stats */}
      <section className="space-y-1 text-xs text-muted-foreground">
        <div className="flex justify-between">
          <span>Models</span>
          <span className="font-mono">{modelsCount}</span>
        </div>
        <div className="flex justify-between">
          <span>Streaming</span>
          <span className="font-mono">SSE</span>
        </div>
        <div className="flex justify-between">
          <span>Conversations</span>
          <span className="font-mono">localStorage</span>
        </div>
      </section>
    </div>
  );
}
