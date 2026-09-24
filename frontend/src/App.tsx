import { useState } from 'react';
import { Header } from './components/common/Header';
import { Overview } from './components/dashboard/Overview';
import { CompareView } from './components/comparison/CompareView';
import { PromptDiffExplorer } from './components/explorer/PromptDiffExplorer';
import { RunsList } from './components/runs/RunsList';
import { RunStudio } from './components/studio/RunStudio';
import { PoliciesView } from './components/policies/PoliciesView';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('comparison');

  return (
    <div className="min-h-screen bg-surface-lowest text-slate-200 flex flex-col font-sans selection:bg-telemetry-emerald selection:text-surface-lowest">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'comparison' && (
          <CompareView onOpenExplorer={() => setActiveTab('explorer')} />
        )}
        {activeTab === 'explorer' && <PromptDiffExplorer />}
        {activeTab === 'dashboard' && <Overview onNavigate={setActiveTab} />}
        {activeTab === 'runs' && <RunsList onNavigateToStudio={() => setActiveTab('studio')} />}
        {activeTab === 'studio' && (
          <RunStudio
            onRunCreated={(_runId) => {
              setActiveTab('comparison');
            }}
          />
        )}
        {activeTab === 'policies' && <PoliciesView />}
      </main>

      {/* STATUS FOOTER BAR */}
      <footer className="h-8 bg-surface-lowest border-t border-border-subtle px-6 flex items-center justify-between font-mono text-[11px] text-slate-500">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-telemetry-emerald animate-pulse"></span>
            <span className="text-slate-400">DAEMON: RUNNING</span>
          </span>
          <span className="hidden sm:inline">CLUSTER: local-inference-01</span>
          <span className="hidden md:inline">RUNTIME: llama.cpp / ollama</span>
        </div>
        <div className="flex items-center gap-4">
          <span>TOST BCa N=10k</span>
          <span className="hidden sm:inline">UTF-8</span>
          <span className="text-slate-300 font-medium">DriftLab Statistical Observability</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
