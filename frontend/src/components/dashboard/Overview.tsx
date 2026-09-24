import React, { useEffect, useState } from 'react';
import {
  Activity,
  Layers,
  ArrowRight,
  TrendingUp,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  HelpCircle,
  Clock,
  Sliders,
} from 'lucide-react';
import { RunRecord } from '../../types/api';
import { fetchRuns } from '../../services/api';
import { MetricCard } from '../common/MetricCard';
import { Skeleton } from '../common/Skeleton';

interface OverviewProps {
  onNavigate: (tab: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({ onNavigate }) => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchRuns();
        setRuns(data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const totalRuns = runs.length;
  const baselineCount = runs.filter((r) => r.run_type === 'baseline').length;
  const candidateCount = runs.filter((r) => r.run_type === 'candidate').length;
  const totalObservations = runs.reduce((acc, r) => acc + (r.observations_count || 0), 0);

  const decisionRules = [
    {
      rule: '1. Insufficient Data',
      desc: 'Prompt or repeat count below risk policy minimum sample size.',
      badge: 'bg-slate-500/10 text-slate-300 border-slate-600/30',
      icon: Clock,
    },
    {
      rule: '2. High Risk Regression',
      desc: 'Statistically significant drop in quality beyond declared margin in high/critical risk task.',
      badge: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
      icon: AlertOctagon,
    },
    {
      rule: '3. Meaningful Drift',
      desc: 'Statistically significant difference with effect size exceeding the practical equivalence margin.',
      badge: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
      icon: AlertTriangle,
    },
    {
      rule: '4. Detected (Low Impact)',
      desc: 'Statistically detected difference, but effect size lies safely inside the acceptable margin.',
      badge: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
      icon: Activity,
    },
    {
      rule: '5. No Meaningful Drift',
      desc: 'Equivalence confirmed: entire confidence interval lies inside the practical margin corridor.',
      badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
      icon: CheckCircle2,
    },
    {
      rule: '6. Insufficient Evidence',
      desc: 'Absence of statistical significance is never proof of no drift. Reported as no sufficient evidence.',
      badge: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
      icon: HelpCircle,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Telemetry Hero Panel */}
      <div className="bg-surface-low border border-border-subtle rounded-[4px] p-6 lg:p-7 relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-2 py-0.5 rounded-[2px] bg-telemetry-emerald/10 text-telemetry-emerald border border-telemetry-emerald/30 text-[11px] font-mono mb-3 font-semibold">
            <Sliders className="w-3.5 h-3.5 text-telemetry-emerald" />
            <span>Statistical Equivalence & Drift Governance</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold font-sans text-slate-100 tracking-tight leading-tight">
            Behavioral Drift Detection & Statistical Validation
          </h1>
          <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
            Distinguish true model drift from natural run-to-run variability. DriftLab combines prompt-clustered BCa bootstrap confidence intervals, label permutation tests, and task-specific risk policy margins.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('comparison')}
              className="flex items-center gap-2 px-4 py-2 bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest text-xs font-mono font-semibold rounded-[4px] shadow-sm transition-colors cursor-pointer"
            >
              <span>Launch Drift Workbench</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('explorer')}
              className="flex items-center gap-2 px-4 py-2 bg-surface-high hover:bg-surface-highest text-slate-200 border border-border-subtle text-xs font-mono font-medium rounded-[4px] transition-colors cursor-pointer"
            >
              <Cpu className="w-4 h-4 text-telemetry-emerald" />
              <span>Prompt Diff Explorer</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Recorded Runs"
          value={loading ? '...' : totalRuns}
          subtitle={`${baselineCount} Baseline / ${candidateCount} Candidate`}
          icon={Layers}
          badge="SQLite Store"
          badgeColor="brand"
        />
        <MetricCard
          title="Observations Logged"
          value={loading ? '...' : totalObservations}
          subtitle="Prompt repeats in JSONL"
          icon={Activity}
          badge="Immutable Truth"
          badgeColor="emerald"
        />
        <MetricCard
          title="Statistical Coverage"
          value="95% BCa"
          subtitle="Prompt-clustered bootstrap"
          icon={TrendingUp}
          badge="Calibrated"
          badgeColor="emerald"
        />
        <MetricCard
          title="Active Backends"
          value="Ollama + Mock"
          subtitle="Local & deterministic GPUs"
          icon={Cpu}
          badge="Zero-GPU CI/CD"
          badgeColor="amber"
        />
      </div>

      {/* The 6 Decision Rules Section */}
      <div className="bg-surface-low border border-border-subtle rounded-[4px] p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold font-sans text-slate-100 tracking-tight">The 6 Ordered Decision Rules</h2>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Applied in strict sequence. Absence of statistical significance is never reported as proof of no drift.
            </p>
          </div>
          <span className="text-[11px] font-mono text-telemetry-emerald bg-telemetry-emerald/10 px-2 py-0.5 rounded-[2px] border border-telemetry-emerald/20 font-semibold">
            Hierarchy Engine
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {decisionRules.map((rule, idx) => {
            const Icon = rule.icon;
            return (
              <div
                key={idx}
                className="bg-surface-lowest border border-border-subtle rounded-[3px] p-3 hover:border-slate-700 transition-colors flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-xs font-semibold text-slate-100">{rule.rule}</span>
                    <div className={`p-1 rounded-[2px] border ${rule.badge}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans">{rule.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Runs Preview */}
      <div className="bg-surface-low border border-border-subtle rounded-[4px] p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold font-sans text-slate-100 tracking-tight">Recent Benchmark Runs</h2>
          <button
            onClick={() => onNavigate('runs')}
            className="text-xs font-mono font-semibold text-telemetry-emerald hover:underline flex items-center gap-1"
          >
            <span>View All Runs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : runs.length > 0 ? (
          <div className="divide-y divide-border-subtle overflow-hidden rounded-[3px] border border-border-subtle bg-surface-lowest">
            {runs.slice(0, 4).map((run) => (
              <div
                key={run.id}
                className="p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 hover:bg-surface-high/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded-[2px] border ${
                      run.run_type === 'baseline'
                        ? 'bg-telemetry-indigo/15 text-telemetry-indigoLight border-telemetry-indigo/30'
                        : 'bg-telemetry-violet/15 text-telemetry-violetLight border-telemetry-violet/30'
                    }`}
                  >
                    {run.run_type}
                  </span>
                  <div>
                    <span className="font-mono text-xs font-semibold text-slate-200 block">{run.id}</span>
                    <span className="text-[11px] text-slate-400 font-mono">{run.model_identifier || 'Unknown Model'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                  <span>{run.observations_count} observations</span>
                  <span className="text-slate-500">
                    {run.created_at ? new Date(run.created_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 py-4 text-center font-mono">No runs recorded yet.</p>
        )}
      </div>
    </div>
  );
};
