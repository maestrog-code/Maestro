import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Clock,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  Users,
  AlertTriangle,
  FileText,
  FolderKanban,
} from "lucide-react";

type Trend = "up" | "down" | "warning";

interface KpiCardProps {
  label: string;
  value: string;
  trendValue: string;
  trend: Trend;
  icon: React.ReactNode;
  hint: string;
}

const trendStyles: Record<Trend, { text: string; bg: string; border: string }> = {
  up: {
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
  down: {
    text: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/20",
  },
  warning: {
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
};

function KpiCard({ label, value, trendValue, trend, icon, hint }: KpiCardProps) {
  const styles = trendStyles[trend];
  const TrendIcon = trend === "down" ? TrendingDown : trend === "warning" ? AlertTriangle : TrendingUp;

  return (
    <div className="relative flex flex-col justify-between rounded-2xl bg-zinc-900/40 border border-white/5 p-5 backdrop-blur-md overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none" />
      <div className="relative flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
          <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-white/[0.03] border border-white/5 text-zinc-400">
            {icon}
          </span>
          {label}
        </span>
        <span
          className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${styles.text} ${styles.bg} border ${styles.border}`}
        >
          <TrendIcon size={12} />
          {trendValue}
        </span>
      </div>
      <div className="relative mt-6">
        <p className="text-3xl font-bold tracking-tight text-zinc-100 tabular-nums">{value}</p>
        <p className="mt-1 text-xs text-zinc-500">{hint}</p>
      </div>
    </div>
  );
}

interface ProjectRowProps {
  name: string;
  client: string;
  status: string;
  statusColor: "blue" | "emerald" | "amber";
  allocation: number;
}

const statusColorStyles = {
  blue: { text: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", bar: "bg-blue-500" },
  emerald: { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", bar: "bg-emerald-500" },
  amber: { text: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", bar: "bg-amber-500" },
};

function ProjectRow({ name, client, status, statusColor, allocation }: ProjectRowProps) {
  const styles = statusColorStyles[statusColor];
  return (
    <div className="flex flex-col gap-3 rounded-xl bg-white/[0.02] border border-white/5 p-4 transition-colors hover:bg-white/[0.04]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-zinc-200 truncate">{name}</p>
          <p className="text-xs text-zinc-500 truncate">{client}</p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${styles.text} ${styles.bg} border ${styles.border}`}
        >
          {status}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1 rounded-full bg-white/5 overflow-hidden">
          <div className={`h-full rounded-full ${styles.bar}`} style={{ width: `${allocation}%` }} />
        </div>
        <span className="w-10 text-right text-xs font-mono font-medium text-zinc-400 tabular-nums">
          {allocation}%
        </span>
      </div>
    </div>
  );
}

const BRIEFING_MARKDOWN = `## Executive Summary

Q2 closed **ahead of plan** on both revenue and margin. Gross revenue of **$478.5K** reflects a **+6.3%** lift quarter-over-quarter, driven primarily by expansion within existing enterprise accounts rather than new logo acquisition.

### Margin Analysis

Net margin expanded to **30.0%** (+2.5 pts), our strongest position in six quarters. The improvement is structural — automation of the delivery pipeline reduced per-project overhead — and should hold through Q3.

> The margin story is durable, but it masks a growing capacity constraint.

### The Constraint: Engineering

Engineering utilization has climbed to **92%**, well past the 80% comfort threshold. At current velocity we are:

- Deferring two roadmap initiatives into Q3
- Absorbing overflow through contractor spend (margin-dilutive)
- Carrying elevated burnout and attrition risk

### Recommendation

**Open two senior engineering roles this quarter.** The math is favorable: incremental payroll is comfortably covered by the current margin surplus, and unlocking capacity protects the expansion pipeline that is fueling revenue growth.
`;

export function ExecutiveDashboard() {
  return (
    <section className="w-full max-w-6xl mx-auto p-6 flex flex-col gap-6">
      {/* Header */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 text-balance">
            Q2 Financial &amp; Operations Overview
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Consolidated executive metrics across finance and delivery.
          </p>
        </div>
        <span className="inline-flex items-center gap-2 self-start rounded-full bg-zinc-900/40 border border-white/5 px-3 py-1.5 text-xs font-medium text-zinc-400 backdrop-blur-md">
          <Clock size={13} className="text-emerald-400" />
          Generated: Today, 6:00 AM
        </span>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <KpiCard
          label="Gross Revenue"
          value="$478,500"
          trendValue="+6.3%"
          trend="up"
          icon={<DollarSign size={15} />}
          hint="vs. $450.1K last quarter"
        />
        <KpiCard
          label="Net Margin"
          value="30.0%"
          trendValue="+2.5%"
          trend="up"
          icon={<Percent size={15} />}
          hint="Strongest in six quarters"
        />
        <KpiCard
          label="Eng. Utilization"
          value="92%"
          trendValue="Over capacity"
          trend="warning"
          icon={<Users size={15} />}
          hint="Above 80% safe threshold"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Daily Briefing */}
        <div className="lg:col-span-2 rounded-2xl bg-zinc-900/40 border border-white/5 backdrop-blur-md overflow-hidden">
          <div className="flex items-center gap-2.5 border-b border-white/5 px-6 py-4">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <FileText size={16} />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">CEO Morning Briefing</h2>
              <p className="text-[11px] text-zinc-500">Auto-generated analysis</p>
            </div>
          </div>
          <div className="px-6 py-5 prose prose-invert prose-sm max-w-none prose-headings:tracking-tight prose-headings:text-zinc-100 prose-h2:text-base prose-h2:mt-0 prose-h3:text-sm prose-h3:text-zinc-300 prose-p:text-zinc-400 prose-p:leading-relaxed prose-strong:text-zinc-100 prose-strong:font-semibold prose-li:text-zinc-400 prose-li:marker:text-blue-400 prose-blockquote:border-l-blue-500/40 prose-blockquote:text-zinc-300 prose-blockquote:font-normal prose-blockquote:not-italic prose-a:text-blue-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{BRIEFING_MARKDOWN}</ReactMarkdown>
          </div>
        </div>

        {/* Right: Active Projects */}
        <div className="rounded-2xl bg-zinc-900/40 border border-white/5 backdrop-blur-md overflow-hidden flex flex-col">
          <div className="flex items-center gap-2.5 border-b border-white/5 px-6 py-4">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <FolderKanban size={16} />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Active Projects</h2>
              <p className="text-[11px] text-zinc-500">Resource allocation</p>
            </div>
          </div>
          <div className="flex flex-col gap-3 p-4">
            <ProjectRow
              name="Atlas Platform Migration"
              client="Northwind Corp"
              status="On Track"
              statusColor="emerald"
              allocation={64}
            />
            <ProjectRow
              name="Q3 Analytics Suite"
              client="Vertex Financial"
              status="In Progress"
              statusColor="blue"
              allocation={82}
            />
            <ProjectRow
              name="Mobile App Rebuild"
              client="Helios Retail"
              status="At Risk"
              statusColor="amber"
              allocation={97}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export default ExecutiveDashboard;
