# MAESTRO — Sprint 012 Step 1 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 012 Step 1.
This document contains the Next.js Server Actions for auth, the new SVG MaestroLogo component, the sidebar implementation in page.tsx, and the backend auth dependency update.

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

    const res = await fetch("http://localhost:8000/api/v1/auth/login", {
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
    cookies().set("maestro_session", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: maxAge,
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

## `../../web/src/components/ui/MaestroLogo.tsx`

```tsx
import React from 'react';

interface MaestroLogoProps {
  className?: string;
}

export function MaestroLogo({ className = "w-10 h-10" }: MaestroLogoProps) {
  return (
    <svg 
      viewBox="0 0 100 100" 
      className={className} 
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <filter id="neonGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* Connecting strokes */}
      <path 
        d="M20 80 L35 30 L50 60 L65 30 L80 80" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="4" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        className="text-zinc-600"
      />

      {/* Base nodes (circles) */}
      <circle cx="20" cy="80" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="35" cy="30" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="65" cy="30" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />
      <circle cx="80" cy="80" r="5" className="fill-zinc-800 stroke-zinc-700" strokeWidth="2" />

      {/* Glowing Center Core */}
      <circle 
        cx="50" 
        cy="60" 
        r="6" 
        className="fill-cyan-400" 
        filter="url(#neonGlow)"
      />
    </svg>
  );
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

## `../../web/src/app/login/page.tsx`

```tsx
"use client";

import React, { useState } from "react";
import { loginAction } from "@/app/actions/auth";
import { MaestroLogo } from "@/components/ui/MaestroLogo";
import { ArrowRight, Loader2, ShieldAlert } from "lucide-react";
import { useFormState, useFormStatus } from "react-dom";

// Note: Using React 19's useFormState. If using an older React, this would need custom useState logic.
// We'll just manage state manually for maximum compatibility if useFormState isn't available, but since Next.js 14+ supports it via react-dom, we can use it.
// Actually, to be extremely robust without worrying about experimental flags, let's use a standard useState wrapper around the server action.

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsPending(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const result = await loginAction(null, formData);

    if (result?.error) {
      setError(result.error);
      setIsPending(false);
    }
    // On success, loginAction handles the redirect, so we don't need to unset isPending
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#050505] text-zinc-100 font-sans relative overflow-hidden">
      {/* Dynamic radial glow background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(59,130,246,0.05),transparent_50%),radial-gradient(circle_at_50%_100%,rgba(147,51,234,0.05),transparent_50%)] pointer-events-none" />

      <div className="relative z-10 w-full max-w-md px-6">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-white/[0.02] border border-white/5 shadow-2xl mb-6">
            <MaestroLogo className="w-14 h-14" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 mb-2">
            Welcome to MAESTRO
          </h1>
          <p className="text-sm text-zinc-500 text-center">
            Authenticate to access the Executive Board Room.
          </p>
        </div>

        <div className="rounded-2xl border border-white/5 bg-zinc-900/40 p-8 backdrop-blur-xl shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="flex items-center gap-2 p-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg animate-fade-in">
                <ShieldAlert size={16} className="shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
                Executive Email
              </label>
              <input
                name="email"
                type="email"
                required
                placeholder="executive@maestro.ai"
                className="w-full bg-zinc-950/50 border border-white/5 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
                Security Clearance
              </label>
              <input
                name="password"
                type="password"
                required
                placeholder="••••••••••••"
                className="w-full bg-zinc-950/50 border border-white/5 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full flex items-center justify-center gap-2 bg-zinc-100 hover:bg-white text-zinc-900 py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <>
                  Initialize Session <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono">
            Secure Endpoint Connection
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

## `app/dependencies/auth.py`

```py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies.database import get_db
from app.modules.users.repositories import user_repository
from app.modules.users.models import User
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = request.cookies.get("maestro_session")
    if not token:
        authorization: str = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_repository.get(db, id=uuid.UUID(user_id))
    if user is None:
        raise credentials_exception
    return user
```

---

## `app/core/auth/router.py`

```py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.core.auth.schemas import LoginRequest, AuthResponse, Token
from app.modules.users.schemas import UserCreate, UserResponse
from app.core.auth.services import authenticate_user, create_refresh_token
from app.modules.users.services import create_user
from app.core.security.jwt import create_access_token
from datetime import timedelta

router = APIRouter()

@router.post("/register", response_model=AuthResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, user_in)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = await create_refresh_token(db, user.id)
    return AuthResponse(
        user=user,
        token=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/login", response_model=AuthResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    login_req = LoginRequest(email=form_data.username, password=form_data.password)
    user = await authenticate_user(db, login_req)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    access_token = create_access_token(subject=str(user.id))
    refresh_token = await create_refresh_token(db, user.id)
    return AuthResponse(
        user=user,
        token=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/verify-email")
async def verify_email(token: str):
    # Placeholder for email verification
    return {"message": "Email verified"}

@router.post("/password-reset")
async def password_reset(email: str):
    # Placeholder for password reset
    return {"message": "Password reset email sent"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    # Placeholder for token rotation
    return {"message": "Token refreshed"}

@router.post("/revoke")
async def revoke_token(token: str):
    # Placeholder for token revocation/blacklisting
    return {"message": "Token revoked"}
```

---

