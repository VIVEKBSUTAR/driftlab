import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Sliders } from 'lucide-react';
import { DriftVerdict } from '../../types/api';
import { StatusBadge } from '../common/StatusBadge';
import { IntervalChart } from './IntervalChart';

interface VerdictCardProps {
  verdict: DriftVerdict;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ verdict }) => {
  const [expanded, setExpanded] = useState(false);

  const riskTierBadges = {
    critical: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    high: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    medium: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    low: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  }[verdict.risk_level] || 'bg-slate-500/10 text-slate-300 border-slate-600/30';

  return (
    <div className="bg-surface-lowest border border-border-subtle rounded-[4px] overflow-hidden my-2">
      <div className="p-4">
        {/* Card Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-slate-100 uppercase tracking-wider">
                  {verdict.category}
                </span>
                <span className="text-slate-600">•</span>
                <span className="text-xs font-semibold text-slate-300 font-mono">
                  {verdict.metric_id}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono mt-0.5">
                Risk Tier: <span className={`uppercase font-semibold px-1.5 py-0.2 rounded-[2px] border text-[10px] ${riskTierBadges}`}>{verdict.risk_level}</span>
              </span>
            </div>
          </div>

          <StatusBadge status={verdict.status} />
        </div>

        {/* Visual Interval Plot */}
        <div className="my-2">
          <IntervalChart verdict={verdict} />
        </div>

        {/* Explanation Banner */}
        <div className="mt-2.5 p-2.5 rounded-[3px] bg-surface-low border border-border-subtle text-xs text-slate-300 leading-relaxed flex items-start gap-2">
          <Sliders className="w-4 h-4 text-telemetry-emerald shrink-0 mt-0.5" />
          <div className="font-sans">
            <span className="font-semibold text-slate-100 font-mono">Decision: </span>
            {verdict.explanation}
          </div>
        </div>

        {/* Accordion Toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2.5 w-full flex items-center justify-center gap-1.5 py-1 text-[11px] font-mono text-slate-400 hover:text-slate-200 hover:bg-surface-high rounded-[3px] transition-colors"
        >
          <span>{expanded ? 'Hide Statistical Breakdown' : 'Show Statistical Breakdown'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {/* Expanded Statistics Table */}
        {expanded && (
          <div className="mt-2.5 pt-2.5 border-t border-border-subtle grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
            <div className="bg-surface-low p-2 rounded-[3px] border border-border-subtle">
              <span className="text-slate-500 block text-[10px] uppercase">Point Estimate (Δ)</span>
              <span className="font-bold text-slate-100 text-sm">
                {verdict.estimate > 0 ? `+${verdict.estimate.toFixed(4)}` : verdict.estimate.toFixed(4)}
              </span>
            </div>
            <div className="bg-surface-low p-2 rounded-[3px] border border-border-subtle">
              <span className="text-slate-500 block text-[10px] uppercase">95% BCa Bootstrap CI</span>
              <span className="font-bold text-slate-100 text-sm">
                [{verdict.ci_low.toFixed(3)}, {verdict.ci_high.toFixed(3)}]
              </span>
            </div>
            <div className="bg-surface-low p-2 rounded-[3px] border border-border-subtle">
              <span className="text-slate-500 block text-[10px] uppercase">Adjusted p-value</span>
              <span className="font-bold text-slate-100 text-sm">
                {verdict.p_adjusted.toFixed(4)}
              </span>
            </div>
            <div className="bg-surface-low p-2 rounded-[3px] border border-border-subtle">
              <span className="text-slate-500 block text-[10px] uppercase">Noise Floor (σ₀)</span>
              <span className="font-bold text-slate-100 text-sm">
                {verdict.noise_floor.toFixed(4)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
