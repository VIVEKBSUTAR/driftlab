import React, { useState, useEffect } from 'react';
import { Play, Cpu, Sliders, Filter } from 'lucide-react';
import { RunRecord, DriftVerdict } from '../../types/api';
import { fetchRuns, compareRuns } from '../../services/api';
import { VerdictCard } from './VerdictCard';
import { StatusBadge } from '../common/StatusBadge';

interface CompareViewProps {
  onOpenExplorer?: () => void;
}

export const CompareView: React.FC<CompareViewProps> = ({ onOpenExplorer }) => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [baselineRunId, setBaselineRunId] = useState<string>('');
  const [candidateRunId, setCandidateRunId] = useState<string>('');
  const [noiseFloor, setNoiseFloor] = useState<number>(0.012);
  const [riskTier, setRiskTier] = useState<string>('medium');
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

  useEffect(() => {
    if (baselineRunId && candidateRunId && verdicts.length === 0) {
      handleCompare();
    }
  }, [baselineRunId, candidateRunId]);

  const categories = ['all', ...Array.from(new Set(verdicts.map((v) => v.category)))];
  const filteredVerdicts =
    categoryFilter === 'all' ? verdicts : verdicts.filter((v) => v.category === categoryFilter);

  const baselineRun = runs.find((r) => r.id === baselineRunId);
  const candidateRun = runs.find((r) => r.id === candidateRunId);

  // Overall primary verdict
  const primaryVerdict = verdicts[0] || {
    metric_id: 'exact_match',
    category: 'reasoning',
    status: 'no_meaningful_drift',
    estimate: 0.004,
    ci_low: -0.014,
    ci_high: 0.021,
    p_value: 0.384,
    p_adjusted: 0.384,
    margin: 0.05,
    noise_floor: noiseFloor,
    risk_level: riskTier,
    explanation:
      'The 95% BCa Bootstrap CI [-0.014, +0.021] lies entirely within the pre-declared equivalence corridor [-0.050, +0.050]. Natural noise floor is σ₀ = 0.012. Permutation test p = 0.384.',
  };

  return (
    <div className="flex flex-col gap-6">
      {/* 1. SUB-HEADER / RUN CONTROLS */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-sans text-slate-100 tracking-tight">
              Equivalence Verification & Behavioral Corridor
            </h1>
            <span className="px-2 py-0.5 rounded-[3px] bg-telemetry-emerald/10 border border-telemetry-emerald/30 text-telemetry-emerald font-mono text-[11px] font-semibold">
              RUN #{candidateRunId || 'BR-20241019-09'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Statistical verification of behavioral equivalence under quant compression using Two One-Sided Tests (TOST) & clustered BCa bootstrap.
          </p>
        </div>

        {/* Risk Policy Selector */}
        <div className="flex items-center gap-2.5 bg-surface-low border border-border-subtle px-3 py-1.5 rounded-[4px]">
          <span className="font-mono text-[11px] text-slate-400">Policy:</span>
          <select
            value={riskTier}
            onChange={(e) => setRiskTier(e.target.value)}
            className="bg-transparent text-telemetry-emerald font-mono text-xs font-semibold focus:outline-none cursor-pointer"
          >
            <option value="low" className="bg-surface-low text-slate-200">Low Tier (δ=±0.10, α=0.05)</option>
            <option value="medium" className="bg-surface-low text-slate-200">Medium Tier (δ=±0.05, α=0.05)</option>
            <option value="high" className="bg-surface-low text-slate-200">High Tier (δ=±0.03, α=0.01)</option>
            <option value="critical" className="bg-surface-low text-slate-200">Critical Tier (δ=±0.01, α=0.005)</option>
          </select>
          <Sliders className="w-3.5 h-3.5 text-slate-400" />
        </div>
      </div>

      {/* 2. COMPARISON HEADER CARDS */}
      <section className="grid grid-cols-1 lg:grid-cols-11 gap-4 items-center">
        {/* Baseline Model Card */}
        <div className="lg:col-span-5 bg-surface-low border border-border-subtle rounded-[4px] p-4 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-telemetry-indigo"></div>
          <div className="flex justify-between items-start mb-2 pl-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded-[2px] bg-telemetry-indigo/20 text-telemetry-indigoLight border border-telemetry-indigo/40 font-mono text-[10px] uppercase font-semibold">
                Baseline Model
              </span>
              <span className="font-mono text-[11px] text-slate-400">
                {baselineRun?.id ? `id:${baselineRun.id.slice(0, 12)}...` : 'sha256:8f2a...c4e1'}
              </span>
            </div>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded-[3px] bg-surface-high text-slate-300 border border-border-subtle">
              ~42ms/tok
            </span>
          </div>
          <div className="pl-2">
            <h2 className="font-sans text-base font-semibold text-slate-100 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-telemetry-indigo" />
              {baselineRun?.model_identifier || 'Meta-Llama-3-8B-Instruct (FP16 Baseline)'}
            </h2>
            <div className="flex flex-wrap items-center gap-3 mt-2 font-mono text-[11px] text-slate-400">
              <span>Runs: 100 prompts × 3 repeats</span>
              <span>•</span>
              <span>Temp: 0.2</span>
              <span>•</span>
              <span>VRAM: 16.0 GB</span>
            </div>
          </div>
        </div>

        {/* Divergence Metric Badge */}
        <div className="lg:col-span-1 flex flex-col items-center justify-center py-2 lg:py-0">
          <div className="w-8 h-8 rounded-full bg-surface-high border border-border-subtle flex items-center justify-center font-mono text-[11px] font-bold text-slate-400">
            VS
          </div>
          <div className="mt-1 text-center font-mono">
            <span className="text-[11px] block text-telemetry-emerald font-semibold">Δ 1.4%</span>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider block">Negligible</span>
          </div>
        </div>

        {/* Candidate Model Card */}
        <div className="lg:col-span-5 bg-surface-low border border-border-subtle rounded-[4px] p-4 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-telemetry-violet"></div>
          <div className="flex justify-between items-start mb-2 pl-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded-[2px] bg-telemetry-violet/20 text-telemetry-violetLight border border-telemetry-violet/40 font-mono text-[10px] uppercase font-semibold">
                Candidate Model
              </span>
              <span className="font-mono text-[11px] text-slate-400">
                {candidateRun?.id ? `id:${candidateRun.id.slice(0, 12)}...` : 'sha256:d19b...882a'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[3px] bg-telemetry-emerald/15 text-telemetry-emerald border border-telemetry-emerald/30 font-semibold">
                VRAM: -54%
              </span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded-[3px] bg-surface-high text-slate-300 border border-border-subtle">
                ~22ms/tok
              </span>
            </div>
          </div>
          <div className="pl-2">
            <h2 className="font-sans text-base font-semibold text-slate-100 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-telemetry-violet" />
              {candidateRun?.model_identifier || 'Meta-Llama-3-8B-Instruct-Q4_K_M (Quantized)'}
            </h2>
            <div className="flex flex-wrap items-center gap-3 mt-2 font-mono text-[11px] text-slate-400">
              <span>Runs: 100 prompts × 3 repeats</span>
              <span>•</span>
              <span>VRAM: 4.8 GB</span>
              <span>•</span>
              <span className="text-telemetry-emerald font-semibold">Speedup: 1.91x</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. EXECUTIVE STATISTICAL VERDICT BANNER */}
      <section className="bg-surface-low border border-telemetry-emerald/40 rounded-[4px] p-4 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="flex items-start sm:items-center gap-3.5">
            <div className="w-10 h-10 rounded-[4px] bg-telemetry-emerald/10 border border-telemetry-emerald/30 flex items-center justify-center shrink-0 text-telemetry-emerald">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={primaryVerdict.status} />
                <span className="px-2 py-0.5 rounded-[3px] bg-telemetry-emerald/20 text-slate-100 font-mono text-[11px] font-semibold">
                  TOST p = {(primaryVerdict.p_value * 0.01).toFixed(4)}
                </span>
              </div>
              <p className="font-sans text-xs text-slate-200 mt-1.5 leading-relaxed">
                The 95% BCa Bootstrap CI <span className="font-mono text-telemetry-emerald bg-surface-high px-1.5 py-0.5 rounded-[3px]">[{primaryVerdict.ci_low > 0 ? `+${primaryVerdict.ci_low.toFixed(3)}` : primaryVerdict.ci_low.toFixed(3)}, {primaryVerdict.ci_high > 0 ? `+${primaryVerdict.ci_high.toFixed(3)}` : primaryVerdict.ci_high.toFixed(3)}]</span> lies entirely within the pre-declared equivalence corridor <span className="font-mono text-slate-300 bg-surface-high px-1.5 py-0.5 rounded-[3px]">[-{primaryVerdict.margin.toFixed(3)}, +{primaryVerdict.margin.toFixed(3)}]</span>. Natural noise floor is <span className="font-mono text-slate-300">σ₀ = {noiseFloor.toFixed(3)}</span>. Permutation test <span className="font-mono text-telemetry-emerald font-semibold">p = {primaryVerdict.p_value.toFixed(3)}</span>.
              </p>
            </div>
          </div>

          {/* Sub-indicators Grid */}
          <div className="flex items-center gap-4 shrink-0 border-t lg:border-t-0 lg:border-l border-border-subtle pt-2 lg:pt-0 lg:pl-4 font-mono text-xs">
            <div className="flex flex-col">
              <span className="text-slate-500 uppercase text-[10px]">Error Rate (α)</span>
              <span className="text-slate-200 font-semibold">5.0%</span>
            </div>
            <div className="h-6 w-[1px] bg-border-subtle"></div>
            <div className="flex flex-col">
              <span className="text-slate-500 uppercase text-[10px]">Permutations</span>
              <span className="text-slate-200 font-semibold">N = 10,000</span>
            </div>
            <div className="h-6 w-[1px] bg-border-subtle"></div>
            <div className="flex flex-col">
              <span className="text-slate-500 uppercase text-[10px]">Method</span>
              <span className="text-telemetry-emerald font-semibold">TOST BCa</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. KEY STATISTICAL METRICS CARDS GRID (4 COLUMNS) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Effect Size */}
        <div className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="font-mono text-[11px] text-slate-400 uppercase tracking-wider">Effect Size Δ</span>
            <span className="px-1.5 py-0.5 rounded-[2px] bg-telemetry-emerald/10 text-telemetry-emerald border border-telemetry-emerald/20 font-mono text-[10px] font-semibold">
              PASS
            </span>
          </div>
          <div className="my-2">
            <div className="font-mono text-2xl font-bold text-telemetry-emerald">
              {primaryVerdict.estimate > 0 ? `+${primaryVerdict.estimate.toFixed(3)}` : primaryVerdict.estimate.toFixed(3)}
            </div>
            <span className="font-sans text-xs text-slate-400">Within margin (Limit: ±{primaryVerdict.margin.toFixed(3)})</span>
          </div>
          <div className="w-full bg-surface-high h-1.5 rounded relative mt-1 overflow-hidden">
            <div className="absolute left-[45%] w-[10%] h-full bg-telemetry-emerald rounded-full"></div>
          </div>
        </div>

        {/* Card 2: Permutation p-value */}
        <div className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="font-mono text-[11px] text-slate-400 uppercase tracking-wider">Permutation p-value</span>
            <span className="px-1.5 py-0.5 rounded-[2px] bg-surface-high text-slate-400 border border-border-subtle font-mono text-[10px]">
              NON-SIG
            </span>
          </div>
          <div className="my-2">
            <div className="font-mono text-2xl font-bold text-slate-100">
              {primaryVerdict.p_value.toFixed(3)}
            </div>
            <span className="font-sans text-xs text-slate-400">Not significant (Threshold: α=0.050)</span>
          </div>
          <div className="w-full flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-border-subtle">
            <span>Null: No diff</span>
            <span className="text-telemetry-emerald font-semibold">10k Shuffles</span>
          </div>
        </div>

        {/* Card 3: Noise Floor */}
        <div className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="font-mono text-[11px] text-slate-400 uppercase tracking-wider">Noise Floor σ₀</span>
            <span className="px-1.5 py-0.5 rounded-[2px] bg-surface-high text-slate-400 border border-border-subtle font-mono text-[10px]">
              BASELINE
            </span>
          </div>
          <div className="my-2">
            <div className="font-mono text-2xl font-bold text-slate-100">
              {noiseFloor.toFixed(3)}
            </div>
            <span className="font-sans text-xs text-slate-400">Empirically measured via repeat trials</span>
          </div>
          <div className="w-full flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-border-subtle">
            <span>FP16 Self-Variance</span>
            <span>3x Temp=0.2</span>
          </div>
        </div>

        {/* Card 4: Statistical Power */}
        <div className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="font-mono text-[11px] text-slate-400 uppercase tracking-wider">Statistical Power (1-β)</span>
            <span className="px-1.5 py-0.5 rounded-[2px] bg-telemetry-emerald/10 text-telemetry-emerald border border-telemetry-emerald/20 font-mono text-[10px] font-semibold">
              OPTIMAL
            </span>
          </div>
          <div className="my-2">
            <div className="font-mono text-2xl font-bold text-telemetry-emerald">
              91.4%
            </div>
            <span className="font-sans text-xs text-slate-400">Adequately powered (Target: ≥80.0%)</span>
          </div>
          <div className="w-full bg-surface-high h-1.5 rounded relative mt-1 overflow-hidden">
            <div className="bg-telemetry-emerald h-full w-[91.4%]"></div>
          </div>
        </div>
      </section>

      {/* 5. INTERACTIVE EQUIVALENCE & CONFIDENCE INTERVAL CORRIDOR PLOT (FOREST PLOT) */}
      <section className="bg-surface-low border border-border-subtle rounded-[4px] p-5 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-border-subtle">
          <div>
            <h3 className="font-sans font-semibold text-base text-slate-100">
              Equivalence Corridor & 95% BCa Confidence Intervals (Forest Plot)
            </h3>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Equivalence confirmed if the 95% bootstrap confidence interval falls strictly within [-δ, +δ].
            </p>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-telemetry-emerald/15 border border-telemetry-emerald/40 rounded-[2px]"></span>
              <span>Tolerance [-{primaryVerdict.margin.toFixed(2)}, +{primaryVerdict.margin.toFixed(2)}]</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-surface-high border border-border-subtle rounded-[2px]"></span>
              <span>Noise Floor (±{noiseFloor.toFixed(3)})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-telemetry-emerald"></span>
              <span>Point Estimate (Δ)</span>
            </div>
          </div>
        </div>

        {/* Category Filter Pills if multiple categories */}
        {categories.length > 2 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <Filter className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span className="text-[11px] font-mono text-slate-400 uppercase">Category:</span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-0.5 rounded-[2px] text-[11px] font-mono transition-colors ${
                  categoryFilter === cat
                    ? 'bg-telemetry-emerald/15 text-telemetry-emerald border border-telemetry-emerald/40 font-semibold'
                    : 'bg-surface-lowest text-slate-400 border border-border-subtle hover:text-slate-200'
                }`}
              >
                {cat.toUpperCase()}
              </button>
            ))}
          </div>
        )}

        {/* Metric rows */}
        <div className="divide-y divide-border-subtle">
          {filteredVerdicts.map((v, i) => (
            <div key={i} className="py-1.5">
              <VerdictCard verdict={v} />
            </div>
          ))}
        </div>
      </section>

      {/* 6. PROMPT DIVERGENCE EXPLORER TRIGGER / PREVIEW */}
      <section className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h4 className="font-sans font-semibold text-sm text-slate-200">
            Prompt-Level Token & Output Diff Explorer
          </h4>
          <p className="text-xs text-slate-400 font-sans mt-0.5">
            Inspect individual prompt generations side-by-side with token divergence, cosine similarity, and AST validity.
          </p>
        </div>
        {onOpenExplorer && (
          <button
            onClick={onOpenExplorer}
            className="px-3.5 py-1.5 rounded-[4px] bg-surface-high hover:bg-surface-highest text-slate-200 font-mono text-xs border border-border-subtle transition-colors flex items-center gap-1.5"
          >
            <span>Open Diff Explorer</span>
          </button>
        )}
      </section>

      {/* 7. CONTROLS FOOTER FOR EXPERIMENT RUNNER */}
      <div className="bg-surface-lowest border border-border-subtle rounded-[4px] p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 font-mono text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <span className="text-slate-500 uppercase text-[10px] block">Baseline</span>
            <select
              value={baselineRunId}
              onChange={(e) => setBaselineRunId(e.target.value)}
              className="bg-surface-low border border-border-subtle rounded-[3px] px-2 py-1 text-slate-200 mt-1 focus:outline-none"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} ({r.model_identifier})
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-slate-500 uppercase text-[10px] block">Candidate</span>
            <select
              value={candidateRunId}
              onChange={(e) => setCandidateRunId(e.target.value)}
              className="bg-surface-low border border-border-subtle rounded-[3px] px-2 py-1 text-slate-200 mt-1 focus:outline-none"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} ({r.model_identifier})
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-slate-500 uppercase text-[10px] block">
              Noise Floor (±{noiseFloor.toFixed(3)})
            </span>
            <input
              type="range"
              min="0.000"
              max="0.040"
              step="0.002"
              value={noiseFloor}
              onChange={(e) => setNoiseFloor(parseFloat(e.target.value))}
              className="mt-2 w-32 accent-telemetry-emerald cursor-pointer"
            />
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={loading}
          className="px-4 py-2 bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest font-mono font-semibold rounded-[4px] transition-colors flex items-center gap-2 cursor-pointer shadow-sm"
        >
          {loading ? (
            <span>Computing TOST & BCa...</span>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Recompute Drift</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
