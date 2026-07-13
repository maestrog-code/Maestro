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
