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
