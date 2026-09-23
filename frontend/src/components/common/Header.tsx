import React, { useEffect, useState } from 'react';
import { Activity, Cpu, Layers, PlayCircle, ShieldCheck, Zap } from 'lucide-react';
import { checkApiHealth } from '../../services/api';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      const ok = await checkApiHealth();
      if (mounted) setIsOnline(ok);
    };
    check();
    const interval = setInterval(check, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: Activity },
    { id: 'comparison', label: 'Drift Analysis', icon: Zap },
    { id: 'runs', label: 'Runs Explorer', icon: Layers },
    { id: 'studio', label: 'Benchmark Studio', icon: PlayCircle },
    { id: 'policies', label: 'Risk Policies', icon: ShieldCheck },
  ];

  return (
    <header className="border-b border-surface-border bg-surface-card/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                DriftLab
              </span>
              <span className="px-1.5 py-0.5 text-[10px] uppercase font-mono font-bold tracking-widest bg-brand-500/10 text-brand-400 border border-brand-500/20 rounded">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Statistical LLM Drift Detection</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? 'bg-brand-500/15 text-brand-300 border border-brand-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-hover'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-brand-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Status Indicator */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-surface-base border border-surface-border text-xs">
            <span
              className={`w-2 h-2 rounded-full animate-pulse ${
                isOnline === true ? 'bg-emerald-400' : isOnline === false ? 'bg-amber-400' : 'bg-slate-500'
              }`}
            />
            <span className="text-slate-300 font-mono text-[11px]">
              {isOnline === true ? 'Backend: Connected' : isOnline === false ? 'Backend: Offline (Demo Mode)' : 'Connecting...'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
