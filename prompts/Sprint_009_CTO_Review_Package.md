# MAESTRO — Sprint 009 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 009 is on branch `feature/sprint-009-frontend-ui`.
This document contains every implementation file in full, exactly as committed.

---

## `package.json`

```json
{
  "name": "web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  },
  "dependencies": {
    "clsx": "^2.1.1",
    "framer-motion": "^11.11.11",
    "lucide-react": "^0.454.0",
    "next": "16.2.10",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "tailwind-merge": "^2.5.4",
    "zustand": "^5.0.14"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",
    "@tailwindcss/typography": "^0.5.20",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.2.10",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

---

## `postcss.config.mjs`

```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

---

## `src/app/globals.css`

```css
@import "tailwindcss";
@plugin "@tailwindcss/typography";

:root {
  --background: #050505;
  --foreground: #ededed;
  --card: #111111;
  --card-foreground: #ededed;
  --popover: #111111;
  --popover-foreground: #ededed;
  --primary: #ffffff;
  --primary-foreground: #000000;
  --secondary: #1a1a1a;
  --secondary-foreground: #ededed;
  --muted: #262626;
  --muted-foreground: #a3a3a3;
  --accent: #1f1f1f;
  --accent-foreground: #ededed;
  --destructive: #7f1d1d;
  --destructive-foreground: #fecaca;
  --border: #262626;
  --input: #262626;
  --ring: #d4d4d4;
  --radius: 0.75rem;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --radius-lg: var(--radius);
  --radius-md: calc(var(--radius) - 2px);
  --radius-sm: calc(var(--radius) - 4px);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: var(--font-sans), sans-serif;
  background-image: radial-gradient(circle at top, rgba(255, 255, 255, 0.05), transparent 40%),
                    radial-gradient(circle at bottom left, rgba(255, 255, 255, 0.02), transparent 40%);
  background-attachment: fixed;
  background-size: cover;
  min-height: 100vh;
}

/* Glassmorphism utilities */
.glass {
  background: rgba(17, 17, 17, 0.4);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-panel {
  background: rgba(17, 17, 17, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--muted);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--muted-foreground);
}

/* Animations */
@keyframes slide-in-right {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.animate-slide-in-right {
  animation: slide-in-right 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in {
  animation: fade-in 0.2s ease-out forwards;
}
```

---

## `src/store/useChatStore.ts`

```typescript
import { create } from "zustand";

export type MessageRole = "system" | "user" | "assistant" | "tool";

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface Message {
  id: string; // Unique ID, can be generated on client for optimistic updates
  role: MessageRole;
  content: string;
  name?: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

export interface ScratchpadEntry {
  step: string;
  status: string;
  notes: string | null;
}

export interface ActiveTool {
  tool_name: string;
  status: string;
}

interface ChatState {
  messages: Message[];
  agentState: string;
  activeTools: ActiveTool[];
  scratchpad: ScratchpadEntry[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  isSimulationMode: boolean;
  subAgentStreams: Record<string, string>;
  selectedSubAgentLog: string | null;

  // Actions
  addMessage: (message: Message) => void;
  appendTokenToLastAssistantMessage: (token: string) => void;
  appendSubAgentToken: (agentName: string, token: string) => void;
  clearSubAgentStreams: () => void;
  setSelectedSubAgentLog: (agentName: string | null) => void;
  setAgentState: (state: string) => void;
  updateScratchpad: (entry: ScratchpadEntry) => void;
  updateToolStatus: (tool: ActiveTool) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingMessageId: (id: string | null) => void;
  setIsSimulationMode: (isSimulationMode: boolean) => void;
  resetStreamState: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  agentState: "Idle",
  activeTools: [],
  scratchpad: [],
  isStreaming: false,
  streamingMessageId: null,
  isSimulationMode: false,
  subAgentStreams: {},
  selectedSubAgentLog: null,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  appendTokenToLastAssistantMessage: (token) =>
    set((state) => {
      const messages = [...state.messages];
      
      // Attempt to find the specific streaming assistant message
      if (state.streamingMessageId) {
        const idx = messages.findIndex((m) => m.id === state.streamingMessageId);
        if (idx !== -1) {
          messages[idx] = {
            ...messages[idx],
            content: messages[idx].content + token,
          };
          return { messages };
        }
      }

      // Fallback: Find the last assistant message and link it
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === "assistant") {
          messages[i] = {
            ...messages[i],
            content: messages[i].content + token,
          };
          return { messages, streamingMessageId: messages[i].id };
        }
      }

      // Fallback 2: If none exists, create a new one and link it
      const newId = crypto.randomUUID();
      const newMsg: Message = {
        id: newId,
        role: "assistant",
        content: token,
      };
      return { messages: [...messages, newMsg], streamingMessageId: newId };
    }),

  setAgentState: (agentState) => set({ agentState }),

  appendSubAgentToken: (agentName, token) =>
    set((state) => ({
      subAgentStreams: {
        ...state.subAgentStreams,
        [agentName]: (state.subAgentStreams[agentName] || "") + token,
      },
    })),

  clearSubAgentStreams: () => set({ subAgentStreams: {} }),

  setSelectedSubAgentLog: (selectedSubAgentLog) => set({ selectedSubAgentLog }),

  updateScratchpad: (entry) =>
    set((state) => {
      // If step already exists, update it; otherwise append
      const existingIdx = state.scratchpad.findIndex((s) => s.step === entry.step);
      if (existingIdx !== -1) {
        const newScratchpad = [...state.scratchpad];
        newScratchpad[existingIdx] = entry;
        return { scratchpad: newScratchpad };
      }
      return { scratchpad: [...state.scratchpad, entry] };
    }),

  updateToolStatus: (tool) =>
    set((state) => {
      if (tool.status === "completed" || tool.status === "failed") {
        return {
          activeTools: state.activeTools.filter((t) => t.tool_name !== tool.tool_name),
        };
      }
      // Add or update
      const existing = state.activeTools.find((t) => t.tool_name === tool.tool_name);
      if (existing) {
        return {
          activeTools: state.activeTools.map((t) =>
            t.tool_name === tool.tool_name ? tool : t
          ),
        };
      }
      return { activeTools: [...state.activeTools, tool] };
    }),

  setIsStreaming: (isStreaming) => set({ isStreaming }),

  setStreamingMessageId: (streamingMessageId) => set({ streamingMessageId }),

  setIsSimulationMode: (isSimulationMode) => set({ isSimulationMode }),

  resetStreamState: () =>
    set({
      agentState: "Idle",
      activeTools: [],
      isStreaming: false,
      streamingMessageId: null,
      isSimulationMode: false,
      subAgentStreams: {},
      selectedSubAgentLog: null,
    }),
}));
```

