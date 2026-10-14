'use client'

import { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  Command,
  GitBranch,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Workflow,
  X,
  Zap,
} from 'lucide-react'

const runs = [
  { name: 'Customer onboarding', id: 'run_8f3c2a', status: 'Running', agent: 'Atlas', started: '2m ago', progress: 72 },
  { name: 'Invoice reconciliation', id: 'run_8f3b19', status: 'Succeeded', agent: 'Ledger', started: '18m ago', progress: 100 },
  { name: 'Q4 support triage', id: 'run_8f39dd', status: 'Needs attention', agent: 'Scout', started: '41m ago', progress: 46 },
  { name: 'Vendor risk review', id: 'run_8f3621', status: 'Succeeded', agent: 'Sentinel', started: '1h ago', progress: 100 },
]

const agents = [
  { name: 'Atlas', role: 'Onboarding coordinator', state: 'Active', color: 'violet', load: '68%' },
  { name: 'Ledger', role: 'Finance operations', state: 'Active', color: 'cyan', load: '42%' },
  { name: 'Scout', role: 'Support intelligence', state: 'Paused', color: 'amber', load: '—' },
]

export default function Home() {
  const [mobileNav, setMobileNav] = useState(false)
  const [activeNav, setActiveNav] = useState('Overview')

  return (
    <main className="app-shell">
      <aside className={mobileNav ? 'sidebar sidebar-open' : 'sidebar'}>
        <div className="brand-row">
          <div className="brand-mark"><Workflow size={18} /></div>
          <span>maestro</span>
          <button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="workspace-switcher">
          <div className="workspace-avatar">M</div>
          <div><strong>Maestro HQ</strong><small>Workspace</small></div>
          <ChevronDown size={14} className="muted-icon" />
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          <p className="nav-label">Workspace</p>
          {[
            { label: 'Overview', icon: LayoutDashboard },
            { label: 'Runs', icon: Play, count: '12' },
            { label: 'Agents', icon: Bot },
            { label: 'Workflows', icon: GitBranch },
          ].map(({ label, icon: Icon, count }) => (
            <button key={label} className={activeNav === label ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveNav(label); setMobileNav(false) }}>
              <Icon size={17} /> <span>{label}</span>{count && <em>{count}</em>}
            </button>
          ))}
          <p className="nav-label nav-label-spaced">Manage</p>
          {[
            { label: 'Activity', icon: Activity },
            { label: 'Settings', icon: Settings2 },
          ].map(({ label, icon: Icon }) => <button key={label} className={activeNav === label ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveNav(label); setMobileNav(false) }}><Icon size={17} /><span>{label}</span></button>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="uptime-card"><div><span className="status-dot" /> Systems nominal</div><strong>99.98% <small>uptime</small></strong></div>
          <div className="user-row"><div className="user-avatar">JD</div><div><strong>Jordan Davis</strong><small>Admin</small></div><MoreHorizontal size={17} className="muted-icon" /></div>
        </div>
      </aside>

      {mobileNav && <button className="scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
      <section className="content">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumbs"><span>Workspace</span><span className="slash">/</span><strong>{activeNav}</strong></div>
          <div className="topbar-actions"><button className="icon-button" aria-label="Search"><Search size={18} /></button><button className="command-button"><Command size={15} /> <span>Search</span><kbd>⌘ K</kbd></button><button className="button primary"><Plus size={16} data-icon="inline-start" /> New run</button></div>
        </header>
        <div className="page-content">
          <div className="page-heading"><div><div className="eyebrow"><Sparkles size={14} /> Operations overview</div><h1>Good morning, Jordan</h1><p>Here's what's happening across your workspace.</p></div><button className="date-button">Last 24 hours <ChevronDown size={15} /></button></div>
          <div className="metric-grid">
            <Metric label="Active runs" value="12" delta="+3" detail="vs. previous period" icon={Zap} accent="purple" />
            <Metric label="Tasks completed" value="1,284" delta="+18.4%" detail="vs. previous period" icon={CheckCircle2} accent="green" />
            <Metric label="Avg. run time" value="4m 12s" delta="−12.6%" detail="vs. previous period" icon={Clock3} accent="blue" />
            <Metric label="Success rate" value="98.7%" delta="+0.8%" detail="vs. previous period" icon={ShieldCheck} accent="orange" />
          </div>

          <div className="section-grid">
            <section className="panel runs-panel"><div className="panel-header"><div><h2>Recent runs</h2><p>Monitor your latest workflow activity.</p></div><button className="text-button">View all <ArrowUpRight size={15} /></button></div><div className="table-wrap"><table><thead><tr><th>Workflow</th><th>Status</th><th>Agent</th><th>Started</th><th aria-label="Actions" /></tr></thead><tbody>{runs.map((run) => <tr key={run.id}><td><div className="run-name"><div className="run-icon"><Workflow size={15} /></div><div><strong>{run.name}</strong><small>{run.id}</small></div></div><div className="progress"><span style={{ width: `${run.progress}%` }} /></div></td><td><Status status={run.status} /></td><td><div className="agent-cell"><span className={`agent-dot ${run.agent.toLowerCase()}`} />{run.agent}</div></td><td className="muted-text">{run.started}</td><td><button className="table-more" aria-label={`More actions for ${run.name}`}><MoreHorizontal size={17} /></button></td></tr>)}</tbody></table></div></section>
            <section className="panel activity-panel"><div className="panel-header"><div><h2>Live activity</h2><p>Events from your workspace.</p></div><span className="live-pill"><span /> Live</span></div><div className="activity-list"><ActivityItem icon={CheckCircle2} tone="green" title="Invoice reconciliation completed" meta="Ledger · 2 minutes ago" /><ActivityItem icon={Bot} tone="purple" title="Atlas started a new run" meta="Customer onboarding · 5 minutes ago" /><ActivityItem icon={AlertTriangle} tone="amber" title="Run needs your attention" meta="Q4 support triage · 12 minutes ago" /><ActivityItem icon={ShieldCheck} tone="blue" title="Policy check passed" meta="Vendor risk review · 18 minutes ago" /></div></section>
          </div>

          <section className="panel agents-panel"><div className="panel-header"><div><h2>Your agents</h2><p>Manage the intelligence powering your workflows.</p></div><button className="text-button">Manage agents <ArrowUpRight size={15} /></button></div><div className="agents-grid">{agents.map((agent) => <div className="agent-card" key={agent.name}><div className={`large-agent-icon ${agent.color}`}><Bot size={20} /></div><div className="agent-card-copy"><div className="agent-title"><strong>{agent.name}</strong><span className={`agent-state ${agent.state.toLowerCase()}`}><Circle size={7} fill="currentColor" /> {agent.state}</span></div><p>{agent.role}</p><div className="load-row"><span>Current load</span><strong>{agent.load}</strong></div><div className="load-bar"><span className={agent.color} style={{ width: agent.load === '—' ? '0%' : agent.load }} /></div></div><button className="table-more" aria-label={`More actions for ${agent.name}`}><MoreHorizontal size={17} /></button></div>)}</div></section>
          <footer className="footer"><span>Maestro platform</span><span>All systems operational</span><span>v0.8.4</span></footer>
        </div>
      </section>
    </main>
  )
}

function Metric({ label, value, delta, detail, icon: Icon, accent }: { label: string; value: string; delta: string; detail: string; icon: typeof Zap; accent: string }) { return <div className="metric-card"><div className={`metric-icon ${accent}`}><Icon size={18} /></div><p>{label}</p><strong>{value}</strong><div className="metric-delta"><span>{delta}</span> {detail}</div></div> }
function Status({ status }: { status: string }) { const tone = status === 'Succeeded' ? 'success' : status === 'Running' ? 'running' : 'attention'; return <span className={`status ${tone}`}><span />{status}</span> }
function ActivityItem({ icon: Icon, tone, title, meta }: { icon: typeof CheckCircle2; tone: string; title: string; meta: string }) { return <div className="activity-item"><div className={`activity-icon ${tone}`}><Icon size={15} /></div><div><strong>{title}</strong><span>{meta}</span></div><MoreHorizontal size={16} className="muted-icon" /></div> }
