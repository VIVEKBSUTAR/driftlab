import React, { useState, useEffect } from 'react';
import { Play, ChevronDown, Info } from 'lucide-react';
import { RunRecord, DriftVerdict } from '../../types/api';
import { fetchRuns, compareRuns } from '../../services/api';
import { StatusBadge } from '../common/StatusBadge';

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmt(v: number, digits = 3) {
  return v > 0 ? `+${v.toFixed(digits)}` : v.toFixed(digits);
}

function CategoryLabel({ value }: { value: string }) {
  return (
    <span className="text-xs text-text-secondary font-medium capitalize">
      {value.replace(/_/g, ' ')}
    </span>
  );
}

// ─── Interval chart (forest plot row) ────────────────────────────────────────

function IntervalBar({ verdict, extent }: { verdict: DriftVerdict; extent: number }) {
  const position = (value: number) => 50 + value / extent * 50;
  const color = verdict.status === 'high_risk_regression' ? '#f87171' : verdict.status === 'no_meaningful_drift' ? '#34d399' : '#fbbf24';
  return <div role="img" aria-label={`Effect ${verdict.estimate.toFixed(4)}, confidence interval ${verdict.ci_low.toFixed(4)} to ${verdict.ci_high.toFixed(4)}, tolerance plus or minus ${verdict.margin}`} className="relative h-9 w-full">
    <div className="absolute inset-y-0 rounded bg-status-greenDim border border-status-green/20" style={{left: `${position(-verdict.margin)}%`, width: `${verdict.margin / extent * 100}%`}} />
    <div className="absolute inset-y-1 bg-bg-elevated/60" style={{left: `${position(-verdict.noise_floor)}%`, width: `${verdict.noise_floor / extent * 100}%`}} />
    <div className="absolute inset-y-0 border-l border-text-muted" style={{left: '50%'}} />
    <div className="absolute top-1/2 h-0.5" style={{left: `${position(verdict.ci_low)}%`, width: `${(verdict.ci_high - verdict.ci_low) / extent * 50}%`, background: color}} />
    {[verdict.ci_low, verdict.ci_high].map((value, i) => <div key={i} className="absolute top-1/2 -translate-y-1/2 h-3 border-l-2" style={{left: `${position(value)}%`, borderColor: color}} />)}
    <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full border-2 border-bg-page" style={{left: `${position(verdict.estimate)}%`, background: color}} />
  </div>;
}

// ─── Verdict row ─────────────────────────────────────────────────────────────