---

## `src/lib/api/chat.ts`

```typescript
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
    const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/ai/chat`, {
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

## `src/components/chat/AgentStatus.tsx`

```tsx
"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Zap, Cog, CheckCircle2, ChevronRight, Terminal } from "lucide-react";
import { useChatStore } from "@/store/useChatStore";

export function AgentStatus() {
  const { agentState, activeTools, scratchpad, isStreaming, subAgentStreams, setSelectedSubAgentLog } = useChatStore();

  if (!isStreaming && activeTools.length === 0 && scratchpad.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-4 md:px-6">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-4 rounded-xl flex flex-col gap-3 relative overflow-hidden"
      >
        {/* Animated Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-transparent opacity-50 pointer-events-none" />

        <div className="flex items-center gap-3">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            className="text-blue-400"
          >
            <Zap size={18} />
          </motion.div>
          <span className="text-sm font-medium text-zinc-200">
            {agentState !== "Idle" ? agentState : "Processing..."}
          </span>
        </div>

        <AnimatePresence>
          {scratchpad.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="flex flex-col gap-2 mt-2 pt-3 border-t border-white/10"
            >
              <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">
                Executive Plan
              </h4>
              {scratchpad.map((item, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <div className="mt-0.5 text-zinc-500">
                    {item.status === "COMPLETED" ? (
                      <CheckCircle2 size={14} className="text-green-500" />
                    ) : item.status === "IN_PROGRESS" ? (
                      <Loader2 size={14} className="animate-spin text-blue-400" />
                    ) : (
                      <ChevronRight size={14} />
                    )}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm text-zinc-300">{item.step}</span>
                    {item.notes && (
                      <span className="text-xs text-zinc-500 mt-0.5 italic">
                        {item.notes}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {activeTools.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="flex flex-wrap gap-2 mt-2 pt-2"
            >
              {activeTools.map((tool) => (
                <motion.div
                  key={tool.tool_name}
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-800/80 border border-white/5 text-xs text-zinc-300 shadow-sm"
                >
                  <Cog size={12} className="animate-spin text-zinc-400" />
                  <span>Running {tool.tool_name}...</span>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {Object.keys(subAgentStreams).length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="flex flex-col gap-2 mt-2 pt-3 border-t border-white/10"
            >
              <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">
                Active Executives
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.keys(subAgentStreams).map((agentName) => {
                  const isAgentActive = isStreaming && agentState.includes(agentName);
                  return (
                    <div
                      key={agentName}
                      className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/40 border border-white/5"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="relative flex items-center justify-center">
                          {isAgentActive ? (
                            <>
                              <span className="absolute inline-flex h-2 w-2 rounded-full bg-blue-400 opacity-75 animate-ping" />
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                            </>
                          ) : (
                            <span className="inline-flex rounded-full h-2 w-2 bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.4)]" />
                          )}
                        </div>
                        <span className="text-sm font-medium text-zinc-300">
                          {agentName} {agentName === "CFO" ? "(Finance)" : agentName === "COO" ? "(Operations)" : ""}
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedSubAgentLog(agentName)}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-300 border border-white/5 transition-colors cursor-pointer"
                      >
                        <Terminal size={12} className="text-zinc-400" />
                        <span>Inspect Logs</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
```

---

## `src/app/page.tsx`

```tsx
"use client";

import React, { useEffect, useRef } from "react";
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

