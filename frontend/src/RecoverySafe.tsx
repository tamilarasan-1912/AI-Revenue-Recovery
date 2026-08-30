import { useMemo, useState } from 'react'
import { Activity, AlertTriangle, BarChart3, CheckCircle2, Eye, Gavel, Play, Shield, XCircle, Zap } from 'lucide-react'

type CaseData = {
  payment_id: string
  amount: number
  failure_reason: string
  recommended_action: string
  policy_decision: 'allow' | 'human_review' | 'stop'
  policy_rules: string[]
  ai_confidence: number
  ml_recoverability: number
  policy_version: string
  requires_human_review: boolean
  can_execute: boolean
  retryable: boolean
}

const CASES: CaseData[] = [
  {
    payment_id: 'SIM-REC-0001', amount: 7499, failure_reason: 'Bank timeout detected; payment is suitable for a controlled retry.',
    recommended_action: 'RETRY', policy_decision: 'allow', policy_rules: ['confidence_above_threshold', 'retry_budget_available'],
    ai_confidence: 0.94, ml_recoverability: 0.91, policy_version: 'v1.4', requires_human_review: false, can_execute: true, retryable: true,
  },
  {
    payment_id: 'SIM-REC-0002', amount: 2899, failure_reason: 'Insufficient funds detected; payment link is preferred over repeated retries.',
    recommended_action: 'PAYMENT_LINK', policy_decision: 'allow', policy_rules: ['recoverable_failure', 'safe_intervention'],
    ai_confidence: 0.90, ml_recoverability: 0.84, policy_version: 'v1.4', requires_human_review: false, can_execute: true, retryable: false,
  },
  {
    payment_id: 'SIM-REC-0003', amount: 19999, failure_reason: 'Fraud signal detected; recovery action must be stopped.',
    recommended_action: 'STOP', policy_decision: 'stop', policy_rules: ['fraud_signal', 'unsafe_recovery_block'],
    ai_confidence: 0.97, ml_recoverability: 0.04, policy_version: 'v1.4', requires_human_review: false, can_execute: false, retryable: false,
  },
  {
    payment_id: 'SIM-REC-0004', amount: 12500, failure_reason: 'Insufficient evidence for automatic recovery; merchant approval is required.',
    recommended_action: 'HUMAN_ESCALATION', policy_decision: 'human_review', policy_rules: ['low_confidence', 'human_approval_required'],
    ai_confidence: 0.42, ml_recoverability: 0.58, policy_version: 'v1.4', requires_human_review: true, can_execute: false, retryable: true,
  },
]

const money = (v: number) => `₹${Math.round(v).toLocaleString('en-IN')}`
const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const titleCase = (v: string) => v.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())

