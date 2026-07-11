"use client";

import React, { useState, useRef, useEffect } from "react";
import { SendHorizontal } from "lucide-react";
import { sendChatMessage } from "@/lib/api/chat";
import { useChatStore } from "@/store/useChatStore";

export function ChatInput({ orgId }: { orgId: string }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isStreaming } = useChatStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;

    const message = input;
    setInput("");

    // Abort previous stream if any (though UI prevents it, good practice)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    await sendChatMessage(orgId, message, abortControllerRef.current.signal);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-4 md:px-6">
      <form
        onSubmit={handleSubmit}
        className="relative flex items-end w-full rounded-2xl bg-zinc-900 border border-white/10 shadow-lg overflow-hidden focus-within:ring-1 focus-within:ring-blue-500/50 focus-within:border-blue-500/50 transition-all"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask MAESTRO a question..."
          rows={1}
          className="w-full max-h-[200px] py-4 pl-5 pr-14 bg-transparent text-zinc-100 placeholder:text-zinc-500 resize-none focus:outline-none focus:ring-0 custom-scrollbar"
          disabled={isStreaming}
        />
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          className="absolute right-2 bottom-2 p-2 rounded-xl bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors flex items-center justify-center"
        >
          <SendHorizontal size={20} />
        </button>
      </form>
      <div className="text-center mt-3">
        <p className="text-[11px] text-zinc-500">
          MAESTRO AI Executives can make mistakes. Verify critical business data.
        </p>
      </div>
    </div>
  );
}
