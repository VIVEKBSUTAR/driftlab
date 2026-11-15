import React from 'react';
import { DriftStatus } from '../../types/api';

interface StatusBadgeProps {
  status: DriftStatus;
  className?: string;
}

type StatusConfig = {
  label: string;
  dot: string;
  text: string;
  bg: string;
  border: string;
};

const STATUS_MAP: Record<string, StatusConfig> = {
  no_meaningful_drift: {
    label: 'Equivalent',
    dot: 'bg-status-green',
    text: 'text-status-green',
    bg: 'bg-status-greenDim',
    border: 'border-status-green/25',
  },
  meaningful_drift: {
    label: 'Meaningful Drift',
    dot: 'bg-status-amber',
    text: 'text-status-amber',
    bg: 'bg-status-amberDim',
    border: 'border-status-amber/25',
  },
  high_risk_regression: {
    label: 'High-Risk Regression',
    dot: 'bg-status-red pulse-dot',
    text: 'text-status-red',
    bg: 'bg-status-redDim',
    border: 'border-status-red/25',
  },
  statistically_detected_low_impact: {
    label: 'Low Impact',
    dot: 'bg-status-blue',
    text: 'text-status-blue',
    bg: 'bg-status-blueDim',
    border: 'border-status-blue/25',
  },
  insufficient_evidence: {
    label: 'Insufficient Evidence',
    dot: 'bg-text-muted',
    text: 'text-text-secondary',
    bg: 'bg-bg-subtle',
    border: 'border-border-base',
  },
  insufficient_data: {
    label: 'Insufficient Data',
    dot: 'bg-text-muted',
    text: 'text-text-secondary',
    bg: 'bg-bg-subtle',
    border: 'border-border-base',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const cfg = STATUS_MAP[status] ?? STATUS_MAP.insufficient_data;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${cfg.bg} ${cfg.text} ${cfg.border} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
};
