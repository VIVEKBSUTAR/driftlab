import React from 'react';
import { AlertOctagon, AlertTriangle, CheckCircle, HelpCircle, Info, Clock } from 'lucide-react';
import { DriftStatus } from '../../types/api';

interface StatusBadgeProps {
  status: DriftStatus;
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, showIcon = true }) => {
  switch (status) {
    case 'high_risk_regression':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 shadow-sm shadow-rose-900/20">
          {showIcon && <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />}
          High Risk Regression
        </span>
      );
    case 'meaningful_drift':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
          {showIcon && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
          Meaningful Drift
        </span>
      );
    case 'statistically_detected_low_impact':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-300 border border-sky-500/30">
          {showIcon && <Info className="w-3.5 h-3.5 text-sky-400" />}
          Detected (Low Impact)
        </span>
      );
    case 'no_meaningful_drift':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
          {showIcon && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
          No Meaningful Drift
        </span>
      );
    case 'insufficient_evidence':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
          {showIcon && <HelpCircle className="w-3.5 h-3.5 text-purple-400" />}
          Insufficient Evidence
        </span>
      );
    case 'insufficient_data':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-300 border border-slate-500/30">
          {showIcon && <Clock className="w-3.5 h-3.5 text-slate-400" />}
          Insufficient Data
        </span>
      );
  }
};
