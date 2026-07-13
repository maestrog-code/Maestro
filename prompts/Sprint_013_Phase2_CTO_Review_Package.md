# MAESTRO — Sprint 013 Phase 2 (Codebase Hardening) CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 013 Phase 2: Production Codebase Hardening.
This document contains the updates to backend configurations (CORS), the secure cookie implementation, and the NEXT_PUBLIC_API_URL hydration across the fetchers.

---

## `../../backend/maestro/app/core/config.py`

```py
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Maestro"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "https://maestro.vercel.app", 
        "https://maestro-production.vercel.app"
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    DATABASE_URL: str = "postgresql+asyncpg://maestro_user:maestro_password@localhost:5432/maestro_db"
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT Settings
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## `../../web/src/app/actions/auth.ts`

```tsx
"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function loginAction(prevState: any, formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  try {
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!res.ok) {
      // Handle known errors cleanly
      if (res.status === 401 || res.status === 422) {
        return { error: "Invalid credentials." };
      }
      return { error: "An unexpected server error occurred." };
    }

    const data = await res.json();
    const token = data.token.access_token;
    const maxAge = 30 * 60; // 30 minutes in seconds

    // Set HTTP-only cookie
    cookies().set("maestro_session", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 30 * 24 * 60 * 60, // 30 days
      path: "/",
    });

  } catch (error) {
    console.error("Login Server Action Error:", error);
    return { error: "Failed to connect to the authentication server." };
  }

  // Redirect on success (Next.js redirect throws an error under the hood, 
  // so it must be called outside the try/catch block)
  redirect("/");
}

export async function logoutAction() {
  cookies().delete("maestro_session");
  redirect("/login");
}
```

---

## `../../web/src/lib/api/chat.ts`

```tsx
import { useChatStore } from "@/store/useChatStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort);
  });

