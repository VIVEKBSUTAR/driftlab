import React, { useState } from 'react';
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';
import { DriftVerdict } from '../../types/api';
import { StatusBadge } from '../common/StatusBadge';
import { IntervalChart } from './IntervalChart';

interface VerdictCardProps {
  verdict: DriftVerdict;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ verdict }) => {
  const [expanded, setExpanded] = useState(false);

  const riskTierColors = {
    critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  }[verdict.risk_level] || 'bg-slate-500/10 text-slate-400 border-slate-500/30';

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden hover:border-slate-700 transition-all">
      <div className="p-5">
        {/* Card Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center space-x-3">
            <div className="flex flex-col">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-semibold text-white uppercase tracking-wider">
                  {verdict.category}
                </span>
                <span className="text-slate-500">•</span>
                <span className="text-sm font-medium text-slate-300">
                  {verdict.metric_id}
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono mt-0.5">
                Task Tier: <span className={`uppercase font-semibold px-1.5 py-0.2 rounded border text-[10px] ${riskTierColors}`}>{verdict.risk_level}</span>
              </span>
            </div>
          </div>

          <StatusBadge status={verdict.status} />
        </div>

        {/* Visual Interval Plot */}
        <div className="my-3">
          <IntervalChart verdict={verdict} />
        </div>

        {/* Executive Summary Explanation */}
        <div className="mt-3 p-3 rounded-lg bg-surface-elevated/60 border border-surface-border/60 text-xs text-slate-300 leading-relaxed flex items-start space-x-2">
          <HelpCircle className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-white">Statistical Verdict: </span>
            {verdict.explanation}
          </div>
        </div>

        {/* Accordion Toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 w-full flex items-center justify-center space-x-1.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-surface-hover rounded transition-colors"
        >
          <span>{expanded ? 'Hide Statistics Breakdown' : 'Show Statistical Metrics Breakdown'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {/* Expanded Statistics Table */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-surface-border grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-surface-base p-2.5 rounded border border-surface-border">
              <span className="text-slate-500 block text-[10px] uppercase font-mono">Point Estimate</span>
              <span className="font-mono font-bold text-white text-sm">
                {verdict.estimate > 0 ? `+${verdict.estimate.toFixed(4)}` : verdict.estimate.toFixed(4)}
              </span>
            </div>
            <div className="bg-surface-base p-2.5 rounded border border-surface-border">
              <span className="text-slate-500 block text-[10px] uppercase font-mono">BCa Bootstrap CI</span>
              <span className="font-mono font-bold text-white text-sm">
                [{verdict.ci_low.toFixed(3)}, {verdict.ci_high.toFixed(3)}]
              </span>
            </div>
            <div className="bg-surface-base p-2.5 rounded border border-surface-border">
              <span className="text-slate-500 block text-[10px] uppercase font-mono">Adjusted p-value</span>
              <span className="font-mono font-bold text-white text-sm">
                {verdict.p_adjusted.toFixed(4)}
              </span>
            </div>
            <div className="bg-surface-base p-2.5 rounded border border-surface-border">
              <span className="text-slate-500 block text-[10px] uppercase font-mono">Noise Floor</span>
              <span className="font-mono font-bold text-white text-sm">
                {verdict.noise_floor.toFixed(4)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
