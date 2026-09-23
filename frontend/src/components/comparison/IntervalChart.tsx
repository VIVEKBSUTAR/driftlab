import React from 'react';
import { DriftVerdict } from '../../types/api';

interface IntervalChartProps {
  verdict: DriftVerdict;
}

export const IntervalChart: React.FC<IntervalChartProps> = ({ verdict }) => {
  const { estimate, ci_low, ci_high, margin, noise_floor, status } = verdict;

  // Compute dynamic symmetric range for display
  const maxAbs = Math.max(
    Math.abs(ci_low),
    Math.abs(ci_high),
    Math.abs(estimate),
    margin * 1.35,
    noise_floor * 1.5,
    0.05
  );

  const width = 500;
  const height = 90;
  const paddingX = 40;
  const plotWidth = width - paddingX * 2;
  const centerY = 45;

  // Coordinate mapping function from value in [-maxAbs, maxAbs] to pixel x in [paddingX, width - paddingX]
  const valToX = (val: number): number => {
    const clamped = Math.max(-maxAbs, Math.min(maxAbs, val));
    const normalized = (clamped + maxAbs) / (2 * maxAbs);
    return paddingX + normalized * plotWidth;
  };

  const zeroX = valToX(0);
  const marginNegX = valToX(-margin);
  const marginPosX = valToX(margin);
  const noiseNegX = valToX(-noise_floor);
  const noisePosX = valToX(noise_floor);
  const ciLowX = valToX(ci_low);
  const ciHighX = valToX(ci_high);
  const estX = valToX(estimate);

  // Status color styles
  const statusColors = {
    high_risk_regression: { stroke: '#F43F5E', fill: '#E11D48', glow: 'rgba(244, 63, 94, 0.4)' },
    meaningful_drift: { stroke: '#F59E0B', fill: '#D97706', glow: 'rgba(245, 158, 11, 0.4)' },
    statistically_detected_low_impact: { stroke: '#38BDF8', fill: '#0284C7', glow: 'rgba(56, 189, 248, 0.4)' },
    no_meaningful_drift: { stroke: '#10B981', fill: '#059669', glow: 'rgba(16, 185, 129, 0.4)' },
    insufficient_evidence: { stroke: '#A855F7', fill: '#9333EA', glow: 'rgba(168, 85, 247, 0.4)' },
    insufficient_data: { stroke: '#94A3B8', fill: '#64748B', glow: 'rgba(148, 163, 184, 0.4)' },
  }[status] || { stroke: '#94A3B8', fill: '#64748B', glow: 'rgba(148, 163, 184, 0.4)' };

  return (
    <div className="w-full bg-surface-base/60 border border-surface-border/80 rounded-lg p-3">
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
        <span>Equivalence Corridor: [{-margin.toFixed(3)}, +{margin.toFixed(3)}]</span>
        <span>95% CI: [{ci_low > 0 ? `+${ci_low.toFixed(3)}` : ci_low.toFixed(3)}, {ci_high > 0 ? `+${ci_high.toFixed(3)}` : ci_high.toFixed(3)}]</span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Equivalence Corridor Shading */}
        <rect
          x={marginNegX}
          y={15}
          width={Math.max(0, marginPosX - marginNegX)}
          height={60}
          fill="rgba(16, 185, 129, 0.08)"
          stroke="rgba(16, 185, 129, 0.25)"
          strokeDasharray="3 3"
          rx={4}
        />

        {/* Noise Floor Band */}
        {noise_floor > 0 && (
          <rect
            x={noiseNegX}
            y={22}
            width={Math.max(0, noisePosX - noiseNegX)}
            height={46}
            fill="rgba(148, 163, 184, 0.06)"
            stroke="rgba(148, 163, 184, 0.2)"
            strokeDasharray="2 2"
          />
        )}

        {/* Zero baseline axis */}
        <line
          x1={zeroX}
          y1={10}
          x2={zeroX}
          y2={80}
          stroke="#475569"
          strokeWidth={1.5}
          strokeDasharray="4 2"
        />

        {/* Confidence Interval Whisker Bar */}
        <line
          x1={ciLowX}
          y1={centerY}
          x2={ciHighX}
          y2={centerY}
          stroke={statusColors.stroke}
          strokeWidth={3.5}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${statusColors.glow})` }}
        />

        {/* CI Bound Caps */}
        <line
          x1={ciLowX}
          y1={centerY - 8}
          x2={ciLowX}
          y2={centerY + 8}
          stroke={statusColors.stroke}
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <line
          x1={ciHighX}
          y1={centerY - 8}
          x2={ciHighX}
          y2={centerY + 8}
          stroke={statusColors.stroke}
          strokeWidth={2.5}
          strokeLinecap="round"
        />

        {/* Point Estimate Marker */}
        <circle
          cx={estX}
          cy={centerY}
          r={5.5}
          fill="#FFFFFF"
          stroke={statusColors.fill}
          strokeWidth={2.5}
          style={{ filter: `drop-shadow(0 0 8px ${statusColors.glow})` }}
        />

        {/* Ticks and Numerical Labels */}
        <text x={zeroX} y={88} textAnchor="middle" fill="#64748B" fontSize="10" fontFamily="monospace">
          0.00
        </text>
        <text x={marginNegX} y={12} textAnchor="middle" fill="#10B981" fontSize="9" fontFamily="monospace">
          -{margin}
        </text>
        <text x={marginPosX} y={12} textAnchor="middle" fill="#10B981" fontSize="9" fontFamily="monospace">
          +{margin}
        </text>
        <text x={estX} y={centerY - 12} textAnchor="middle" fill="#FFFFFF" fontWeight="600" fontSize="10" fontFamily="monospace">
          {estimate > 0 ? `+${estimate.toFixed(3)}` : estimate.toFixed(3)}
        </text>
      </svg>

      <div className="flex items-center justify-between text-[10px] text-slate-500 mt-0.5">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-1.5 bg-emerald-500/20 border border-emerald-500/40 rounded-sm"></span>
          Equivalence Margin (±{margin})
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-1.5 bg-slate-500/20 border border-slate-500/40 rounded-sm"></span>
          Noise Floor (±{noise_floor})
        </span>
        <span className="text-slate-400">
          p-adj: <strong className="font-mono text-slate-300">{verdict.p_adjusted.toFixed(4)}</strong>
        </span>
      </div>
    </div>
  );
};