async function runSimulatedChatStream(
  prompt: string,
  signal: AbortSignal,
  assistantMsgId: string
) {
  const store = useChatStore.getState();
  console.info("[Simulation Mode] Enabled - Backend unreachable. Running simulated multi-agent stream.");
  store.setIsSimulationMode(true);
  store.clearSubAgentStreams();

  try {
    store.setAgentState("CEO: Decomposing task & initializing team...");
    await delay(1200, signal);

    store.updateScratchpad({
      step: "Decompose query & delegate tasks",
      status: "COMPLETED",
      notes: "CEO planned: delegated finance to CFO, operations to COO."
    });
    
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "IN_PROGRESS",
      notes: "Running financial audit tool..."
    });
    store.setAgentState("CEO delegated to CFO...");
    store.updateToolStatus({ tool_name: "fetch_financial_metrics", status: "running" });
    store.appendSubAgentToken("CFO", "[System] CFO Agent initialized.\n");
    await delay(500, signal);
    store.appendSubAgentToken("CFO", "Fetching gross revenue and operational cost metrics...\n");
    await delay(1000, signal);

    store.updateToolStatus({ tool_name: "fetch_financial_metrics", status: "completed" });
    store.updateToolStatus({ tool_name: "calculate_projected_margins", status: "running" });
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "IN_PROGRESS",
      notes: "Calculating margin projections..."
    });
    store.appendSubAgentToken("CFO", "Gross revenue found: $478,500 (+6.3% variance).\n");
    await delay(600, signal);
    store.appendSubAgentToken("CFO", "Calculating operating margins vs target (22.0%)...\n");
    await delay(600, signal);

    store.updateToolStatus({ tool_name: "calculate_projected_margins", status: "completed" });
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "COMPLETED",
      notes: "Margins calculated: 24.5% actual vs 22% target."
    });
    store.appendSubAgentToken("CFO", "Operating margin calculated: 24.5% (Actual) vs 22.0% (Target). CFO analysis completed successfully.\n");

    store.updateScratchpad({
      step: "COO: Verify operations & resource allocation",
      status: "IN_PROGRESS",
      notes: "Auditing engineer resource utilization..."
    });
    store.setAgentState("CEO delegated to COO...");
    store.updateToolStatus({ tool_name: "check_resource_allocation", status: "running" });
    store.appendSubAgentToken("COO", "[System] COO Agent initialized.\n");
    await delay(600, signal);
    store.appendSubAgentToken("COO", "Accessing active workspace telemetry & engineering logs...\n");
    await delay(1200, signal);

    store.updateToolStatus({ tool_name: "check_resource_allocation", status: "completed" });
    store.updateScratchpad({
      step: "COO: Verify operations & resource allocation",
      status: "COMPLETED",
      notes: "Capacity verified: 92% utilization, 8% buffer."
    });
    store.appendSubAgentToken("COO", "Resource utilization verified: 92% active, 8% capacity buffer. Backlog status: Stable. COO operations audit completed.\n");

    store.updateScratchpad({
      step: "CEO: Consolidate briefings & draft executive response",
      status: "IN_PROGRESS",
      notes: "Synthesizing response report..."
    });
    store.setAgentState("CEO: Summarizing team responses...");
    await delay(1000, signal);

    // Stream response tokens
    const text = `### Executive Briefing: Q2 Operations & Financial Outlook

I have coordinated with our **CFO** (Financial Analysis) and **COO** (Operations) to compile the requested analysis. Here is our consolidated briefing:

#### 1. Financial Performance Analysis (CFO)
Our financial tools retrieved the current Q2 performance metrics. We observed a strong revenue trend driven by a **14.2% increase** in contract size:
| Metric | Target | Actual | Variance |
| :--- | :--- | :--- | :--- |
| **Gross Revenue** | $450,000 | $478,500 | +6.3% |
| **Operating Margin**| 22.0% | 24.5% | +2.5% |
| **Customer LTV** | $8,500 | $9,750 | +14.7% |

#### 2. Operations & Capacity Review (COO)
Resource allocation has been cross-referenced with our active pipeline. While engineering bandwidth is currently at **92% utilization**, we have sufficient buffer to onboard up to two more concurrent enterprise projects.

#### 3. Strategic Guidance (CEO Summary)
* **Capital Allocation:** Reinvest the Q2 revenue surplus into our automated sales pipeline to accelerate pipeline velocity.
* **Hiring Pipeline:** Initiate a search for a Senior Backend Engineer by mid-Q3 to relieve pressure on the core systems team.

Let me know if you would like me to task the **CFO** to run a detailed cash flow projection based on these figures.`;

    const tokens = text.split(" ");
    for (let i = 0; i < tokens.length; i++) {
      const nextWord = tokens[i] + (i === tokens.length - 1 ? "" : " ");
      store.appendTokenToLastAssistantMessage(nextWord);
      // Vary delay slightly to feel realistic
      const delayTime = 30 + Math.random() * 50;
      await delay(delayTime, signal);
    }

    store.updateScratchpad({
      step: "CEO: Consolidate briefings & draft executive response",
      status: "COMPLETED",
      notes: "Draft completed and presented."
    });

  } catch (err: any) {
    if (err.name === "AbortError") {
      console.log("Simulated stream aborted");
    } else {
      console.error("Simulation error:", err);
    }
  } finally {
    store.resetStreamState();
  }
}

