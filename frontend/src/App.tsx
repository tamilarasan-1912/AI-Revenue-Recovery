import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

type Metrics = {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  unsafe_actions_blocked: number;
  human_escalations: number;
};

function money(value: number) {
  return `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function Card({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>{hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}</div>;
}

function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { fetch(`${API}/analytics/dashboard`).then(r => { if (!r.ok) throw new Error('Backend unavailable'); return r.json(); }).then(setMetrics).catch(e => setError(e.message)); }, []);
  return <div className="space-y-6">
    <div><p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Revenue recovery control room</p><h2 className="mt-1 text-3xl font-bold text-slate-950">Executive Dashboard</h2><p className="mt-2 text-slate-600">Detect → diagnose → policy-gate → recover → audit.</p></div>
    {error && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}. Start the backend and refresh.</div>}
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <Card label="Revenue at risk" value={money(metrics?.revenue_at_risk || 0)} />
      <Card label="Revenue recovered" value={money(metrics?.revenue_recovered || 0)} />
      <Card label="Recovery rate" value={`${metrics?.recovery_rate || 0}%`} />
      <Card label="Unsafe actions blocked" value={String(metrics?.unsafe_actions_blocked || 0)} />
      <Card label="Human escalations" value={String(metrics?.human_escalations || 0)} />
    </div>
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 className="font-semibold">Decision pipeline</h3><div className="mt-5 space-y-3 text-sm">{['Payment failure received','Risk and root cause classified','Recovery strategy proposed','Deterministic policy evaluated','Safe outcome recorded'].map((x, i) => <div key={x} className="flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">{i + 1}</span><span>{x}</span></div>)}</div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 className="font-semibold">Safety boundary</h3><p className="mt-3 text-sm leading-6 text-slate-600">The AI can recommend an intervention, but it cannot authorize execution. Fraud signals stop recovery, retry limits stop repeated attempts, and low confidence routes cases to human review.</p><div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm font-medium">AI proposes → Policy controls → Executor acts</div></section>
    </div>
  </div>;
}

function SimulationLab() {
  const [size, setSize] = useState(10000); const [result, setResult] = useState<any>(null);
  return <div className="space-y-6"><div><p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Evidence</p><h2 className="mt-1 text-3xl font-bold">Simulation Lab</h2><p className="mt-2 text-slate-600">Compare bounded recovery against a blind-retry baseline.</p></div><div className="rounded-2xl border bg-white p-6 shadow-sm"><label className="text-sm font-medium">Cohort size</label><input type="number" min="100" max="100000" value={size} onChange={e => setSize(Number(e.target.value))} className="ml-3 rounded-lg border p-2"/><button onClick={() => fetch(`${API}/simulation/run?size=${size}`, { method: 'POST' }).then(r => r.json()).then(setResult)} className="ml-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Run evaluation</button>{result && <pre className="mt-5 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-white">{JSON.stringify(result, null, 2)}</pre>}</div></div>;
}

function AuditLog() {
  const [logs, setLogs] = useState<any[]>([]); useEffect(() => { fetch(`${API}/audit/?limit=50`).then(r => r.json()).then(setLogs).catch(() => setLogs([])); }, []);
  return <div className="space-y-6"><div><p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Traceability</p><h2 className="mt-1 text-3xl font-bold">Audit Log</h2></div><div className="overflow-x-auto rounded-2xl border bg-white shadow-sm"><table className="min-w-full text-left text-sm"><thead className="border-b bg-slate-50"><tr><th className="p-4">Event</th><th className="p-4">Payment</th><th className="p-4">Action</th><th className="p-4">Outcome</th><th className="p-4">Time</th></tr></thead><tbody>{logs.map((l: any) => <tr key={l.id} className="border-b last:border-0"><td className="p-4 font-mono text-xs">{l.event_id}</td><td className="p-4 font-mono text-xs">{l.payment_id}</td><td className="p-4">{l.action}</td><td className="p-4">{l.outcome}</td><td className="p-4 text-slate-500">{l.timestamp}</td></tr>)}</tbody></table>{logs.length === 0 && <p className="p-6 text-sm text-slate-500">No audit events yet.</p>}</div></div>;
}

export default function App() {
  return <BrowserRouter><div className="flex min-h-screen bg-slate-100"><aside className="w-64 shrink-0 bg-slate-950 p-6 text-white"><h1 className="text-2xl font-bold">Recover<span className="text-blue-400">AI</span></h1><p className="mt-2 text-xs text-slate-400">Revenue recovery control plane</p><nav className="mt-8 space-y-2"><Link to="/" className="block rounded-lg px-3 py-2 hover:bg-white/10">Dashboard</Link><Link to="/simulation" className="block rounded-lg px-3 py-2 hover:bg-white/10">Simulation Lab</Link><Link to="/audit" className="block rounded-lg px-3 py-2 hover:bg-white/10">Audit Log</Link></nav><div className="mt-10 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-300">SIMULATION MODE<br/><span className="text-slate-500">No real-money movement</span></div></aside><main className="flex-1 overflow-auto p-6 lg:p-10"><Routes><Route path="/" element={<Dashboard />} /><Route path="/simulation" element={<SimulationLab />} /><Route path="/audit" element={<AuditLog />} /></Routes></main></div></BrowserRouter>;
}
