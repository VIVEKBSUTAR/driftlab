import React, { useEffect, useState } from 'react';
import { Search, Eye, Filter, RefreshCw, Layers, Plus } from 'lucide-react';
import { RunRecord } from '../../types/api';
import { fetchRuns } from '../../services/api';
import { RunDetailModal } from './RunDetailModal';
import { Skeleton } from '../common/Skeleton';

interface RunsListProps {
  onNavigateToStudio: () => void;
}

export const RunsList: React.FC<RunsListProps> = ({ onNavigateToStudio }) => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchRuns();
      setRuns(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredRuns = runs.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(search.toLowerCase()) ||
      (r.model_identifier && r.model_identifier.toLowerCase().includes(search.toLowerCase()));
    const matchesType = filterType === 'all' || r.run_type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Experiment Runs Explorer</h1>
          <p className="text-xs text-slate-400 mt-1">
            Browse and inspect recorded benchmark runs, model snapshot digests, and observation counts.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            className="p-2 bg-surface-card hover:bg-surface-hover text-slate-300 border border-surface-border rounded-lg transition-colors cursor-pointer"
            title="Refresh runs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNavigateToStudio}
            className="flex items-center space-x-2 px-3.5 py-2 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-lg shadow-sm shadow-brand-500/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Benchmark Run</span>
          </button>
        </div>
      </div>

      {/* Filter and Search controls */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search run ID or model..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface-base border border-surface-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 font-mono"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-400 font-mono">Type:</span>
          {['all', 'baseline', 'candidate'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                filterType === t
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-surface-hover'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-lg shadow-black/20">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : filteredRuns.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-surface-elevated text-slate-400 border-b border-surface-border uppercase text-[11px] tracking-wider">
                <tr>
                  <th className="px-4 py-3">Run ID</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Model Snapshot</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Observations</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border bg-surface-base/40">
                {filteredRuns.map((r) => (
                  <tr key={r.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-3 font-semibold text-white">{r.id}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded border text-[10px] uppercase font-bold ${
                          r.run_type === 'baseline'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                        }`}
                      >
                        {r.run_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300 font-sans font-medium">{r.model_identifier || 'Unknown'}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-slate-200">{r.observations_count}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setSelectedRunId(r.id)}
                        className="p-1.5 bg-surface-elevated hover:bg-brand-600 hover:text-white text-slate-400 rounded-lg transition-colors cursor-pointer"
                        title="View run snapshot and aggregates"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-300">No matching runs found</p>
            <p className="text-xs text-slate-500 mt-0.5">Try adjusting your search criteria or launch a new run.</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <RunDetailModal runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
    </div>
  );
};