export async function sendChatMessage(
  orgId: string,
  prompt: string,
  signal: AbortSignal
) {
  const store = useChatStore.getState();
  store.setIsStreaming(true);
  store.setIsSimulationMode(false);
  store.clearSubAgentStreams();

  // Optimistically add the user message
  store.addMessage({
    id: crypto.randomUUID(),
    role: "user",
    content: prompt,
  });

  const assistantMessageId = crypto.randomUUID();
  // Add an empty assistant message that we will append tokens to
  store.addMessage({
    id: assistantMessageId,
    role: "assistant",
    content: "",
  });
  store.setStreamingMessageId(assistantMessageId);

  store.setAgentState("Initializing...");

  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/organizations/${orgId}/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: prompt }), // Corrected schema key: "message" instead of "prompt"
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("No response body stream");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;

        const lines = rawEvent.split("\n");
        let eventType = "";
        let eventData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.replace("event: ", "").trim();
          } else if (line.startsWith("data: ")) {
            eventData = line.replace("data: ", "").trim();
          }
        }

        if (eventType === "end") {
          store.resetStreamState();
          return;
        }

        if (!eventData || eventData === "{}") continue;

        try {
          const payload = JSON.parse(eventData);

          switch (eventType) {
            case "token":
              store.appendTokenToLastAssistantMessage(payload.text);
              break;
            case "sub_agent_token":
              store.appendSubAgentToken(payload.agent_name, payload.text);
              break;
            case "orchestration":
              store.setAgentState(`CEO delegating to ${payload.target_agent}...`);
              break;
            case "task_update":
              store.updateScratchpad({
                step: payload.step,
                status: payload.status,
                notes: payload.notes,
              });
              break;
            case "tool_call":
              store.updateToolStatus({
                tool_name: payload.tool_name,
                status: payload.status,
              });
              break;
            default:
              console.warn("Unknown event type:", eventType);
          }
        } catch (e) {
          console.error("Failed to parse event data", e, eventData);
        }
      }
    }
  } catch (error: any) {
    if (error.name === "AbortError") {
      console.log("Stream aborted");
      store.resetStreamState();
    } else {
      console.warn("Real connection failed. Falling back to simulation mode.", error);
      await runSimulatedChatStream(prompt, signal, assistantMessageId);
    }
  }
}
```

---

## `../../web/src/app/page.tsx`

```tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
import { MaestroLogo } from "@/components/ui/MaestroLogo";
import { useChatStore } from "@/store/useChatStore";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { AgentStatus } from "@/components/chat/AgentStatus";
import { ChatInput } from "@/components/chat/ChatInput";
import { sendChatMessage } from "@/lib/api/chat";
import { 
  Bot, 
  Terminal, 
  Activity, 
  Cpu, 
  Sparkles, 
  Server, 
  Layout, 
  TrendingUp, 
  ArrowRight,
  ShieldCheck,
  Building,
  X
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ExecutiveDashboard } from "@/components/dashboard/ExecutiveDashboard";
import useSWR from "swr";


const SUGGESTIONS = [
  {
    title: "Generate Q2 Briefing",
    desc: "Run financial forecast & resource allocation checks",
    prompt: "Generate Q2 operations and financial outlook report"
  },
  {
    title: "Forecast Growth Margins",
    desc: "Calculate margins based on target vs actual metrics",
    prompt: "Run margin projections and evaluate budget allocation"
  },
  {
    title: "Audit Capacity Limits",
    desc: "Verify engineering utilization and recruiting pipeline",
    prompt: "Analyze resource capacity and recommend hiring pipeline schedule"
  }
];

