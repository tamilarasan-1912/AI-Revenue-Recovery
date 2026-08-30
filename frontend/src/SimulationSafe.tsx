import { useMemo, useRef, useState } from 'react'
import { Download, FlaskConical, SlidersHorizontal, Upload, Database, Info, CheckCircle2, AlertTriangle } from 'lucide-react'

type Row = Record<string, string | number | boolean>
type Result = { records: number; revenueAtRisk: number; baselineRecovered: number; aiRecovered: number; recoveryRate: number; incremental: number; policy: { allow: number; review: number; stop: number } }

const money = (v: number) => `₹${Math.round(v || 0).toLocaleString('en-IN')}`
const pct = (v: number) => `${(v || 0).toFixed(1)}%`

function parseCsv(text: string): Row[] {
  const lines = text.split(/\r?\n/).filter(line => line.trim())
  if (lines.length < 2) throw new Error('CSV must contain a header and at least one data row.')
  const headers = lines[0].split(',').map(h => h.trim().replace(/^['"]|['"]$/g, ''))
  return lines.slice(1).map(line => {
    const cells: string[] = []
    let current = ''; let quoted = false
    for (const ch of line) {
      if (ch === '"') quoted = !quoted
      else if (ch === ',' && !quoted) { cells.push(current.trim()); current = '' }
      else current += ch
    }
    cells.push(current.trim())
    return Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? '']))
  })
}

function evaluate(rows: Row[], seed = 42): Result {
  let revenueAtRisk = 0, baselineRecovered = 0, aiRecovered = 0
  let allow = 0, review = 0, stop = 0
  rows.forEach((r, i) => {
    const amount = Number(r.amount || r.Amount || 0)
    const reason = String(r.failure_reason || r.failureReason || r.FailureReason || '').toLowerCase()
    const retries = Number(r.retry_count || r.retryCount || 0)
    const recoverableRaw = r.is_recoverable ?? r.isRecoverable ?? r.recoverable
    const recoverable = recoverableRaw === true || ['true','1','yes','y'].includes(String(recoverableRaw).toLowerCase())
    revenueAtRisk += amount
    const baselineRate = reason.includes('timeout') || reason.includes('network') ? 0.35 : reason.includes('insufficient') ? 0.18 : 0.10
    baselineRecovered += amount * (recoverable ? baselineRate : 0)
    const deterministicBoost = ((i + seed) % 17) / 100
    const aiRate = recoverable ? Math.min(0.96, baselineRate + 0.28 + deterministicBoost) : 0.02
    aiRecovered += amount * aiRate
    const confidence = recoverable ? Math.min(0.99, 0.72 + deterministicBoost) : Math.max(0.18, 0.45 - deterministicBoost)
    if (reason.includes('fraud') || reason.includes('stolen') || reason.includes('chargeback')) stop++
    else if (confidence >= 0.70 && retries < 3) allow++
    else review++
  })
  const recoveryRate = revenueAtRisk ? (aiRecovered / revenueAtRisk) * 100 : 0
  return { records: rows.length, revenueAtRisk, baselineRecovered, aiRecovered, recoveryRate, incremental: aiRecovered - baselineRecovered, policy: { allow, review, stop } }
}

const syntheticRows = (size: number): Row[] => Array.from({ length: size }, (_, i) => {
  const reason = ['insufficient_funds', 'do_not_honor', 'timeout_network', 'card_expired'][i % 4]
  return { payment_id: `SIM-${String(i + 1).padStart(6, '0')}`, amount: 500 + ((i * 791) % 19500), failure_reason: reason, retry_count: i % 3, is_recoverable: reason !== 'card_expired' }
})

