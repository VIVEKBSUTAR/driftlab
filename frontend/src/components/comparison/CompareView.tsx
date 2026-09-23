import React, { useState, useEffect } from 'react';
import { Play, Filter, AlertOctagon, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';
import { RunRecord, DriftVerdict } from '../../types/api';
import { fetchRuns, compareRuns } from '../../services/api';
import { VerdictCard } from './VerdictCard';
import { Skeleton } from '../common/Skeleton';

export const CompareView: React.FC = () => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [baselineRunId, setBaselineRunId] = useState<string>('');
  const [candidateRunId, setCandidateRunId] = useState<string>('');
  const [noiseFloor, setNoiseFloor] = useState<number>(0.015);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(false);
  const [verdicts, setVerdicts] = useState<DriftVerdict[]>([]);

  useEffect(() => {
    const loadRuns = async () => {
      const data = await fetchRuns();
      setRuns(data);
      if (data.length >= 2) {
        const baseline = data.find((r) => r.run_type === 'baseline') || data[0];
        const candidate = data.find((r) => r.run_type === 'candidate' && r.id !== baseline.id) || data[1];
        setBaselineRunId(baseline.id);
        setCandidateRunId(candidate.id);
      } else if (data.length === 1) {
        setBaselineRunId(data[0].id);
        setCandidateRunId(data[0].id);
      }
    };
    loadRuns();
  }, []);

  // Run comparison
  const handleCompare = async () => {
    if (!baselineRunId || !candidateRunId) return;
    setLoading(true);
    try {
      const res = await compareRuns({
        baseline_run_id: baselineRunId,
        candidate_run_id: candidateRunId,
        noise_floor: noiseFloor,
      });
      setVerdicts(res.verdicts || []);
    } finally {
      setLoading(false);
    }
  };

  // Auto-trigger comparison once runs are loaded
  useEffect(() => {
    if (baselineRunId && candidateRunId && verdicts.length === 0) {
      handleCompare();
    }
  }, [baselineRunId, candidateRunId]);

  const categories = ['all', ...Array.from(new Set(verdicts.map((v) => v.category)))];
  const filteredVerdicts =
    categoryFilter === 'all' ? verdicts : verdicts.filter((v) => v.category === categoryFilter);

  // Verdict Summary counts
  const highRiskCount = verdicts.filter((v) => v.status === 'high_risk_regression').length;
  const driftCount = verdicts.filter((v) => v.status === 'meaningful_drift').length;
  const equivCount = verdicts.filter((v) => v.status === 'no_meaningful_drift').length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Controls */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-lg shadow-black/20">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Statistical Drift Analysis</h1>
            <p className="text-xs text-slate-400 mt-1">
              Compare candidate LLM state against baseline using prompt clustering, BCa bootstrap CI, and practical equivalence margins.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleCompare}
              disabled={loading || !baselineRunId || !candidateRunId}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg shadow-md shadow-brand-500/20 disabled:opacity-50 transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Calculating...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Execute Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Run Selectors & Sliders */}
        <div className="mt-5 pt-5 border-t border-surface-border grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Baseline selector */}
          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 mb-1.5 uppercase">
              1. Baseline Run (Control)
            </label>
            <select
              value={baselineRunId}
              onChange={(e) => setBaselineRunId(e.target.value)}
              className="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 font-mono"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  [{r.run_type.toUpperCase()}] {r.id} — {r.model_identifier || 'Unknown Model'}
                </option>
              ))}
            </select>
          </div>

          {/* Candidate selector */}
          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 mb-1.5 uppercase">
              2. Candidate Run (Treatment)
            </label>
            <select
              value={candidateRunId}
              onChange={(e) => setCandidateRunId(e.target.value)}
              className="w-full bg-surface-base border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 font-mono"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  [{r.run_type.toUpperCase()}] {r.id} — {r.model_identifier || 'Unknown Model'}
                </option>
              ))}
            </select>
          </div>

          {/* Noise floor slider */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-mono font-medium text-slate-400 uppercase">
                Noise Floor Filter: <span className="text-brand-400 font-bold font-mono">±{noiseFloor.toFixed(3)}</span>
              </label>
            </div>
            <input
              type="range"
              min="0.000"
              max="0.050"
              step="0.005"
              value={noiseFloor}
              onChange={(e) => setNoiseFloor(parseFloat(e.target.value))}
              className="w-full h-2 bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-brand-500"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
              <span>0.000 (Sensitive)</span>
              <span>0.025</span>
              <span>0.050 (Permissive)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Scoreboard Bar */}
      {verdicts.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-surface-card border border-rose-500/20 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase">High Risk Regressions</span>
              <div className="text-2xl font-bold font-mono text-rose-400">{highRiskCount}</div>
            </div>
          </div>

          <div className="bg-surface-card border border-amber-500/20 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase">Meaningful Drift Detected</span>
              <div className="text-2xl font-bold font-mono text-amber-400">{driftCount}</div>
            </div>
          </div>

          <div className="bg-surface-card border border-emerald-500/20 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase">No Meaningful Drift (Equivalence)</span>
              <div className="text-2xl font-bold font-mono text-emerald-400">{equivCount}</div>
            </div>
          </div>
        </div>
      )}

      {/* Category Filter Pills */}
      {categories.length > 2 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-xs font-mono text-slate-400 uppercase mr-1">Filter Category:</span>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1 rounded-full text-xs font-mono transition-colors ${
                categoryFilter === cat
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/40 font-semibold'
                  : 'bg-surface-card text-slate-400 border border-surface-border hover:text-slate-200'
              }`}
            >
              {cat.toUpperCase()}
            </button>
          ))}
        </div>
      )}

      {/* Verdict Cards List */}
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
        </div>
      ) : filteredVerdicts.length > 0 ? (
        <div className="space-y-4">
          {filteredVerdicts.map((v, i) => (
            <VerdictCard key={`${v.category}-${v.metric_id}-${i}`} verdict={v} />
          ))}
        </div>
      ) : (
        <div className="bg-surface-card border border-surface-border rounded-xl p-12 text-center">
          <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No Comparison Results Yet</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            Select a baseline and candidate run above and click "Execute Analysis" to evaluate behavioral drift.
          </p>
        </div>
      )}
    </div>
  );
};