export default function Home() {
  const [activeView, setActiveView] = useState<"chat" | "dashboard">("dashboard");
  const { 
    activeOrganization,
    setActiveOrganization,
    messages, 
    isStreaming, 
    isSimulationMode, 
    selectedSubAgentLog, 
    setSelectedSubAgentLog, 
    subAgentStreams,
    agentState
  } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Unified SWR multi-tenant organization fetch handler
  const { data: organizations, error: orgsError } = useSWR(
    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/organizations`,
    (url) => fetch(url, { credentials: "include" }).then((res) => {
      if (!res.ok) throw new Error("Workspace validation failed");
      return res.json();
    }),
    {
      revalidateOnFocus: false,
      onSuccess: (data) => {
        // Automatically hydrate store with user's primary organization context
        if (data?.length > 0 && !activeOrganization) {
          setActiveOrganization(data[0]);
        }
      }
    }
  );

  const isHydratingWorkspace = !organizations && !orgsError;

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleSuggestionClick = async (prompt: string) => {
    if (isStreaming) return;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    await sendChatMessage(currentOrgId, prompt, abortControllerRef.current.signal);
  };

  // 1. Guardrail: Handle active hydration loader state
  if (isHydratingWorkspace) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#050505] font-sans">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <MaestroLogo className="w-16 h-16" />
          <p className="text-[10px] uppercase font-mono tracking-widest text-zinc-600">
            Synchronizing Workspace Security Context...
          </p>
        </div>
      </div>
    );
  }

  // 2. Guardrail: Handle empty organizational clearance zones
  if (orgsError || !organizations || organizations.length === 0) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#050505] font-sans px-6 text-center">
        <div className="max-w-md p-8 rounded-2xl border border-red-500/10 bg-red-500/5 text-zinc-100 backdrop-blur-xl">
          <p className="text-sm font-semibold text-red-400 mb-2">Access Control Denied</p>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Your credentials validated successfully, but your profile lacks active security clearance for an enterprise workspace tenant. Contact an administrator to map your organizational access controls.
          </p>
        </div>
      </div>
    );
  }

  // Fallback anchor to guarantee resolution values are locked
  const currentOrgId = activeOrganization?.id || organizations[0]?.id;

  return (
    <div className="flex h-screen w-full bg-[#050505] text-zinc-100 overflow-hidden font-sans">
      {/* Dynamic radial glow background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.03),transparent_40%),radial-gradient(circle_at_70%_80%,rgba(147,51,234,0.03),transparent_40%)] pointer-events-none" />

      {/* Sidebar - Executive Team & Stats */}
      <aside className="hidden lg:flex flex-col w-80 bg-zinc-950 border-r border-white/5 relative z-10 flex-shrink-0">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          {/* The isolated Node Symbol */}
          <div className="flex-shrink-0">
            <MaestroLogo className="w-10 h-10" />
          </div>
          
          {/* The Text - Rendered via HTML */}
          <div className="hidden lg:block">
            <h1 className="font-bold text-base tracking-tight text-zinc-100 flex items-center gap-1.5">
              MAESTRO <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">v0.1.0</span>
            </h1>
            <p className="text-xs text-zinc-500">Autonomous Business OS</p>
          </div>
        </div>

        {/* Executive Officers */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 custom-scrollbar">
          {/* Views */}
          <div>
            <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider px-2 block mb-3">
              Views
            </span>
            <div className="space-y-1">
              <button 
                onClick={() => setActiveView("chat")}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg border ${activeView === "chat" ? "bg-white/[0.04] border-white/10" : "border-transparent hover:bg-white/[0.01]"}`}
              >
                <div className="flex items-center gap-2.5">
                  <Layout size={16} className={activeView === "chat" ? "text-blue-400" : "text-zinc-500"} />
                  <span className={`text-sm font-medium ${activeView === "chat" ? "text-zinc-200" : "text-zinc-400"}`}>Board Room</span>
                </div>
              </button>
              <button 
                onClick={() => setActiveView("dashboard")}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg border ${activeView === "dashboard" ? "bg-white/[0.04] border-white/10" : "border-transparent hover:bg-white/[0.01]"}`}
              >
                <div className="flex items-center gap-2.5">
                  <TrendingUp size={16} className={activeView === "dashboard" ? "text-blue-400" : "text-zinc-500"} />
                  <span className={`text-sm font-medium ${activeView === "dashboard" ? "text-zinc-200" : "text-zinc-400"}`}>Executive Dashboard</span>
                </div>
              </button>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider px-2 block mb-3">
              Executive Officers
            </span>
            <div className="space-y-1">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                  <span className="text-sm font-medium text-zinc-300">CEO (Chief Executive)</span>
                </div>
                <span className="text-[11px] text-zinc-500 font-mono">Orchestrator</span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-transparent hover:bg-white/[0.01]">
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-zinc-600" />
                  <span className="text-sm font-medium text-zinc-400">CFO (Finance Officer)</span>
                </div>
                <span className="text-[11px] text-zinc-500 font-mono">Ready</span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-transparent hover:bg-white/[0.01]">
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-zinc-600" />
                  <span className="text-sm font-medium text-zinc-400">COO (Operations Officer)</span>
                </div>
                <span className="text-[11px] text-zinc-500 font-mono">Ready</span>
              </div>
            </div>
          </div>

          {/* System Performance Status */}
          <div>
            <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider px-2 block mb-3">
              Workspace Telemetry
            </span>
            <div className="space-y-3 px-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-500 flex items-center gap-1.5"><Cpu size={13} /> CPU Utilization</span>
                <span className="text-zinc-300 font-mono font-medium">1.2%</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-500 flex items-center gap-1.5"><Server size={13} /> DB Health</span>
                <span className="text-emerald-400 font-medium flex items-center gap-1">
                  <ShieldCheck size={13} /> Active
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-500 flex items-center gap-1.5"><Activity size={13} /> Response Latency</span>
                <span className="text-zinc-300 font-mono font-medium">18ms</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status watermark footer */}
        <div className="p-4 border-t border-white/5 bg-zinc-950/80">
          {isSimulationMode ? (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
              <Terminal size={14} className="shrink-0 animate-pulse" />
              <div>
                <p className="font-semibold">Local Simulation Mode</p>
                <p className="text-[10px] text-amber-500/80 leading-tight">Backend unreachable. Mocks loaded.</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-900 border border-white/5 text-zinc-400 text-xs">
              <Building size={14} className="shrink-0" />
              <div>
                <p className="font-medium text-zinc-300">Enterprise Context</p>
                <p className="text-[10px] text-zinc-500">Connected to Organization</p>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-col flex-1 h-full min-w-0 relative z-10 bg-zinc-950/20">
        {activeView === "dashboard" ? (
          <ExecutiveDashboard orgId={currentOrgId} />
        ) : (
          <>
        {/* Top Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 backdrop-blur-md bg-[#050505]/80">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
              <Bot size={18} />
            </div>
            <h1 className="font-bold text-sm tracking-tight text-zinc-100">MAESTRO</h1>
          </div>
          <div className="hidden lg:flex items-center gap-2">
            <Layout size={16} className="text-zinc-400" />
            <span className="text-xs text-zinc-400 font-medium">Executive Board Room</span>
          </div>
          
          {/* Header Watermark Badge */}
          {isSimulationMode && (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full animate-pulse">
              [Simulation Mode]
            </span>
          )}
        </header>

        {/* Message Thread container */}
        <div className="flex-1 overflow-y-auto min-h-0 custom-scrollbar">
          {messages.length === 0 ? (
            /* Suggestions view if conversation is empty */
            <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto px-4 text-center">
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white mb-6 shadow-xl shadow-blue-500/10"
              >
                <Sparkles size={32} />
              </motion.div>
              <h2 className="text-2xl font-bold text-zinc-100 tracking-tight mb-2">
                Convene the Executive Board
              </h2>
              <p className="text-sm text-zinc-400 max-w-md mb-8 leading-relaxed">
                Task the CEO agent to analyze spreadsheets, coordinate specialized CFO/COO executives, and draft directives grounded in your data.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full text-left">
                {SUGGESTIONS.map((sug, idx) => (
                  <motion.button
                    key={idx}
                    onClick={() => handleSuggestionClick(sug.prompt)}
                    initial={{ y: 15, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="group relative flex flex-col p-4 rounded-xl bg-zinc-900/40 border border-white/5 hover:border-white/10 hover:bg-zinc-900/60 text-left transition-all duration-200 cursor-pointer overflow-hidden shadow-sm"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <h3 className="text-sm font-semibold text-zinc-200 group-hover:text-blue-400 transition-colors flex items-center justify-between">
                      {sug.title}
                      <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transform translate-x-[-4px] group-hover:translate-x-0 transition-all text-blue-400" />
                    </h3>
                    <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed">
                      {sug.desc}
                    </p>
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            /* Message list */
            <div className="flex flex-col w-full pb-8">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              
              {/* Agent Orchestration checklists & running tool badges */}
              <AgentStatus />
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="border-t border-white/5 backdrop-blur-md bg-[#050505]/60 z-20">
          <ChatInput orgId={currentOrgId} />
        </div>
        </>
        )}
      </main>

      {/* Detail Drawer */}
      <AnimatePresence>
        {selectedSubAgentLog && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="absolute top-0 right-0 h-full w-full sm:w-[480px] bg-zinc-950/95 backdrop-blur-xl border-l border-white/10 z-50 flex flex-col shadow-2xl"
          >
            {/* Drawer Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/5">
              <div className="flex items-center gap-2.5">
                <Terminal size={18} className="text-blue-400" />
                <h3 className="font-semibold text-zinc-100">
                  {selectedSubAgentLog} Log Stream
                </h3>
              </div>
              <button
                onClick={() => setSelectedSubAgentLog(null)}
                className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Logs Terminal Area */}
            <div className="flex-1 overflow-y-auto p-6 font-mono text-xs text-zinc-300 space-y-2 bg-black/40 custom-scrollbar select-text">
              <div className="text-zinc-500">// Stream connection established</div>
              <pre className="whitespace-pre-wrap break-all leading-relaxed font-mono">
                {subAgentStreams[selectedSubAgentLog] || "No logs received yet."}
              </pre>
              {isStreaming && agentState.includes(selectedSubAgentLog) && (
                <div className="flex items-center gap-1.5 text-blue-400 animate-pulse mt-4">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                  <span>Streaming active tokens...</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

---

## `../../web/src/components/dashboard/ExecutiveDashboard.tsx`

```tsx
"use client";

import React from "react";
import useSWR from "swr";
import ReactMarkdown from "react-markdown";
import { DollarSign, Percent, Cpu, Clock, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";

const fetcher = (url: string) => fetch(url, { credentials: "include" }).then((res) => {
  if (!res.ok) throw new Error("Failed to pull backend telemetry");
  return res.json();
});

interface ExecutiveDashboardProps {
  orgId: string;
}

export function ExecutiveDashboard({ orgId }: ExecutiveDashboardProps) {
  // 1. Existing Metrics Hook
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const { data: telemetry, error: metricsError } = useSWR(
    orgId ? `${API_BASE}/api/v1/organizations/${orgId}/dashboard/metrics` : null,
    fetcher,
    { refreshInterval: 120000, revalidateOnFocus: true } // Auto-poll every 2m, force on focus
  );

  // 2. NEW: Briefing Hook
  const { data: briefingData, error: briefingError } = useSWR(
    orgId ? `${API_BASE}/api/v1/organizations/${orgId}/dashboard/briefing/latest` : null,
    fetcher,
    { refreshInterval: 300000, revalidateOnFocus: true } // Poll every 5m, force on focus
  );

  const isLoadingMetrics = !telemetry && !metricsError;
  const isBriefingLoading = !briefingData && !briefingError;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8 h-full overflow-y-auto custom-scrollbar">
      {/* Dashboard Top Header Bar */}
      <header className="flex flex-col gap-4 border-b border-white/5 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-pretty text-xl font-semibold tracking-tight text-white sm:text-2xl">
            Executive Performance Overview
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Real-time autonomous metrics compiled directly from system accounting ledgers.
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/5 bg-zinc-900/60 px-3 py-1.5 text-xs font-medium text-zinc-400 backdrop-blur-xl">
          <Clock className="size-3.5 text-blue-400" />
          Generated: Today, 6:00 AM
        </span>
      </header>

      {/* KPI Three-Column Grid Matrix */}
      <section className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Card 1: Gross Revenue */}
        <KpiCard
          label="Gross Revenue"
          value={isLoadingMetrics ? "..." : telemetry?.financials?.total_revenue}
          delta={isLoadingMetrics ? "" : telemetry?.financials?.gross_revenue_delta}
          trend="up"
          icon={<DollarSign className="size-4" />}
          note={isLoadingMetrics ? "Evaluating statement data..." : telemetry?.financials?.revenue_note}
          loading={isLoadingMetrics}
        />

        {/* Card 2: Net Margin */}
        <KpiCard
          label="Net Margin"
          value={isLoadingMetrics ? "..." : telemetry?.financials?.net_margin}
          delta={isLoadingMetrics ? "" : telemetry?.financials?.net_margin_delta}
          trend="up"
          icon={<Percent className="size-4" />}
          note={isLoadingMetrics ? "Rebalancing accounting rows..." : telemetry?.financials?.margin_note}
          loading={isLoadingMetrics}
        />

        {/* Card 3: Team Bandwidth Utilization */}
        <KpiCard
          label="Team Utilization"
          value={isLoadingMetrics ? "..." : telemetry?.operations?.avg_utilization}
          delta={isLoadingMetrics ? "" : telemetry?.operations?.delta}
          trend={isLoadingMetrics ? "up" : telemetry?.operations?.trend}
          icon={<Cpu className="size-4" />}
          note={isLoadingMetrics ? "Auditing production allocation logs..." : telemetry?.operations?.note}
          loading={isLoadingMetrics}
        />
      </section>

      {/* Main Content: Briefing & Projects */}
      <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        
        {/* Left Column: CEO Daily Briefing */}
        <article className="rounded-2xl border border-white/5 bg-zinc-900/40 p-6 backdrop-blur-xl lg:col-span-2 flex flex-col">
          <div className="flex items-center gap-2 border-b border-white/5 pb-4 mb-4">
            <div className={`size-2 rounded-full ${isBriefingLoading ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400 shadow-[0_0_8px] shadow-emerald-400/60'}`} />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
              CEO Morning Briefing
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            {isBriefingLoading ? (
              <div className="space-y-4 animate-pulse">
                <div className="h-4 bg-zinc-800 rounded w-3/4"></div>
                <div className="h-4 bg-zinc-800 rounded w-full"></div>
                <div className="h-4 bg-zinc-800 rounded w-5/6"></div>
                <div className="h-4 bg-zinc-800 rounded w-1/2 mt-8"></div>
                <div className="h-4 bg-zinc-800 rounded w-full"></div>
              </div>
            ) : briefingError ? (
              <div className="text-sm text-red-400">Failed to load morning briefing.</div>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none text-zinc-300">
                <ReactMarkdown>{briefingData?.content || "_No briefing content available._"}</ReactMarkdown>
              </div>
            )}
          </div>
        </article>

        {/* Right Column: Active Projects */}
        <aside className="rounded-2xl border border-white/5 bg-zinc-900/40 p-6 backdrop-blur-xl flex flex-col">
          <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Active Projects
            </h2>
            <span className="text-xs text-zinc-600">Resource alloc.</span>
          </div>

          <div className="flex flex-col gap-4 flex-1 overflow-y-auto custom-scrollbar">
            {isLoadingMetrics ? (
              // Skeleton loading for projects
              <>
                <div className="h-16 bg-zinc-800/50 rounded-xl animate-pulse"></div>
                <div className="h-16 bg-zinc-800/50 rounded-xl animate-pulse"></div>
                <div className="h-16 bg-zinc-800/50 rounded-xl animate-pulse"></div>
              </>
            ) : telemetry?.active_projects?.length > 0 ? (
              telemetry.active_projects.map((project: any) => (
                <ProjectRow 
                  key={project.name} 
                  name={project.name} 
                  client={project.client} 
                  status={project.status} 
                  allocation={project.allocation} 
                />
              ))
            ) : (
              <div className="text-sm text-zinc-500 text-center mt-4">No active projects found.</div>
            )}
          </div>
        </aside>

      </section>
    </div>
  );
}