export default function RecoverySafe() {
  const [index, setIndex] = useState(0)
  const [executed, setExecuted] = useState(false)
  const [message, setMessage] = useState('')
  const current = CASES[index]
  const display = useMemo(() => ({ ...current, can_execute: current.can_execute && !executed }), [current, executed])

  const runCase = () => {
    setIndex((index + 1) % CASES.length)
    setExecuted(false)
    setMessage('Recovery case evaluated in isolated simulation mode.')
  }

  const execute = () => {
    if (!display.can_execute) return
    setExecuted(true)
    setMessage('Executor outcome: SIMULATED_SUCCESS — no real payment was initiated.')
  }

  const tone = display.policy_decision === 'allow' ? 'green' : display.policy_decision === 'human_review' ? 'amber' : 'red'

  return <div style={{ minHeight: '100vh', background: '#f7f9fb', color: '#17191d', fontFamily: 'Inter, system-ui, sans-serif' }}>
    <header style={{ height: 64, background: '#fff', borderBottom: '1px solid #d7dbe0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px', boxSizing: 'border-box' }}>
      <div><b style={{ fontSize: 22 }}>RecoverAI</b><div style={{ fontSize: 11, color: '#656a73', fontWeight: 700 }}>Automated Intelligence</div></div>
      <div style={{ display: 'flex', gap: 24, alignItems: 'center', fontSize: 14, fontWeight: 700 }}><span>Recovery Control</span><a href="/simulation" style={{ color: '#17191d', textDecoration: 'none' }}>Simulation Lab</a><span style={{ border: '1px solid #c7cbd1', padding: '7px 10px', borderRadius: 5 }}>Test Mode</span></div>
    </header>

    <main style={{ maxWidth: 1180, margin: '0 auto', padding: '34px 24px 60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', marginBottom: 20 }}>
        <div><h1 style={{ margin: 0, fontSize: 34 }}>Revenue Recovery Control Center</h1><p style={{ color: '#656a73', marginTop: 8 }}>Monitor failed payments, recover eligible revenue, and prevent unsafe recovery actions.</p></div>
        <button onClick={runCase} style={{ border: '1px solid #c7cbd1', background: '#fff', borderRadius: 6, padding: '10px 14px', fontWeight: 700, cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'center' }}><Play size={16}/> Run Recovery Case</button>
      </div>

      {message && <div style={{ marginBottom: 18, padding: 12, borderRadius: 7, background: '#eef5ff', border: '1px solid #bfd7ff', display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}><Activity size={16}/>{message}</div>}

      <section style={{ background: '#fff', border: '1px solid #d7dbe0', borderRadius: 10, padding: 20, marginBottom: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start' }}>
          <div><h2 style={{ margin: 0, fontSize: 20 }}>Decision Pipeline</h2><p style={{ color: '#656a73', fontSize: 13 }}>ML predicts → AI recommends → Policy authorizes → Executor acts</p></div>
          <select value={index} onChange={e => { setIndex(Number(e.target.value)); setExecuted(false); setMessage('') }} style={{ height: 40, border: '1px solid #c7cbd1', borderRadius: 6, padding: '0 10px', fontWeight: 600 }}>
            {CASES.map((c, i) => <option key={c.payment_id} value={i}>{c.payment_id}</option>)}
          </select>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(80px,1fr))', gap: 8, marginTop: 24 }}>
          {[[XCircle, 'Payment Failed'], [BarChart3, 'ML Risk'], [Activity, 'Diagnosis'], [Zap, 'AI Strategy'], [Gavel, 'Policy Gate'], [Play, 'Executor'], [CheckCircle2, 'Outcome']].map(([Icon, label], i) => { const I = Icon as typeof Activity; return <div key={String(label)} style={{ textAlign: 'center' }}><div style={{ width: 44, height: 44, borderRadius: 99, margin: '0 auto 8px', display: 'grid', placeItems: 'center', background: i === 6 && executed ? '#dff5e8' : i === 0 ? '#fee4e2' : i === 1 || i === 3 ? '#e5f0ff' : '#eef0f2', color: i === 0 ? '#c62828' : '#176b4c' }}><I size={20}/></div><small style={{ fontWeight: 700 }}>{String(label)}</small></div> })}
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18 }}>
        <section style={{ background: '#fff', border: '1px solid #d7dbe0', borderRadius: 10, padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 22 }}><div><small style={{ color: '#656a73', fontWeight: 800 }}>TRANSACTION</small><div style={{ fontSize: 20, fontWeight: 900, marginTop: 4 }}>{display.payment_id}</div></div><div><small style={{ color: '#656a73', fontWeight: 800 }}>AMOUNT</small><div style={{ fontSize: 20, fontWeight: 900, marginTop: 4 }}>{money(display.amount)}</div></div></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 18 }}>
            <div style={{ background: '#f7f9fb', border: '1px solid #e1e4e8', borderRadius: 8, padding: 16 }}><div style={{ fontWeight: 900, fontSize: 12, letterSpacing: '.08em', display: 'flex', gap: 7, alignItems: 'center' }}><Zap size={16}/> AI DIAGNOSIS</div><p style={{ lineHeight: 1.6, fontSize: 14 }}>{display.failure_reason}</p><small style={{ color: '#656a73', fontWeight: 800 }}>AI RECOMMENDATION</small><div style={{ fontSize: 18, fontWeight: 900, marginTop: 5 }}>{titleCase(display.recommended_action)}</div></div>
            <div><small style={{ color: '#656a73', fontWeight: 800 }}>POLICY DECISION</small><div style={{ marginTop: 8, display: 'inline-flex', padding: '6px 10px', borderRadius: 6, fontWeight: 800, background: tone === 'green' ? '#e5f6eb' : tone === 'amber' ? '#fff4d8' : '#fee8e6', color: tone === 'green' ? '#176b4c' : tone === 'amber' ? '#8a6200' : '#b42318' }}>{titleCase(display.policy_decision)}</div><div style={{ marginTop: 20, display: 'grid', gap: 12 }}><div><small>AI Confidence</small><b style={{ float: 'right' }}>{pct(display.ai_confidence)}</b></div><div><small>ML Recoverability</small><b style={{ float: 'right' }}>{pct(display.ml_recoverability)}</b></div></div></div>
          </div>
          {display.can_execute && <button onClick={execute} style={{ marginTop: 20, border: 0, background: '#176b4c', color: '#fff', borderRadius: 6, padding: '11px 16px', fontWeight: 800, cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'center' }}><CheckCircle2 size={16}/> Authorize & Execute (Simulation)</button>}
        </section>

        <section style={{ background: '#fff', border: '1px solid #d7dbe0', borderRadius: 10, padding: 20 }}>
          <h2 style={{ fontSize: 18, marginTop: 0 }}>Safety & Recovery Plan</h2>
          <div style={{ display: 'grid', gap: 14, marginTop: 18 }}>
            <div><Shield size={16} style={{ verticalAlign: 'middle', marginRight: 8 }}/> Policy version <b style={{ float: 'right' }}>{display.policy_version}</b></div>
            <div><Activity size={16} style={{ verticalAlign: 'middle', marginRight: 8 }}/> Retryable <b style={{ float: 'right' }}>{display.retryable ? 'YES' : 'NO'}</b></div>
            <div><AlertTriangle size={16} style={{ verticalAlign: 'middle', marginRight: 8 }}/> Rules triggered <b style={{ float: 'right' }}>{display.policy_rules.length}</b></div>
            <div><Eye size={16} style={{ verticalAlign: 'middle', marginRight: 8 }}/> Human review <b style={{ float: 'right' }}>{display.requires_human_review ? 'REQUIRED' : 'NO'}</b></div>
          </div>
          <div style={{ marginTop: 24, padding: 12, border: '1px solid #d7dbe0', borderRadius: 7, fontSize: 12, color: '#656a73' }}>This fallback is isolated from payment providers. No real-money transaction is initiated.</div>
        </section>
      </div>
    </main>
  </div>
}
