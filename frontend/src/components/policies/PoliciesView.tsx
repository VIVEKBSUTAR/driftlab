import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Shield, Info } from 'lucide-react';
import { RiskPolicyConfig } from '../../types/api';

export const PoliciesView: React.FC = () => {
  const policies: RiskPolicyConfig[] = [
    {
      name: 'low_risk_default',
      risk_level: 'low',
      margin: 0.08,
      alpha: 0.05,
      min_prompts: 5,
      min_repeats: 3,
      harmful_direction: 'negative',
    },
    {
      name: 'medium_risk_default',
      risk_level: 'medium',
      margin: 0.05,
      alpha: 0.05,
      min_prompts: 10,
      min_repeats: 3,
      harmful_direction: 'negative',
    },
    {
      name: 'high_risk_default',
      risk_level: 'high',
      margin: 0.03,
      alpha: 0.01,
      min_prompts: 20,
      min_repeats: 5,
      harmful_direction: 'negative',
    },
    {
      name: 'critical_risk_default',
      risk_level: 'critical',
      margin: 0.015,
      alpha: 0.005,
      min_prompts: 30,
      min_repeats: 5,
      harmful_direction: 'negative',
    },
  ];

  const tierStyles = {
    critical: {
      badge: 'bg-telemetry-rose/10 text-telemetry-roseLight border-telemetry-rose/30',
      icon: ShieldAlert,
    },
    high: {
      badge: 'bg-telemetry-amber/10 text-telemetry-amber border-telemetry-amber/30',
      icon: AlertTriangle,
    },
    medium: {
      badge: 'bg-telemetry-indigo/10 text-telemetry-indigoLight border-telemetry-indigo/30',
      icon: Shield,
    },
    low: {
      badge: 'bg-telemetry-emerald/10 text-telemetry-emerald border-telemetry-emerald/30',
      icon: ShieldCheck,
    },
  };

  return (
    <div className="space-y-5">
      <div className="pb-3 border-b border-border-subtle">
        <h1 className="text-xl font-bold font-sans text-slate-100 tracking-tight">Task Risk Tier Policies</h1>
        <p className="text-xs text-slate-400 mt-0.5 font-sans">
          Each task category is mapped to a pre-declared risk policy specifying the practical equivalence margin ($\pm \delta$), statistical significance threshold ($\alpha$), and sample size minimums.
        </p>
      </div>

      {/* Policy Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {policies.map((p) => {
          const style = tierStyles[p.risk_level];
          const Icon = style.icon;
          return (
            <div
              key={p.risk_level}
              className="bg-surface-low border border-border-subtle rounded-[4px] p-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[2px] text-[11px] font-mono font-bold uppercase border ${style.badge}`}>
                    <Icon className="w-3.5 h-3.5" />
                    {p.risk_level} Risk Tier
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">{p.name}</span>
                </div>

                <div className="grid grid-cols-2 gap-2.5 mt-3 text-xs font-mono">
                  <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                    <span className="text-[10px] text-slate-500 uppercase block">Practical Margin (±δ)</span>
                    <span className="text-base font-bold text-slate-100">±{(p.margin * 100).toFixed(1)}%</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5 font-mono">({p.margin.toFixed(3)})</span>
                  </div>

                  <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                    <span className="text-[10px] text-slate-500 uppercase block">Significance Alpha (α)</span>
                    <span className="text-base font-bold text-telemetry-emerald">{p.alpha}</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">({(100 - p.alpha * 100).toFixed(1)}% Confidence)</span>
                  </div>

                  <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                    <span className="text-[10px] text-slate-500 uppercase block">Min Prompts</span>
                    <span className="text-xs font-bold text-slate-200">{p.min_prompts} Prompts</span>
                  </div>

                  <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                    <span className="text-[10px] text-slate-500 uppercase block">Min Repeats</span>
                    <span className="text-xs font-bold text-slate-200">{p.min_repeats} Repeats / Prompt</span>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-border-subtle text-[11px] text-slate-400 flex items-center justify-between font-mono">
                <span>Degradation Direction:</span>
                <span className="text-slate-300 font-semibold uppercase">{p.harmful_direction}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Explanatory Callout */}
      <div className="bg-surface-low border border-telemetry-emerald/30 rounded-[4px] p-4 text-xs text-slate-300 leading-relaxed flex items-start gap-3">
        <Info className="w-4 h-4 text-telemetry-emerald shrink-0 mt-0.5" />
        <div className="font-sans">
          <h4 className="font-bold text-slate-100 text-xs mb-1 font-mono">Why Practical Margins Matter</h4>
          <p className="text-slate-400 text-xs leading-normal">
            In naive A/B testing, any minute change can become "statistically significant" ($p &lt; 0.05$) given a large enough sample size, even if the change is a negligible 0.05% fluctuation that users will never notice. 
            DriftLab combines hypothesis testing with **Equivalence Corridors**: a candidate model is only flagged for meaningful drift if the effect size breaches the practical threshold declared in the task's risk policy.
          </p>
        </div>
      </div>
    </div>
  );
};
