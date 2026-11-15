import { useEffect, useState } from 'react';
import { RunRecord, RunDetail } from '../../types/api';
import { fetchRuns, fetchRunDetail } from '../../services/api';

const colors = ['#c0b0f5', '#8faed4', '#9bc8b2', '#cfba94'];
const number = (n: number) => n.toLocaleString();

export function BenchmarkMetrics() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const records = await fetchRuns();
      setRuns(records);
      setSelected(current => records.some(r => r.id === current && r.status === 'completed') ? current : records.find(r => r.status === 'completed')?.id ?? '');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load metrics.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    let active = true;
    setDetail(null); setDetailError('');
    if (!selected) return;
    setDetailLoading(true);
    fetchRunDetail(selected).then(data => { if (active) setDetail(data); })
      .catch(e => { if (active) setDetailError(e.message); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selected, runs]);

  const completed = runs.filter(r => r.status === 'completed');
  const statuses = ['completed', 'running', 'pending', 'failed'];
  const timeline = [...runs].filter(r => r.created_at).sort((a, b) => Date.parse(a.created_at!) - Date.parse(b.created_at!)).slice(-12);
  const maximum = Math.max(1, ...timeline.map(r => r.observations_count));
  const metrics = [...new Set(detail?.aggregates.map(a => a.metric_name) ?? [])];
  const latencies = (detail?.observations ?? []).filter(o => !o.error && Number.isFinite(o.latency_ms)).map(o => o.latency_ms).sort((a, b) => a - b);
  const meanLatency = latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : null;
  const p95 = latencies.length ? latencies[Math.ceil(latencies.length * .95) - 1] : null;

  return <div className="benchmark-metrics space-y-6 mb-6" aria-busy={loading}>
    {error && <p role="alert" className="p-4 rounded-lg border border-status-red/30 text-status-red">{error} Metrics may be out of date.</p>}
    {!loading && !error && !runs.length && <div className="p-8 rounded-lg border border-dashed border-[var(--border)] text-center text-text-secondary">No benchmark data yet. Create a baseline and candidate to populate these charts.</div>}
    <div className="grid lg:grid-cols-3 gap-4">
      <Panel title="Observation volume" note="Last 12 runs, oldest to newest · observations per run" className="lg:col-span-2">
        {timeline.length ? <><svg viewBox="0 0 640 220" role="img" aria-label="Observation count by benchmark run" className="w-full">
          {[0, .5, 1].map(t => <g key={t}><line x1="45" x2="625" y1={180 - t * 150} y2={180 - t * 150} stroke="#30363d" strokeDasharray="3 4" /><text x="35" y={184 - t * 150} fill="#8b949e" fontSize="11" textAnchor="end">{Math.round(maximum * t)}</text></g>)}
          {timeline.map((r, i) => { const width = 570 / timeline.length; const height = r.observations_count / maximum * 150;
            return <g key={r.id}><title>{r.id}: {r.observations_count} observations · {r.run_type} · {r.status}</title><rect x={50 + i * width} y={180 - height} width={Math.max(4, width - 12)} height={height} rx="4" fill={r.run_type === 'baseline' ? colors[0] : colors[1]} /><text x={50 + i * width + (width - 12) / 2} y="202" textAnchor="middle" fill="#8b949e" fontSize="10">{i + 1}</text></g>;
          })}
        </svg><div className="flex gap-5 text-xs text-text-secondary"><span><i className="inline-block w-2 h-2 bg-[#c0b0f5] rounded-sm mr-2" />Baseline</span><span><i className="inline-block w-2 h-2 bg-[#8faed4] rounded-sm mr-2" />Candidate</span></div>
          <details className="text-xs text-text-secondary mt-3"><summary className="cursor-pointer">View chart data</summary><div className="overflow-x-auto"><table className="w-full mt-2 text-left"><thead><tr><th>Run</th><th>Date</th><th>Observations</th></tr></thead><tbody>{timeline.map((r, i) => <tr key={r.id}><td className="py-1">{i + 1}. {r.id}</td><td>{new Date(r.created_at!).toLocaleDateString()}</td><td>{number(r.observations_count)}</td></tr>)}</tbody></table></div></details></> : <Empty loading={loading} />}
      </Panel>
      <Panel title="Execution health" note="All recorded runs by current status">
        <div className="space-y-5 mt-4">{statuses.map((status, i) => { const count = runs.filter(r => r.status === status).length; return <div key={status}>
          <div className="flex justify-between text-xs mb-2"><span className="capitalize text-text-secondary">{status}</span><span className="font-mono">{loading ? '—' : count}</span></div>
          <div className="h-2 rounded-full bg-bg-elevated overflow-hidden"><div style={{ width: `${runs.length ? count / runs.length * 100 : 0}%`, background: [colors[2], colors[0], colors[3], '#f87171'][i] }} className="h-full rounded-full" /></div>
        </div>; })}</div>
      </Panel>
    </div>
    <Panel title="Run quality & performance" note="Mean of prompt-level means; metrics remain separate because their scales differ.">
      <label className="block text-xs text-text-secondary mt-3 mb-4">Completed run
        <select value={selected} onChange={e => setSelected(e.target.value)} className="block mt-2 w-full bg-bg-page border border-[var(--border)] rounded-lg p-2 text-text-primary">
          {!completed.length && <option value="">No completed runs</option>}
          {completed.map(r => <option key={r.id} value={r.id}>{r.model_identifier} · {r.id}{r.synthetic ? ' · Synthetic' : ''}</option>)}
        </select>
      </label>
      {detailError && <p role="alert" className="text-status-red text-sm">{detailError}</p>}
      {detail?.synthetic && <p className="text-xs text-status-amber mb-4">Synthetic benchmark: validates pipeline behavior; does not establish model quality.</p>}
      {detailLoading ? <Empty loading /> : metrics.length ? <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-5">{metrics.map((metric, i) => {
          const values = detail!.aggregates.filter(a => a.metric_name === metric);
          const mean = values.reduce((s, a) => s + a.mean_value, 0) / values.length;
          const min = metric === 'embedding_similarity' ? -1 : 0;
          const start = min === -1 ? 50 : 0;
          const end = (mean - min) / (1 - min) * 100;
          return <div key={metric}><div className="flex justify-between text-xs mb-2"><span className="text-text-secondary">{metric.replace(/_/g, ' ')}</span><strong className="font-mono">{mean.toFixed(4)}</strong></div>
            <div role="img" aria-label={`${metric}: ${mean.toFixed(4)}, scale ${min} to 1, ${values.length} prompts`} className="h-3 relative rounded bg-bg-elevated"><div className="absolute h-full rounded" style={{ left: `${Math.min(start, end)}%`, width: `${Math.abs(end - start)}%`, background: colors[i % colors.length] }} /><div className="absolute inset-y-0 border-l border-text-muted" style={{ left: `${start}%` }} /></div>
            <div className="flex justify-between text-2xs text-[#959dab] mt-1"><span>{min}</span><span>{values.length} prompts</span><span>1</span></div></div>;
        })}</div>
        <div className="grid grid-cols-2 gap-3 content-start"><Stat label="Mean latency" value={meanLatency === null ? '—' : `${meanLatency.toFixed(0)} ms`} note="Successful generations" /><Stat label="P95 latency" value={p95 === null ? '—' : `${p95.toFixed(0)} ms`} note="Nearest-rank 95th percentile" /></div>
      </div> : !detailError && <Empty loading={false} />}
    </Panel>
  </div>;
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="p-5 rounded-lg bg-[var(--surface)] border border-[var(--border)]"><p className="text-xs text-text-secondary">{label}</p><p className="text-2xl font-semibold font-mono tracking-tight mt-2">{value}</p><p className="text-xs text-[#959dab] mt-2">{note}</p></div>;
}
function Panel({ title, note, children, className = '' }: { title: string; note: string; children: React.ReactNode; className?: string }) {
  return <section className={`p-5 rounded-lg bg-[var(--surface)] border border-[var(--border)] min-w-0 ${className}`}><h2 className="text-sm font-semibold">{title}</h2><p className="text-xs text-[#959dab] mt-1 mb-3 break-words">{note}</p>{children}</section>;
}
function Empty({ loading }: { loading: boolean }) { return <p className="text-sm text-[#959dab] py-12 text-center">{loading ? 'Loading metrics…' : 'No observations available.'}</p>; }
