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
    <div className="space-y-5">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-border-subtle">
        <div>
          <h1 className="text-xl font-bold font-sans text-slate-100 tracking-tight">Experiment Runs Explorer</h1>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Browse and inspect recorded benchmark runs, cryptographic model snapshot digests, and prompt observations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="p-1.5 bg-surface-low hover:bg-surface-high text-slate-300 border border-border-subtle rounded-[4px] transition-colors cursor-pointer"
            title="Refresh runs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNavigateToStudio}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest text-xs font-mono font-semibold rounded-[4px] shadow-sm transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Benchmark Run</span>
          </button>
        </div>
      </div>

      {/* Filter and Search controls */}
      <div className="bg-surface-low border border-border-subtle rounded-[4px] p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
          <input
            type="text"
            placeholder="Search run ID or model..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface-lowest border border-border-subtle rounded-[3px] pl-8 pr-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-border-focus font-mono"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto font-mono text-xs">
          <Filter className="w-3 h-3 text-slate-400" />
          <span className="text-slate-400 text-[11px]">Type:</span>
          {['all', 'baseline', 'candidate'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-2 py-0.5 rounded-[2px] text-[11px] font-mono transition-colors ${
                filterType === t
                  ? 'bg-telemetry-emerald/15 text-telemetry-emerald border border-telemetry-emerald/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 border border-transparent hover:bg-surface-high'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-surface-low border border-border-subtle rounded-[4px] overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : filteredRuns.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-surface-high/60 text-slate-400 border-b border-border-subtle uppercase text-[10px] tracking-wider font-semibold">
                <tr>
                  <th className="px-4 py-2.5">Run ID</th>
                  <th className="px-4 py-2.5">Type</th>
                  <th className="px-4 py-2.5">Model Snapshot</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Observations</th>
                  <th className="px-4 py-2.5">Created</th>
                  <th className="px-4 py-2.5 text-center">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle bg-surface-lowest">
                {filteredRuns.map((r) => (
                  <tr key={r.id} className="hover:bg-surface-high/20 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-200">{r.id}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-block px-1.5 py-0.2 rounded-[2px] border text-[10px] uppercase font-bold ${
                          r.run_type === 'baseline'
                            ? 'bg-telemetry-indigo/15 text-telemetry-indigoLight border-telemetry-indigo/30'
                            : 'bg-telemetry-violet/15 text-telemetry-violetLight border-telemetry-violet/30'
                        }`}
                      >
                        {r.run_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-300 font-sans font-medium">{r.model_identifier || 'Unknown'}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center gap-1.5 text-telemetry-emerald text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-telemetry-emerald" />
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-bold text-slate-200">{r.observations_count}</td>
                    <td className="px-4 py-2.5 text-slate-500 text-[11px]">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <button
                        onClick={() => setSelectedRunId(r.id)}
                        className="p-1 bg-surface-low hover:bg-surface-high hover:text-telemetry-emerald text-slate-400 rounded-[3px] border border-border-subtle transition-colors cursor-pointer"
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
          <div className="p-8 text-center">
            <Layers className="w-6 h-6 text-slate-600 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-300 font-mono">No matching runs found</p>
            <p className="text-[11px] text-slate-500 mt-0.5 font-sans">Try adjusting your search criteria or launch a new run.</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <RunDetailModal runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
    </div>
  );
};
