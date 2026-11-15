import React, { useEffect, useState } from 'react';
import { FlaskConical, LayoutGrid, GitCompare, History, Play } from 'lucide-react';
import { checkApiHealth } from '../../services/api';
import type { TabId } from '../../App';

interface HeaderProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
}

const navItems: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview',  label: 'Overview',  icon: LayoutGrid },
  { id: 'compare',   label: 'Compare',   icon: GitCompare },
  { id: 'runs',      label: 'Runs',      icon: History },
];

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      const ok = await checkApiHealth();
      if (mounted) setIsOnline(ok);
    };
    check();
    const interval = setInterval(check, 10000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-bg-page border-b border-border-base">
      <div className="max-w-5xl mx-auto px-3 sm:px-6 h-14 flex items-center justify-between gap-2 sm:gap-8">

        {/* Brand */}
        <button
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-2.5 shrink-0 hover:opacity-80 transition-opacity"
        >
          <div className="w-7 h-7 rounded bg-accent-dim border border-accent-border flex items-center justify-center">
            <FlaskConical className="w-3.5 h-3.5 text-accent" />
          </div>
          <span className="font-semibold text-[15px] text-text-primary tracking-tight">
            DriftLab
          </span>
          <span className="hidden sm:inline px-1.5 py-0.5 rounded text-2xs font-mono bg-bg-subtle text-text-secondary border border-border-base">
            v0.1
          </span>
        </button>

        {/* Navigation */}
        <nav className="flex items-center gap-1 h-full">
          {navItems.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                aria-label={label}
                aria-current={active ? 'page' : undefined}
                onClick={() => setActiveTab(id)}
                className={`
                  relative flex items-center gap-2 px-3 h-full text-sm font-medium transition-colors
                  ${active
                    ? 'text-text-primary'
                    : 'text-text-secondary hover:text-text-primary'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
                {/* Active underline */}
                {active && (
                  <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-t bg-accent" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-3 shrink-0">
          {/* API status */}
          <div className="hidden md:flex items-center gap-2 text-xs text-text-secondary">
            <span
              className={`w-1.5 h-1.5 rounded-full pulse-dot ${
                isOnline === null ? 'bg-text-muted' :
                isOnline ? 'bg-status-green' : 'bg-status-amber'
              }`}
            />
            <span>
              {isOnline === null ? 'Connecting…' : isOnline ? 'API Online' : 'API Offline'}
            </span>
          </div>

          {/* Run benchmark CTA */}
          <button
            onClick={() => setActiveTab('studio')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent hover:bg-accent-light text-text-inverse text-sm font-medium transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span className="hidden sm:inline">New Run</span>
          </button>
        </div>

      </div>
    </header>
  );
};
