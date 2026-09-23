import React, { useEffect, useState } from 'react';
import {
  Activity,
  Layers,
  Zap,
  ArrowRight,
  TrendingUp,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  HelpCircle,
  Clock,
  Play,
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
      badge: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
      icon: Clock,
    },
    {
      rule: '2. High Risk Regression',
      desc: 'Statistically significant drop in quality beyond declared margin in high/critical risk task.',
      badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      icon: AlertOctagon,
    },
    {
      rule: '3. Meaningful Drift',
      desc: 'Statistically significant difference with effect size exceeding the practical equivalence margin.',
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: AlertTriangle,
    },
    {
      rule: '4. Detected (Low Impact)',
      desc: 'Statistically detected difference, but effect size lies safely inside the acceptable margin.',
      badge: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
      icon: Activity,
    },
    {
      rule: '5. No Meaningful Drift',
      desc: 'Equivalence confirmed: entire confidence interval lies inside the practical margin corridor.',
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: CheckCircle2,
    },
    {
      rule: '6. Insufficient Evidence',
      desc: 'Absence of statistical significance is never proof of no drift. Reported as no sufficient evidence.',
      badge: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      icon: HelpCircle,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-surface-card via-surface-elevated to-surface-card border border-surface-border p-6 lg:p-8">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20 text-xs font-mono mb-3">
            <Zap className="w-3.5 h-3.5 text-brand-400" />
            <span>Rigorous LLM Drift Validation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight leading-tight">
            Behavioral Drift Detection & Equivalence Verification
          </h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Distinguish true model drift from natural run-to-run variability. DriftLab combines prompt-clustered BCa bootstrap confidence intervals, label permutation tests, and task-specific risk policy margins.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('comparison')}
              className="flex items-center space-x-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-brand-600/30 transition-all cursor-pointer"
            >
              <span>Launch Drift Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('studio')}
              className="flex items-center space-x-2 px-4 py-2.5 bg-surface-elevated hover:bg-surface-hover text-slate-200 border border-surface-border text-sm font-medium rounded-lg transition-all cursor-pointer"
            >
              <Play className="w-4 h-4 text-brand-400" />
              <span>Run Benchmark Studio</span>
            </button>
          </div>
        </div>

        {/* Ambient background glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 bg-brand-600/10 rounded-full blur-3xl pointer-events-none" />
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
          badge="Source of Truth"
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
      <div className="bg-surface-card border border-surface-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">The 6 Ordered Decision Rules</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Applied in strict sequence. Absence of statistical significance is never reported as proof of no drift.
            </p>
          </div>
          <span className="text-xs font-mono text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
            Hierarchy Engine
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {decisionRules.map((rule, idx) => {
            const Icon = rule.icon;
            return (
              <div
                key={idx}
                className="bg-surface-base/80 border border-surface-border rounded-lg p-3.5 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-white">{rule.rule}</span>
                    <div className={`p-1 rounded border ${rule.badge}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{rule.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Runs Preview */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-white tracking-tight">Recent Benchmark Runs</h2>
          <button
            onClick={() => onNavigate('runs')}
            className="text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center space-x-1"
          >
            <span>View All Runs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : runs.length > 0 ? (
          <div className="divide-y divide-surface-border overflow-hidden rounded-lg border border-surface-border">
            {runs.slice(0, 4).map((run) => (
              <div
                key={run.id}
                className="p-3.5 bg-surface-base flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                      run.run_type === 'baseline'
                        ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                        : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                    }`}
                  >
                    {run.run_type}
                  </span>
                  <div>
                    <span className="font-mono text-xs font-semibold text-white block">{run.id}</span>
                    <span className="text-xs text-slate-400 font-mono">{run.model_identifier || 'Unknown Model'}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-4 text-xs font-mono text-slate-400">
                  <span>{run.observations_count} observations</span>
                  <span className="text-slate-500">
                    {run.created_at ? new Date(run.created_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 py-4 text-center">No runs recorded yet.</p>
        )}
      </div>
    </div>
  );
};
