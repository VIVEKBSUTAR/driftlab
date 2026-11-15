import React, { useEffect, useState } from 'react';
import { Search, Eye, RefreshCw, Plus } from 'lucide-react';
import { RunRecord } from '../../types/api';
import { fetchRuns } from '../../services/api';
import { RunDetailModal } from './RunDetailModal';

interface RunsListProps {
  onNavigateToStudio: () => void;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export const RunsList: React.FC<RunsListProps> = ({ onNavigateToStudio }) => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setRuns(await fetchRuns());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load runs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = runs.filter((r) => {
    const q = search.toLowerCase();
    const matchSearch =
      r.id.toLowerCase().includes(q) ||
      (r.model_identifier?.toLowerCase().includes(q) ?? false);
    const matchType = filterType === 'all' || r.run_type === filterType;
    return matchSearch && matchType;
  });

  return (
    <div className="space-y-6">

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary tracking-tight mb-1">Run History</h1>
          <p className="text-sm text-text-secondary">
            All recorded benchmark runs. Click a row to inspect its details.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 bg-bg-card hover:bg-bg-elevated text-text-secondary border border-border-base rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNavigateToStudio}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-accent hover:bg-accent-light text-text-inverse text-sm font-medium rounded transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Run
          </button>
        </div>
      </div>

      {/* Search + filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search by run ID or model name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-card border border-border-base rounded px-3 py-2 pl-9 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-border-focus"
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-bg-card border border-border-base rounded">
          {['all', 'baseline', 'candidate'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors capitalize ${
                filterType === t
                  ? 'bg-bg-elevated text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <p role="alert" className="p-4 rounded-lg border border-status-red/30 text-status-red">{error}</p>}
      {/* Table */}
      <div className="bg-bg-card border border-border-base rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-bg-elevated rounded animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-secondary">No runs found.</p>
            <p className="text-xs text-text-muted mt-1">Try a different search or create a new run.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-border-base text-xs text-text-muted uppercase tracking-wide">
                  <th className="px-5 py-3 font-medium">Run ID</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Model</th>
                  <th className="px-5 py-3 font-medium text-right">Observations</th>
                  <th className="px-5 py-3 font-medium">Created</th>
                  <th className="px-5 py-3 font-medium text-center">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted">
                {filtered.map((r) => (
                  <tr
                    key={r.id}
                    className="hover:bg-bg-elevated transition-colors cursor-pointer"
                    onClick={() => setSelectedRunId(r.id)}
                  >
                    <td className="px-5 py-3 font-mono text-text-primary font-medium">{r.id}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-2xs font-medium uppercase ${
                        r.run_type === 'baseline'
                          ? 'bg-status-blueDim text-status-blue'
                          : 'bg-status-purpleDim text-status-purple'
                      }`}>
                        {r.run_type}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-text-secondary">{r.model_identifier ?? '—'}</td>
                    <td className="px-5 py-3 text-right font-mono text-text-primary">{r.observations_count}</td>
                    <td className="px-5 py-3 text-text-muted text-xs">
                      {r.created_at ? formatDate(r.created_at) : '—'}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedRunId(r.id); }}
                        className="p-1.5 rounded hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors"
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <RunDetailModal runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
    </div>
  );
};
