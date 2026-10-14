# MAESTRO — Sprint 011 Step 2 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 011 Step 2 (Frontend Scaffold) is on branch `main`.
This document contains the Next.js layout and KPI card implementation.

---

## `../../web/src/components/dashboard/ExecutiveDashboard.tsx`

```tsx
"use client";

import React from "react";
import useSWR from "swr";
import { DollarSign, Percent, Cpu, Clock, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error("Failed to pull backend telemetry");
  return res.json();
});

interface ExecutiveDashboardProps {
  orgId: string;
}

export function ExecutiveDashboard({ orgId }: ExecutiveDashboardProps) {
  // Wire up the live API endpoint to SWR
  const { data: telemetry, error: metricsError } = useSWR(
    `http://localhost:8000/api/v1/organizations/${orgId}/dashboard/metrics`,
    fetcher,
    { refreshInterval: 30000 } // Auto-poll every 30 seconds
  );

  const isLoading = !telemetry && !metricsError;

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
          value={isLoading ? "..." : telemetry?.financials?.total_revenue}
          delta={isLoading ? "" : telemetry?.financials?.gross_revenue_delta}
          trend="up"
          icon={<DollarSign className="size-4" />}
          note={isLoading ? "Evaluating statement data..." : telemetry?.financials?.revenue_note}
          loading={isLoading}
        />

        {/* Card 2: Net Margin */}
        <KpiCard
          label="Net Margin"
          value={isLoading ? "..." : telemetry?.financials?.net_margin}
          delta={isLoading ? "" : telemetry?.financials?.net_margin_delta}
          trend="up"
          icon={<Percent className="size-4" />}
          note={isLoading ? "Rebalancing accounting rows..." : telemetry?.financials?.margin_note}
          loading={isLoading}
        />

        {/* Card 3: Team Bandwidth Utilization */}
        <KpiCard
          label="Team Utilization"
          value={isLoading ? "..." : telemetry?.operations?.avg_utilization}
          delta={isLoading ? "" : telemetry?.operations?.delta}
          trend={isLoading ? "up" : telemetry?.operations?.trend}
          icon={<Cpu className="size-4" />}
          note={isLoading ? "Auditing production allocation logs..." : telemetry?.operations?.note}
          loading={isLoading}
        />
      </section>

      {/* Placeholder grid zone for Step 3 components (Briefing and Projects Table) */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3 opacity-30 pointer-events-none">
        <div className="lg:col-span-2 border border-dashed border-white/10 rounded-2xl h-64 flex items-center justify-center text-xs font-mono text-zinc-500">
          [Step 3 — CEO Briefing Reader Dock]
        </div>
        <div className="border border-dashed border-white/10 rounded-2xl h-64 flex items-center justify-center text-xs font-mono text-zinc-500">
          [Step 3 — Active Projects Progress Table]
        </div>
      </div>
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
```

---

## `../../web/src/app/page.tsx`

```tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
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

const DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000000";

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

    await sendChatMessage(DEFAULT_ORG_ID, prompt, abortControllerRef.current.signal);
  };

  return (
    <div className="flex h-screen w-full bg-[#050505] text-zinc-100 overflow-hidden font-sans">
      {/* Dynamic radial glow background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.03),transparent_40%),radial-gradient(circle_at_70%_80%,rgba(147,51,234,0.03),transparent_40%)] pointer-events-none" />

      {/* Sidebar - Executive Team & Stats */}
      <aside className="hidden lg:flex flex-col w-80 bg-zinc-950 border-r border-white/5 relative z-10 flex-shrink-0">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400">
            <Bot size={22} />
          </div>
          <div>
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
          <ExecutiveDashboard orgId={DEFAULT_ORG_ID} />
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
          <ChatInput orgId={DEFAULT_ORG_ID} />
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

## `app/core/config.py`

```py
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Maestro"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000"]

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

