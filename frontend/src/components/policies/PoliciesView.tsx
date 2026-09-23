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
      badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      icon: ShieldAlert,
      bar: 'bg-rose-500',
    },
    high: {
      badge: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
      icon: AlertTriangle,
      bar: 'bg-orange-500',
    },
    medium: {
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: Shield,
      bar: 'bg-amber-500',
    },
    low: {
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: ShieldCheck,
      bar: 'bg-emerald-500',
    },
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Task Risk Tier Policies</h1>
        <p className="text-xs text-slate-400 mt-1">
          Each task category is mapped to a pre-declared risk policy specifying the practical equivalence margin ($\pm \Delta$), statistical significance threshold ($\alpha$), and sample size minimums.
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
              className="bg-surface-card border border-surface-border rounded-xl p-5 hover:border-slate-700 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold uppercase border ${style.badge}`}>
                    <Icon className="w-3.5 h-3.5" />
                    {p.risk_level} Risk Tier
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">{p.name}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-4 text-xs font-mono">
                  <div className="p-2.5 bg-surface-base rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 uppercase block">Practical Margin</span>
                    <span className="text-base font-bold text-white">±{(p.margin * 100).toFixed(1)}%</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">({p.margin.toFixed(3)})</span>
                  </div>

                  <div className="p-2.5 bg-surface-base rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 uppercase block">Significance Alpha (α)</span>
                    <span className="text-base font-bold text-brand-400">{p.alpha}</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">({(100 - p.alpha * 100).toFixed(1)}% Confidence)</span>
                  </div>

                  <div className="p-2.5 bg-surface-base rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 uppercase block">Min Prompts</span>
                    <span className="text-sm font-bold text-slate-200">{p.min_prompts} Prompts</span>
                  </div>

                  <div className="p-2.5 bg-surface-base rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 uppercase block">Min Repeats</span>
                    <span className="text-sm font-bold text-slate-200">{p.min_repeats} Repeats / Prompt</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-surface-border text-[11px] text-slate-400 flex items-center justify-between">
                <span>Degradation Direction:</span>
                <span className="font-mono text-slate-300 font-semibold uppercase">{p.harmful_direction}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Explanatory Callout */}
      <div className="bg-surface-card border border-brand-500/20 rounded-xl p-5 text-xs text-slate-300 leading-relaxed flex items-start space-x-3">
        <Info className="w-5 h-5 text-brand-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-white text-sm mb-1">Why Practical Margins Matter</h4>
          <p>
            In traditional naive A/B testing, any minute change can become "statistically significant" ($p &lt; 0.05$) given a large enough sample size, even if the change is a negligible 0.05% fluctuation that users will never notice. 
            DriftLab combines hypothesis testing with **Equivalence Corridors**: a candidate model is only flagged for meaningful drift if the effect size breaches the practical threshold declared in the task's risk policy.
          </p>
        </div>
      </div>
    </div>
  );
};
