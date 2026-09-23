import { useState } from 'react';
import { Header } from './components/common/Header';
import { Overview } from './components/dashboard/Overview';
import { CompareView } from './components/comparison/CompareView';
import { RunsList } from './components/runs/RunsList';
import { RunStudio } from './components/studio/RunStudio';
import { PoliciesView } from './components/policies/PoliciesView';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  return (
    <div className="min-h-screen bg-surface-base text-slate-100 flex flex-col font-sans">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <Overview onNavigate={setActiveTab} />}
        {activeTab === 'comparison' && <CompareView />}
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

      <footer className="border-t border-surface-border py-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>DriftLab &copy; 2026 — Statistical Behavioral Drift Detection Framework</span>
          <span className="text-slate-400">REST API: http://localhost:8000</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