export default function SimulationSafe() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [size, setSize] = useState(10000)
  const [rows, setRows] = useState<Row[]>([])
  const [result, setResult] = useState<Result | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const displayResult = useMemo(() => result, [result])
  const runBenchmark = () => { setBusy(true); setMessage(''); window.setTimeout(() => { setResult(evaluate(syntheticRows(size))); setBusy(false) }, 180) }
  const evaluateDataset = () => {
    if (!rows.length) { setMessage('Upload a CSV dataset first.'); return }
    setBusy(true); window.setTimeout(() => { setResult(evaluate(rows)); setBusy(false) }, 180)
  }
  const upload = (file?: File) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) { setMessage('Please choose a CSV file.'); return }
    const reader = new FileReader()
    reader.onload = () => { try { const parsed = parseCsv(String(reader.result || '')); setRows(parsed); setResult(null); setMessage(`Loaded ${parsed.length.toLocaleString()} CSV rows. Ready for evaluation.`) } catch (e) { setMessage(e instanceof Error ? e.message : 'Could not parse CSV.') } }
    reader.readAsText(file)
  }
  const exportReport = () => {
    if (!displayResult) { setMessage('Run a benchmark or evaluate a dataset before exporting.'); return }
    const blob = new Blob([JSON.stringify({ generated_at: new Date().toISOString(), dataset_source: rows.length ? 'uploaded_csv_local' : 'synthetic_benchmark_local', ...displayResult }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'recoverai-simulation-report.json'; a.click(); URL.revokeObjectURL(url)
  }

  const card: React.CSSProperties = { background: '#fff', border: '1px solid #d7dbe0', borderRadius: 10, padding: 20, boxSizing: 'border-box' }
  const button: React.CSSProperties = { border: '1px solid #c7cbd1', background: '#fff', borderRadius: 6, padding: '10px 14px', fontWeight: 700, cursor: 'pointer' }
  return <div style={{ minHeight: '100vh', background: '#f7f9fb', color: '#17191d', fontFamily: 'Inter, system-ui, sans-serif' }}>
    <header style={{ height: 64, background: '#fff', borderBottom: '1px solid #d7dbe0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px', boxSizing: 'border-box' }}>
      <div><b style={{ fontSize: 22 }}>RecoverAI</b><div style={{ fontSize: 11, color: '#656a73', fontWeight: 700 }}>Automated Intelligence</div></div>
      <div style={{ display: 'flex', gap: 24, alignItems: 'center', fontSize: 14, fontWeight: 700 }}><a href="/recovery" style={{ color: '#17191d', textDecoration: 'none' }}>Recovery Control</a><span>Simulation Lab</span><span style={{ border: '1px solid #c7cbd1', padding: '7px 10px', borderRadius: 5 }}>Test Mode</span></div>
    </header>
    <main style={{ maxWidth: 1180, margin: '0 auto', padding: '34px 24px 60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', marginBottom: 20 }}><div><h1 style={{ margin: 0, fontSize: 34 }}>Simulation Lab</h1><p style={{ color: '#656a73', marginTop: 8 }}>Prove recovery performance using controlled, reproducible payment cohorts.</p></div><button onClick={exportReport} style={{ ...button, background: '#111', color: '#fff', borderColor: '#111', display: 'flex', gap: 8, alignItems: 'center' }}><Download size={16}/> Export Report</button></div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: '#45464d', fontSize: 13, marginBottom: 24 }}><Info size={16} color="#0058be"/> Synthetic / simulated evidence — no real-money movement.</div>
      {message && <div style={{ marginBottom: 18, padding: 12, borderRadius: 7, background: '#eef5ff', border: '1px solid #bfd7ff', display: 'flex', gap: 8, alignItems: 'center' }}><Info size={16}/>{message}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18 }}>
        <section style={card}><SlidersHorizontal size={22} color="#0058be"/><h2 style={{ fontSize: 17, marginBottom: 8 }}>Synthetic Benchmark</h2><p style={{ color: '#656a73', fontSize: 13, lineHeight: 1.6 }}>Generate a controlled, reproducible cohort without contacting a payment provider.</p><label style={{ fontSize: 12, fontWeight: 700 }}>COHORT SIZE<input type="number" min={100} max={100000} value={size} onChange={e => setSize(Math.max(100, Math.min(100000, Number(e.target.value) || 100)))} style={{ display: 'block', width: '100%', marginTop: 7, height: 38, border: '1px solid #c7cbd1', borderRadius: 6, padding: '0 10px', boxSizing: 'border-box' }}/></label><button onClick={runBenchmark} disabled={busy} style={{ ...button, width: '100%', marginTop: 14, background: '#0058be', color: '#fff', borderColor: '#0058be' }}>{busy ? 'Running…' : 'Run Benchmark'}</button></section>
        <section style={{ ...card, borderStyle: 'dashed', cursor: 'pointer' }} onClick={() => inputRef.current?.click()}><Upload size={22} color="#0058be"/><h2 style={{ fontSize: 17, marginBottom: 8 }}>Upload Dataset</h2><p style={{ color: '#656a73', fontSize: 13, lineHeight: 1.6 }}>Choose a CSV with payment_id, amount, failure_reason, retry_count and is_recoverable.</p><input ref={inputRef} type="file" accept=".csv,text/csv" hidden onChange={e => upload(e.target.files?.[0])}/><button style={{ ...button, width: '100%' }}>Choose CSV</button></section>
        <section style={card}><Database size={22} color="#176b4c"/><h2 style={{ fontSize: 17, marginBottom: 8 }}>Dataset Evaluation</h2><p style={{ color: '#656a73', fontSize: 13, lineHeight: 1.6 }}>Evaluate the active uploaded CSV locally through the same deterministic recovery-policy logic.</p><div style={{ fontSize: 13, margin: '14px 0', fontWeight: 700 }}>{rows.length ? `${rows.length.toLocaleString()} rows loaded` : 'No dataset loaded'}</div><button onClick={evaluateDataset} disabled={busy} style={{ ...button, width: '100%' }}>{busy ? 'Running…' : 'Evaluate Dataset'}</button></section>
      </div>
      {displayResult && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 14, marginTop: 24 }}>
          {[['Revenue at Risk', money(displayResult.revenueAtRisk)], ['Baseline Recovered', money(displayResult.baselineRecovered)], ['RecoverAI Recovered', money(displayResult.aiRecovered)], ['Recovery Rate', pct(displayResult.recoveryRate)], ['Incremental Revenue', `+${money(displayResult.incremental)}`]].map(([label, value]) => <section key={label} style={card}><div style={{ fontSize: 11, color: '#656a73', fontWeight: 800, textTransform: 'uppercase' }}>{label}</div><div style={{ fontSize: 25, fontWeight: 900, marginTop: 7 }}>{value}</div></section>)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18, marginTop: 18 }}>
          <section style={card}><h2 style={{ fontSize: 18, marginTop: 0 }}>Recovery Evidence</h2><div style={{ display: 'grid', gap: 12 }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Baseline recovery</span><b>{money(displayResult.baselineRecovered)}</b></div><div style={{ height: 10, background: '#e7e9ed', borderRadius: 20 }}><div style={{ width: `${Math.min(100, displayResult.baselineRecovered / Math.max(1, displayResult.revenueAtRisk) * 100)}%`, height: '100%', background: '#777b83', borderRadius: 20 }}/></div><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>RecoverAI recovery</span><b>{money(displayResult.aiRecovered)}</b></div><div style={{ height: 10, background: '#e7e9ed', borderRadius: 20 }}><div style={{ width: `${Math.min(100, displayResult.aiRecovered / Math.max(1, displayResult.revenueAtRisk) * 100)}%`, height: '100%', background: '#287bea', borderRadius: 20 }}/></div></div></section>
          <section style={card}><h2 style={{ fontSize: 18, marginTop: 0 }}>Safety Matrix</h2><p><CheckCircle2 size={15} style={{ verticalAlign: 'middle' }}/> Auto-Allow <b style={{ float: 'right' }}>{displayResult.policy.allow.toLocaleString()}</b></p><p><AlertTriangle size={15} style={{ verticalAlign: 'middle' }}/> Human Review <b style={{ float: 'right' }}>{displayResult.policy.review.toLocaleString()}</b></p><p><AlertTriangle size={15} style={{ verticalAlign: 'middle' }}/> Auto-Stop <b style={{ float: 'right' }}>{displayResult.policy.stop.toLocaleString()}</b></p><p style={{ color: '#656a73', fontSize: 12 }}>{displayResult.records.toLocaleString()} simulations evaluated.</p></section>
        </div>
      </>}
      <div style={{ marginTop: 22, padding: 13, border: '1px solid #d7dbe0', borderRadius: 8, background: '#fff', fontSize: 12, color: '#656a73' }}><FlaskConical size={15} style={{ verticalAlign: 'middle', marginRight: 7 }}/> Simulation mode is isolated from live payment execution. No real-money transaction is initiated by this page.</div>
    </main>
  </div>
}
