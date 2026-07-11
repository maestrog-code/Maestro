"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { User, Bot } from "lucide-react";
import type { Message } from "@/store/useChatStore";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full gap-4 px-4 py-6 md:px-6",
        isUser ? "bg-transparent" : "bg-zinc-900/40 border-y border-white/5"
      )}
    >
      <div className="flex w-full max-w-4xl mx-auto gap-4 md:gap-6">
        <div
          className={cn(
            "flex shrink-0 items-center justify-center w-8 h-8 rounded-md mt-1",
            isUser
              ? "bg-zinc-800 text-zinc-300 border border-white/10"
              : "bg-blue-600/20 text-blue-400 border border-blue-500/20"
          )}
        >
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>
        <div className="flex flex-col flex-1 min-w-0">
          <div className="text-sm font-medium text-zinc-400 mb-1">
            {isUser ? "You" : "MAESTRO"}
          </div>
          <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-zinc-900/50 prose-pre:border prose-pre:border-white/10">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