function VerdictRow({ verdict, extent }: { verdict: DriftVerdict; extent: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="verdict-row border-b border-border-muted last:border-0">
      {/* Main row */}
      <div className="px-5 py-4">
        <div className="flex items-center justify-between gap-4 mb-3">
          <div>
            <CategoryLabel value={verdict.category} />
            <span className="text-text-muted mx-2">·</span>
            <span className="text-xs font-mono text-text-muted">{verdict.metric_id}</span>
          </div>
          <StatusBadge status={verdict.status} />
        </div>

        {/* Interval bar */}
        <div className="mb-2">
          <IntervalBar verdict={verdict} extent={extent} />
        </div>

        {/* Axis labels */}
        <div className="flex justify-between text-2xs text-text-muted font-mono">
          <span>−{extent.toFixed(3)}</span>
          <span className="text-text-muted">0  (no change)</span>
          <span>+{extent.toFixed(3)}</span>
        </div>

        {/* Explanation + toggle */}
        <div className="flex items-start justify-between gap-2 mt-3">
          <p className="text-xs text-text-secondary leading-relaxed flex-1">
            {verdict.explanation}
          </p>
          <button
            onClick={() => setOpen(!open)}
            className="shrink-0 flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors mt-0.5"
          >
            <span>Stats</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* Expanded stats */}
      {open && (
        <div className="px-5 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MiniStat label="Effect (Δ)"       value={fmt(verdict.estimate)} />
          <MiniStat label="Confidence interval"            value={`[${verdict.ci_low.toFixed(3)}, ${verdict.ci_high.toFixed(3)}]`} mono />
          <MiniStat label="Holm-adjusted p"           value={verdict.p_adjusted.toFixed(4)} />
          <MiniStat label="Noise floor (σ₀)"  value={verdict.noise_floor.toFixed(4)} />
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-bg-page rounded border border-border-base px-3 py-2">
      <p className="text-2xs text-text-muted uppercase tracking-wide mb-0.5">{label}</p>
      <p className={`text-sm font-semibold text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</p>
    </div>
  );
}

// ─── Main CompareView ─────────────────────────────────────────────────────────

export const CompareView: React.FC = () => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [baselineId, setBaselineId] = useState('');
  const [candidateId, setCandidateId] = useState('');
  const [noiseFloor, setNoiseFloor] = useState(0.012);
  const [manualNoise, setManualNoise] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState('');
  const [synthetic, setSynthetic] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verdicts, setVerdicts] = useState<DriftVerdict[]>([]);
  const [hasRun, setHasRun] = useState(false);

  useEffect(() => {
    fetchRuns().then((data) => {
      setRuns(data);
      setBaselineId(data.find(r => r.run_type === 'baseline' && r.status === 'completed')?.id ?? '');
      setCandidateId(data.find(r => r.run_type === 'candidate' && r.status === 'completed')?.id ?? '');
    }).catch(e => setError(e.message));
  }, []);

  useEffect(() => { setVerdicts([]); setHasRun(false); setSource(''); }, [baselineId, candidateId, noiseFloor, manualNoise]);

  const runCompare = async () => {
    if (!baselineId || !candidateId) return;
    setLoading(true);
    setError('');
    setVerdicts([]);
    setHasRun(false);
    try {
      const res = await compareRuns({
        baseline_run_id: baselineId,
        candidate_run_id: candidateId,
        ...(manualNoise ? { noise_floor: noiseFloor } : {}),
      });
      setVerdicts(res.verdicts ?? []);
      setHasRun(true);
      setSource(`${res.baseline_run_id} → ${res.candidate_run_id}`);
      setSynthetic(Boolean(res.baseline?.synthetic || res.candidate?.synthetic));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const baseline = runs.find((r) => r.id === baselineId);
  const candidate = runs.find((r) => r.id === candidateId);

  const extent = Math.max(.01, ...verdicts.flatMap(v => [Math.abs(v.ci_low), Math.abs(v.ci_high), Math.abs(v.estimate), v.margin, v.noise_floor])) * 1.15;
  const summary = {
    pass: verdicts.filter((v) => v.status === 'no_meaningful_drift').length,
    warn: verdicts.filter((v) => v.status === 'meaningful_drift').length,
    fail: verdicts.filter((v) => v.status === 'high_risk_regression').length,
    unknown: verdicts.filter((v) => ['insufficient_data', 'insufficient_evidence'].includes(v.status)).length,
  };

  return (
    <div className="space-y-8">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text-primary tracking-tight mb-1">
          Model Comparison
        </h1>
        <p className="text-sm text-text-secondary">
          Select two runs to compare their behavior across all evaluated task categories.
        </p>
      </div>

      {error && <p role="alert" className="p-4 rounded-lg border border-status-red/30 text-status-red">{error}</p>}
      {/* Configuration panel */}
      <div className="bg-bg-card border border-border-base rounded-lg p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Comparison Setup</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">

          <SelectField
            label="Baseline (original model)"
            value={baselineId}
            onChange={value => { if (!loading) setBaselineId(value); }}
            options={runs.filter(r => r.run_type === 'baseline' && r.status === 'completed')}
          />
          <SelectField
            label="Candidate (modified model)"
            value={candidateId}
            onChange={value => { if (!loading) setCandidateId(value); }}
            options={runs.filter(r => r.run_type === 'candidate' && r.status === 'completed')}
          />

          <div className="flex flex-col gap-1">
            <label className="text-xs text-text-secondary mb-2"><input type="checkbox" checked={manualNoise} disabled={loading} onChange={e => setManualNoise(e.target.checked)} className="mr-2" />Override estimated noise</label>
            <label className="text-xs font-medium text-text-secondary">
              Manual noise floor — <span className="font-mono">σ₀ = {noiseFloor.toFixed(3)}</span>
            </label>
            <input
              disabled={!manualNoise || loading}
              type="range" min="0" max="0.04" step="0.002"
              value={noiseFloor}
              onChange={(e) => setNoiseFloor(parseFloat(e.target.value))}
              className="mt-2 w-full accent-accent cursor-pointer"
            />
            <p className="text-xs text-text-muted">
              Default: estimate noise from baseline repeats.
            </p>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-4">
          <button
            onClick={runCompare}
            disabled={loading || !baselineId || !candidateId || baselineId === candidateId}
            className="inline-flex items-center gap-2 px-4 py-2 rounded bg-accent hover:bg-accent-light text-text-inverse text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {loading ? 'Running analysis…' : 'Run Comparison'}
          </button>
          {baseline && candidate && (
            <p className="text-xs text-text-muted">
              <span className="font-medium text-text-secondary">{baseline.model_identifier}</span>
              {' vs '}
              <span className="font-medium text-text-secondary">{candidate.model_identifier}</span>
            </p>
          )}
        </div>
      </div>

      {/* Summary row */}
      {verdicts.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <SummaryCard label="Equivalent" count={summary.pass} color="text-status-green" />
          <SummaryCard label="Meaningful drift"    count={summary.warn} color="text-status-amber" />
          <SummaryCard label="Regression" count={summary.fail} color="text-status-red" />
          <SummaryCard label="Unclear"    count={summary.unknown} color="text-text-secondary" />
        </div>
      )}

      {hasRun && <p className="text-xs text-text-secondary break-words">{source}{synthetic ? ' · Synthetic evidence: pipeline validation only.' : ''} · Positive Δ means higher candidate score. Confidence levels follow each risk tier (95%, 99%, or 99.5%).</p>}
      {verdicts.some(v => v.status === 'statistically_detected_low_impact') && <p className="text-xs text-text-secondary">Low-impact statistical differences: {verdicts.filter(v => v.status === 'statistically_detected_low_impact').length}. These are separate from meaningful drift.</p>}
      {/* Verdicts */}
      {verdicts.length > 0 && (
        <div className="bg-bg-card border border-border-base rounded-lg overflow-hidden">
          <div className="px-5 py-3 border-b border-border-base flex items-center gap-2">
            <h2 className="text-sm font-semibold text-text-primary">Results by Category</h2>
            <span className="text-xs text-text-muted">({verdicts.length} metrics evaluated)</span>
            <div className="ml-auto flex items-center gap-1 text-xs text-text-muted">
              <Info className="w-3.5 h-3.5" />
              <span>Shared score-delta scale · green: tolerance · gray: noise</span>
            </div>
          </div>
          <div>
            {verdicts.map((v, i) => (
              <VerdictRow key={i} verdict={v} extent={extent} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !hasRun && runs.length === 0 && (
        <div className="text-center py-16 text-text-secondary">
          <p className="text-sm">No runs recorded yet.</p>
          <p className="text-xs text-text-muted mt-1">
            Use <span className="font-mono">driftlab run</span> to record your first benchmark.
          </p>
        </div>
      )}
    </div>
  );
};

// ─── SelectField ─────────────────────────────────────────────────────────────

function SelectField({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: RunRecord[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-text-secondary">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none bg-bg-page border border-border-base rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-focus pr-8"
        >
          <option value="">Select a completed run</option>
          {options.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id} — {r.model_identifier}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
      </div>
    </div>
  );
}

function SummaryCard({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="bg-bg-card border border-border-base rounded-lg px-4 py-3 flex items-center justify-between">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className={`text-xl font-semibold ${color}`}>{count}</span>
    </div>
  );
}
