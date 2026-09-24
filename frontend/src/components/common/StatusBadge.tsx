import React from 'react';
import { DriftStatus } from '../../types/api';

interface StatusBadgeProps {
  status: DriftStatus;
  showPip?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, showPip = true, className = '' }) => {
  switch (status) {
    case 'high_risk_regression':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-rose-500/10 text-rose-300 border border-rose-500/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />}
          High Risk Regression
        </span>
      );
    case 'meaningful_drift':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-amber-500/10 text-amber-300 border border-amber-500/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />}
          Meaningful Drift
        </span>
      );
    case 'statistically_detected_low_impact':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
          Detected (Low Impact)
        </span>
      );
    case 'no_meaningful_drift':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
          Equivalence Verified
        </span>
      );
    case 'insufficient_evidence':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-purple-500/10 text-purple-300 border border-purple-500/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />}
          Insufficient Evidence
        </span>
      );
    case 'insufficient_data':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] font-mono text-[11px] font-semibold tracking-wider uppercase bg-slate-500/10 text-slate-300 border border-slate-600/30 ${className}`}>
          {showPip && <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />}
          Insufficient Data
        </span>
      );
  }
};

