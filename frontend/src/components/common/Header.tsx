import React, { useEffect, useState } from 'react';
import { GitCompare, Sliders, Layers, Terminal, ShieldCheck, Database, HelpCircle, FileText } from 'lucide-react';
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
    { id: 'comparison', label: 'Drift Workbench', icon: GitCompare },
    { id: 'explorer', label: 'Prompt Diff Explorer', icon: FileText },
    { id: 'dashboard', label: 'Telemetry Overview', icon: Layers },
    { id: 'runs', label: 'Run History', icon: Database },
    { id: 'policies', label: 'Risk Policies', icon: ShieldCheck },
  ];

  return (
    <header className="flex justify-between items-center w-full px-6 h-14 border-b border-border-subtle bg-surface-lowest sticky top-0 z-50">
      {/* Brand & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setActiveTab('comparison')}>
          <div className="w-7 h-7 rounded-[4px] bg-telemetry-emerald/10 border border-telemetry-emerald/30 flex items-center justify-center text-telemetry-emerald">
            <GitCompare className="w-4 h-4" />
          </div>
          <span className="font-semibold text-base tracking-tight text-slate-100 font-sans">
            DriftLab
          </span>
        </div>
        <span className="px-1.5 py-0.5 rounded-[3px] bg-surface-high text-telemetry-emerald font-mono text-[10px] border border-border-subtle font-semibold">
          v0.1.0-alpha
        </span>
        <div className="h-4 w-[1px] bg-border-subtle mx-1 hidden sm:block"></div>
        <div className="hidden sm:flex items-center gap-1.5 font-mono text-xs text-slate-400">
          <span>Benchmarks</span>
          <span className="text-slate-600">/</span>
          <span className="text-slate-200">llama-3-8b-instruct-drift</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="hidden md:flex items-center gap-6 h-full">
        {navItems.map((item) => {
          const active = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`h-full flex items-center gap-2 font-mono text-xs transition-colors border-b-2 pt-0.5 ${
                active
                  ? 'border-telemetry-emerald text-telemetry-emerald font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Trailing Status & Actions */}
      <div className="flex items-center gap-3">
        {/* Status Pills */}
        <div className="hidden lg:flex items-center gap-2 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-[3px] bg-surface-low border border-border-subtle">
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-telemetry-emerald animate-pulse' : 'bg-telemetry-amber'}`}></span>
            <span className="text-slate-400">Daemon:</span>
            <span className={isOnline ? 'text-telemetry-emerald' : 'text-telemetry-amber'}>
              {isOnline ? 'Connected' : 'Demo Mode'}
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-[3px] bg-surface-low border border-border-subtle">
            <span className="w-1.5 h-1.5 rounded-full bg-telemetry-emerald"></span>
            <span className="text-slate-400">DB:</span>
            <span className="text-slate-200">In Sync</span>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={() => setActiveTab('studio')}
          className="px-3 py-1.5 rounded-[4px] bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest font-mono text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Run Benchmark</span>
        </button>

        {/* Quick icons */}
        <div className="hidden sm:flex items-center gap-1 text-slate-400">
          <button
            onClick={() => setActiveTab('studio')}
            className="p-1.5 rounded hover:bg-surface-high hover:text-slate-200 transition-colors"
            title="Benchmark Runner"
          >
            <Terminal className="w-4 h-4" />
          </button>
          <a
            href="https://github.com/VIVEKBSUTAR/driftlab"
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded hover:bg-surface-high hover:text-slate-200 transition-colors"
            title="Documentation"
          >
            <HelpCircle className="w-4 h-4" />
          </a>
        </div>

        {/* User avatar */}
        <div className="w-7 h-7 rounded-[4px] bg-surface-high border border-border-subtle flex items-center justify-center font-mono text-[11px] font-bold text-telemetry-emerald" title="Lead Systems Architect">
          SA
        </div>
      </div>
    </header>
  );
};

