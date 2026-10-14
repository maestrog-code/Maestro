"use client";

import React, { useState } from "react";
import { useFormState, useFormStatus } from "react-dom";
import Link from "next/link";
import { MaestroLogo } from "@/components/ui/MaestroLogo";
import { signupAction } from "@/app/actions/auth";
import { Building, Lock, Mail, ArrowRight } from "lucide-react";

const initialState = {
  error: "",
};

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {pending ? "Provisioning Workspace..." : "Initialize Workspace"}
      {!pending && <ArrowRight size={16} />}
    </button>
  );
}

export default function SignupPage() {
  const [state, formAction] = useFormState(signupAction, initialState);

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#050505] font-sans px-6">
      {/* Background Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(59,130,246,0.05),transparent_50%)] pointer-events-none" />

      <div className="w-full max-w-sm relative z-10">
        <div className="flex flex-col items-center mb-8 text-center">
          <MaestroLogo className="w-12 h-12 mb-4" />
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">Deploy MAESTRO</h1>
          <p className="text-sm text-zinc-500 mt-2">Provision a new enterprise workspace.</p>
        </div>

        <div className="rounded-2xl border border-white/5 bg-zinc-900/40 p-6 backdrop-blur-xl">
          <form action={formAction} className="space-y-4">
            
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Organization Name
              </label>
              <div className="relative">
                <Building className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 size-4" />
                <input
                  type="text"
                  name="company"
                  required
                  placeholder="Acme Corp"
                  className="w-full rounded-lg border border-white/10 bg-black/50 py-2.5 pl-10 pr-4 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Admin Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 size-4" />
                <input
                  type="email"
                  name="email"
                  required
                  placeholder="admin@acmecorp.com"
                  className="w-full rounded-lg border border-white/10 bg-black/50 py-2.5 pl-10 pr-4 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Master Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 size-4" />
                <input
                  type="password"
                  name="password"
                  required
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-white/10 bg-black/50 py-2.5 pl-10 pr-4 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all"
                />
              </div>
            </div>

            {state?.error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400 text-center">
                {state.error}
              </div>
            )}

            <div className="pt-2">
              <SubmitButton />
            </div>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-zinc-500">
          Already have clearance?{" "}
          <Link href="/login" className="text-blue-400 hover:text-blue-300 transition-colors font-medium">
            Access Dashboard
          </Link>
        </p>
      </div>
    </div>
  );
}
