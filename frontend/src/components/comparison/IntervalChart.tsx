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
    margin * 1.3,
    noise_floor * 1.5,
    0.05
  );

  const width = 500;
  const height = 75;
  const paddingX = 40;
  const plotWidth = width - paddingX * 2;
  const centerY = 38;

  // Coordinate mapping function
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

  // Semantic status colors matching Obsidian Telemetry tokens
  const statusColors = {
    high_risk_regression: { stroke: '#ef4444', fill: '#ffb4ab', glow: 'rgba(239, 68, 68, 0.4)' },
    meaningful_drift: { stroke: '#f59e0b', fill: '#fbbf24', glow: 'rgba(245, 158, 11, 0.4)' },
    statistically_detected_low_impact: { stroke: '#6366f1', fill: '#c0c1ff', glow: 'rgba(99, 102, 241, 0.4)' },
    no_meaningful_drift: { stroke: '#10b981', fill: '#4edea3', glow: 'rgba(16, 185, 129, 0.4)' },
    insufficient_evidence: { stroke: '#a855f7', fill: '#ddb7ff', glow: 'rgba(168, 85, 247, 0.4)' },
    insufficient_data: { stroke: '#64748b', fill: '#94a3b8', glow: 'rgba(100, 116, 139, 0.4)' },
  }[status] || { stroke: '#64748b', fill: '#94a3b8', glow: 'rgba(100, 116, 139, 0.4)' };

  return (
    <div className="w-full bg-surface-lowest border border-border-subtle rounded-[4px] p-2.5">
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
        <span>Equivalence Corridor: [{-margin.toFixed(3)}, +{margin.toFixed(3)}]</span>
        <span>95% CI: [{ci_low > 0 ? `+${ci_low.toFixed(3)}` : ci_low.toFixed(3)}, {ci_high > 0 ? `+${ci_high.toFixed(3)}` : ci_high.toFixed(3)}]</span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Equivalence Corridor Shading */}
        <rect
          x={marginNegX}
          y={10}
          width={Math.max(0, marginPosX - marginNegX)}
          height={55}
          fill="rgba(16, 185, 129, 0.08)"
          stroke="rgba(16, 185, 129, 0.3)"
          strokeDasharray="3 3"
          rx={2}
        />

        {/* Noise Floor Band */}
        {noise_floor > 0 && (
          <rect
            x={noiseNegX}
            y={15}
            width={Math.max(0, noisePosX - noiseNegX)}
            height={45}
            fill="rgba(255, 255, 255, 0.03)"
            stroke="rgba(100, 116, 139, 0.25)"
            strokeDasharray="2 2"
          />
        )}

        {/* Zero baseline axis */}
        <line
          x1={zeroX}
          y1={6}
          x2={zeroX}
          y2={69}
          stroke="#475569"
          strokeWidth={1.2}
          strokeDasharray="3 2"
        />

        {/* Confidence Interval Whisker Bar */}
        <line
          x1={ciLowX}
          y1={centerY}
          x2={ciHighX}
          y2={centerY}
          stroke={statusColors.stroke}
          strokeWidth={3}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${statusColors.glow})` }}
        />

        {/* CI Bound Caps */}
        <line
          x1={ciLowX}
          y1={centerY - 7}
          x2={ciLowX}
          y2={centerY + 7}
          stroke={statusColors.stroke}
          strokeWidth={2}
          strokeLinecap="round"
        />
        <line
          x1={ciHighX}
          y1={centerY - 7}
          x2={ciHighX}
          y2={centerY + 7}
          stroke={statusColors.stroke}
          strokeWidth={2}
          strokeLinecap="round"
        />

        {/* Point Estimate Marker */}
        <circle
          cx={estX}
          cy={centerY}
          r={5}
          fill="#FFFFFF"
          stroke={statusColors.stroke}
          strokeWidth={2}
          style={{ filter: `drop-shadow(0 0 6px ${statusColors.glow})` }}
        />

        {/* Ticks and Numerical Labels */}
        <text x={zeroX} y={72} textAnchor="middle" fill="#64748B" fontSize="9" fontFamily="monospace">
          0.00
        </text>
        <text x={marginNegX} y={9} textAnchor="middle" fill="#10B981" fontSize="9" fontFamily="monospace">
          -{margin}
        </text>
        <text x={marginPosX} y={9} textAnchor="middle" fill="#10B981" fontSize="9" fontFamily="monospace">
          +{margin}
        </text>
        <text x={estX} y={centerY - 10} textAnchor="middle" fill="#FFFFFF" fontWeight="600" fontSize="9" fontFamily="monospace">
          {estimate > 0 ? `+${estimate.toFixed(3)}` : estimate.toFixed(3)}
        </text>
      </svg>

      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-1 pt-1 border-t border-border-subtle/50">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-1.5 bg-telemetry-emerald/20 border border-telemetry-emerald/40 rounded-[2px]"></span>
          Equivalence Margin (±{margin})
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-1.5 bg-surface-high border border-border-subtle rounded-[2px]"></span>
          Noise Floor (±{noise_floor})
        </span>
        <span className="text-slate-400">
          p-adj: <strong className="font-mono text-slate-200">{verdict.p_adjusted.toFixed(4)}</strong>
        </span>
      </div>
    </div>
  );
};
