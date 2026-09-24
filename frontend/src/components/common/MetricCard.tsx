import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  badge?: string;
  badgeColor?: 'emerald' | 'amber' | 'rose' | 'brand';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  badgeColor = 'brand',
}) => {
  const badgeClasses = {
    brand: 'bg-telemetry-emerald/10 text-telemetry-emerald border-telemetry-emerald/30',
    emerald: 'bg-telemetry-emerald/10 text-telemetry-emerald border-telemetry-emerald/30',
    amber: 'bg-telemetry-amber/10 text-telemetry-amber border-telemetry-amber/30',
    rose: 'bg-telemetry-rose/10 text-telemetry-roseLight border-telemetry-rose/30',
  }[badgeColor];

  return (
    <div className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className="w-7 h-7 rounded-[4px] bg-surface-high border border-border-subtle flex items-center justify-center text-slate-300">
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <span className="text-2xl font-bold font-mono text-slate-100 tracking-tight">{value}</span>
        {badge && (
          <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-[2px] border ${badgeClasses}`}>
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500 font-sans">{subtitle}</p>}
    </div>
  );
};
