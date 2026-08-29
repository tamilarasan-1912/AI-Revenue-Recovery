import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || '/api';

type Payment = {
  payment_id: string;
  amount: number;
  status: string;
  payment_method?: string;
  failure_reason?: string;
  retry_count?: number;
  created_at?: string;
};

type PaymentsResponse = {
  summary?: {
    total_events?: number;
    failed_payments?: number;
    successful_payments?: number;
    pending_payments?: number;
    recovery_cases?: number;
  };
  payments?: Payment[];
};

const money = (v: unknown) => `₹${Number(v ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

function normalize(payload: unknown): Required<PaymentsResponse> {
  const p = (payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {}) as PaymentsResponse;
  const rows = Array.isArray(p.payments) ? p.payments.filter(x => x && typeof x === 'object') : [];
  const summary = p.summary && typeof p.summary === 'object' && !Array.isArray(p.summary) ? p.summary : {};
  return {
    payments: rows,
    summary: {
      total_events: Number(summary.total_events ?? rows.length ?? 0),
      failed_payments: Number(summary.failed_payments ?? rows.filter(x => x.status === 'failed').length),
      successful_payments: Number(summary.successful_payments ?? rows.filter(x => x.status === 'success').length),
      pending_payments: Number(summary.pending_payments ?? rows.filter(x => x.status === 'pending').length),
      recovery_cases: Number(summary.recovery_cases ?? 0),
    },
  };
}

async function loadPayments(): Promise<Required<PaymentsResponse>> {
  const response = await fetch(`${API}/payments/?limit=50`, { headers: { Accept: 'application/json' } });
  const raw = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error((raw as any)?.detail || (raw as any)?.message || `Request failed (${response.status})`);
  return normalize(raw);
}

export default function PaymentsSafe() {
  const [data, setData] = useState<Required<PaymentsResponse> | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError('');
    try { setData(await loadPayments()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to load payment data'); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  const summary = data?.summary ?? { total_events: 0, failed_payments: 0, successful_payments: 0, pending_payments: 0, recovery_cases: 0 };

  return (
    <div className="min-h-screen bg-[#f7f9fb] text-[#17191d]">
      <header className="flex h-16 items-center justify-between border-b border-[#d7dbe0] bg-white px-5 lg:px-8">
        <div><span className="text-xs font-bold uppercase tracking-widest text-[#777b83]">Revenue Recovery</span><span className="mx-2 text-[#b0b4bb]">/</span><span className="text-sm font-semibold">Payments</span></div>
        <button onClick={() => window.location.assign('/')} className="rounded border border-[#c8cbd1] bg-white px-3 py-2 text-xs font-bold">Back to dashboard</button>
      </header>
      <main className="mx-auto max-w-[1500px] p-5 lg:p-8">
        <div className="mb-7"><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">Dataset Payments</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight">Payments</h1><p className="mt-2 text-sm leading-6 text-[#656a73]">Payment-state visibility for the latest uploaded CSV dataset. No hard-coded payment records are used.</p></div>
        {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><b>Could not load payment data.</b><div className="mt-1">{error}</div><button onClick={() => void load()} className="mt-3 rounded bg-red-700 px-3 py-2 text-xs font-bold text-white">Retry</button></div>}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {[['Payment Events', summary.total_events], ['Failed', summary.failed_payments], ['Recovered / Success', summary.successful_payments], ['Pending', summary.pending_payments], ['Recovery Cases', summary.recovery_cases]].map(([label, value]) => <section key={String(label)} className="rounded-xl border border-[#d7dbe0] bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-widest text-[#656a73]">{label}</p><p className="mt-2 text-3xl font-extrabold">{String(value)}</p><p className="mt-1 text-xs text-[#737780]">Latest uploaded dataset</p></section>)}
        </div>
        <section className="mt-6 overflow-hidden rounded-xl border border-[#d7dbe0] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-[#d7dbe0] p-5"><h2 className="text-xl font-bold">Recent payments</h2><button disabled={loading} onClick={() => void load()} className="rounded border border-[#c8cbd1] px-3 py-2 text-sm font-semibold">{loading ? 'Loading…' : 'Refresh'}</button></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-[#f0f2f5] text-xs font-bold uppercase"><tr>{['Payment','Amount','Status','Method','Failure','Retries','Created'].map(x => <th key={x} className="px-4 py-3">{x}</th>)}</tr></thead><tbody>
            {!data?.payments?.length ? <tr><td colSpan={7} className="p-10 text-center text-[#666a72]">{loading ? 'Loading dataset records…' : 'No CSV payment records yet.'}</td></tr> : data.payments.map(p => <tr key={p.payment_id} className="border-t border-[#d9dbde]"><td className="break-all px-4 py-3 font-mono text-xs text-blue-700">{p.payment_id}</td><td className="px-4 py-3 font-mono">{money(p.amount)}</td><td className="px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs font-bold ${p.status === 'failed' ? 'bg-red-50 text-red-700' : p.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>{p.status || 'unknown'}</span></td><td className="px-4 py-3">{p.payment_method || '—'}</td><td className="max-w-[300px] px-4 py-3">{p.failure_reason || '—'}</td><td className="px-4 py-3">{p.retry_count ?? 0}</td><td className="whitespace-nowrap px-4 py-3">{p.created_at ? new Date(p.created_at).toLocaleString() : '—'}</td></tr>)}
          </tbody></table></div>
        </section>
      </main>
    </div>
  );
}