// Nested Sub-Component with Integrated Skeleton Shimmer support
interface KpiCardProps {
  label: string;
  value: string;
  delta: string;
  trend: "up" | "down" | "warning";
  icon: React.ReactNode;
  note: string;
  loading: boolean;
}

function KpiCard({ label, value, delta, trend, icon, note, loading }: KpiCardProps) {
  const trendStyles = {
    up: "text-emerald-400 bg-emerald-500/10 ring-1 ring-emerald-500/20",
    down: "text-red-400 bg-red-500/10 ring-1 ring-red-500/20",
    warning: "text-amber-400 bg-amber-500/10 ring-1 ring-amber-500/20",
  };

  const TrendIcon = trend === "warning" ? AlertTriangle : trend === "down" ? TrendingDown : TrendingUp;

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-white/5 bg-zinc-900/40 p-6 backdrop-blur-xl transition-all duration-300 hover:border-white/10">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg border border-white/5 bg-white/5 text-zinc-300">
            {icon}
          </div>
          <span className="text-sm font-medium text-zinc-400">{label}</span>
        </div>
        {!loading && (
          <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold animate-fade-in ${trendStyles[trend]}`}>
            <TrendIcon className="size-3.5" />
            {delta}
          </span>
        )}
      </div>

      <div className="mt-5">
        {loading ? (
          <div className="h-9 w-28 rounded bg-zinc-800 animate-pulse" />
        ) : (
          <p className="text-3xl font-semibold tracking-tight text-white tabular-nums animate-fade-in">
            {value}
          </p>
        )}
      </div>
      
      <p className="mt-2 text-xs text-zinc-500 tracking-wide">{note}</p>
    </div>
  );
}

function ProjectRow({ name, client, status, allocation }: any) {
  const statusColors: any = {
    "on_track": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    "at_risk": "text-amber-400 bg-amber-400/10 border-amber-400/20",
    "delayed": "text-red-400 bg-red-400/10 border-red-400/20",
  };
  const statusKey = status ? status.toLowerCase().replace(" ", "_") : "on_track";
  const color = statusColors[statusKey] || "text-zinc-400 bg-zinc-400/10 border-zinc-400/20";

  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/5">
      <div>
        <h3 className="text-sm font-medium text-zinc-200">{name}</h3>
        <p className="text-xs text-zinc-500">{client}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-zinc-400">{allocation} alloc</span>
        <span className={`text-[10px] uppercase font-semibold px-2 py-1 rounded border ${color}`}>
          {status ? status.replace("_", " ") : "ON TRACK"}
        </span>
      </div>
    </div>
  );
}
```

---

