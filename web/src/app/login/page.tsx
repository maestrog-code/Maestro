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
