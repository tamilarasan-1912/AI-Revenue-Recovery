import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PaymentsSafe from './PaymentsSafe'
import './index.css'
import './industry-fixes.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

type AuditEvent = {
  event_id?: string
  payment_id?: string
  action?: string
  outcome?: string
  timestamp?: string
}

function normalizeAudit(payload: unknown): AuditEvent[] {
  if (Array.isArray(payload)) return payload.filter(Boolean) as AuditEvent[]
  if (payload && typeof payload === 'object') {
    const value = payload as Record<string, unknown>
    const candidates = [value.events, value.audit, value.records, value.items, value.data]
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) return candidate.filter(Boolean) as AuditEvent[]
    }
  }
  return []
}

function AuditRecoveryPage() {
  const [rows, setRows] = useState<AuditEvent[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/audit/?limit=100`, { headers: { Accept: 'application/json' } })
      const raw = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error((raw as any)?.detail || (raw as any)?.message || `Request failed (${response.status})`)
      setRows(normalizeAudit(raw))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load audit events')
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return (
    <div className="min-h-screen bg-[#f7f9fb] text-[#17191d]">
      <header className="flex h-16 items-center justify-between border-b border-[#d7dbe0] bg-white px-5 lg:px-8">
        <div>
          <div className="text-xl font-extrabold tracking-tight">RecoverAI</div>
          <div className="text-xs font-semibold text-[#656a73]">Automated Intelligence</div>
        </div>
        <div className="flex items-center gap-4 text-sm font-semibold">
          <span>Recovery Control</span><span>Simulation Lab</span><span className="rounded border px-3 py-1.5">Test Mode</span>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] p-5 lg:p-8">
        <div className="mb-7">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">Compliance & Traceability</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight">Audit Log</h1>
          <p className="mt-2 text-sm leading-6 text-[#656a73]">Trace every recovery decision, policy outcome and execution event.</p>
        </div>
        {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><b>Could not load audit events.</b><div className="mt-1">{error}</div><button onClick={() => void load()} className="mt-3 rounded bg-red-700 px-3 py-2 text-xs font-bold text-white">Retry</button></div>}
        <section className="overflow-hidden rounded-xl border border-[#d7dbe0] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-[#d7dbe0] p-5"><h2 className="text-xl font-bold">Decision & Execution Events</h2><button disabled={loading} onClick={() => void load()} className="rounded border border-[#c8cbd1] px-3 py-2 text-sm font-semibold">{loading ? 'Loading…' : 'Refresh'}</button></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-[#f0f2f5] text-xs font-bold uppercase"><tr>{['Event','Payment','Action','Outcome','Timestamp'].map(x => <th key={x} className="px-4 py-3">{x}</th>)}</tr></thead><tbody>
            {!rows.length ? <tr><td colSpan={5} className="p-10 text-center text-[#666a72]">{loading ? 'Loading audit events…' : 'No audit events available.'}</td></tr> : rows.map((r, i) => <tr key={`${r.event_id || r.payment_id || 'event'}-${i}`} className="border-t border-[#d9dbde]"><td className="px-4 py-3 font-mono text-xs">{r.event_id || '—'}</td><td className="px-4 py-3 font-mono text-xs text-blue-700">{r.payment_id || '—'}</td><td className="px-4 py-3">{String(r.action || '—').replace(/_/g, ' ')}</td><td className="px-4 py-3 font-semibold">{String(r.outcome || '—').replace(/_/g, ' ')}</td><td className="px-4 py-3 whitespace-nowrap">{r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}</td></tr>)}
          </tbody></table></div>
        </section>
      </main>
    </div>
  )
}

class AppErrorBoundary extends React.Component<React.PropsWithChildren, { hasError: boolean; message: string }> {
  state = { hasError: false, message: '' }

  static getDerivedStateFromError(error: unknown) {
    return { hasError: true, message: error instanceof Error ? error.message : 'Unexpected application error' }
  }

  componentDidCatch(error: unknown) {
    console.error('RecoverAI application error:', error)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    if (window.location.pathname === '/payments') return <PaymentsSafe />
    if (window.location.pathname === '/audit') return <AuditRecoveryPage />

    return (
      <div className="min-h-screen bg-[#f7f9fb] p-8 text-[#17191d]">
        <div className="mx-auto mt-20 max-w-xl rounded-xl border border-red-200 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-extrabold">RecoverAI could not render this page</h1>
          <p className="mt-3 text-sm text-[#656a73]">The application recovered from the runtime crash instead of showing a blank screen.</p>
          <pre className="mt-4 overflow-auto rounded bg-red-50 p-3 text-xs text-red-700">{this.state.message}</pre>
          <button onClick={() => window.location.reload()} className="mt-5 rounded bg-black px-4 py-2.5 text-sm font-bold text-white">Reload application</button>
        </div>
      </div>
    )
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><AppErrorBoundary><App /></AppErrorBoundary></React.StrictMode>
)
