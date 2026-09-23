import React, { useEffect, useState } from 'react';
import { X, Cpu, FileText, Database, Layers } from 'lucide-react';
import { RunDetail } from '../../types/api';
import { fetchRunDetail } from '../../services/api';
import { Skeleton } from '../common/Skeleton';

interface RunDetailModalProps {
  runId: string | null;
  onClose: () => void;
}

export const RunDetailModal: React.FC<RunDetailModalProps> = ({ runId, onClose }) => {
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    const load = async () => {
      try {
        const data = await fetchRunDetail(runId);
        setDetail(data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [runId]);

  if (!runId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-card border border-surface-border rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Modal Header */}
        <div className="p-5 border-b border-surface-border flex items-center justify-between bg-surface-elevated/40">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold font-mono text-white">{runId}</h3>
                {detail && (
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                      detail.run_type === 'baseline'
                        ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                        : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                    }`}
                  >
                    {detail.run_type}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">Run Snapshot & Prompt Aggregates</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-surface-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : detail ? (
            <>
              {/* Metadata Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 bg-surface-base rounded-lg border border-surface-border">
                  <span className="text-slate-500 block mb-1 text-[10px] uppercase flex items-center gap-1">
                    <Cpu className="w-3 h-3 text-brand-400" /> Model Identifier
                  </span>
                  <span className="text-slate-200 font-semibold">{detail.model.identifier || 'N/A'}</span>
                  <span className="text-[10px] text-slate-500 block truncate mt-1">
                    Digest: {detail.model.digest || 'N/A'}
                  </span>
                </div>

                <div className="p-3 bg-surface-base rounded-lg border border-surface-border">
                  <span className="text-slate-500 block mb-1 text-[10px] uppercase flex items-center gap-1">
                    <FileText className="w-3 h-3 text-emerald-400" /> Source of Truth
                  </span>
                  <span className="text-slate-200 truncate block font-mono text-[11px]">{detail.jsonl_path || 'N/A'}</span>
                  <span className="text-[10px] text-emerald-400 block mt-1">
                    {detail.observations_count} Observations Recorded
                  </span>
                </div>
              </div>

              {/* Prompt Aggregates Table */}
              <div>
                <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-brand-400" />
                  Prompt-Level Aggregates (Repeats Clustered)
                </h4>
                {detail.aggregates && detail.aggregates.length > 0 ? (
                  <div className="overflow-x-auto rounded-lg border border-surface-border">
                    <table className="w-full text-xs font-mono text-left">
                      <thead className="bg-surface-elevated/60 text-slate-400 border-b border-surface-border text-[11px]">
                        <tr>
                          <th className="px-3 py-2">Task ID</th>
                          <th className="px-3 py-2">Metric</th>
                          <th className="px-3 py-2">Mean Score</th>
                          <th className="px-3 py-2">Std Dev</th>
                          <th className="px-3 py-2 text-right">Repeats</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border bg-surface-base/60">
                        {detail.aggregates.map((agg, idx) => (
                          <tr key={idx} className="hover:bg-surface-hover/50">
                            <td className="px-3 py-2 text-slate-300 font-semibold">{agg.task_id}</td>
                            <td className="px-3 py-2 text-brand-400">{agg.metric_name}</td>
                            <td className="px-3 py-2 text-white font-bold">{agg.mean_value.toFixed(4)}</td>
                            <td className="px-3 py-2 text-slate-400">{agg.std_value !== null ? agg.std_value.toFixed(4) : '0.0000'}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{agg.repeats_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 font-mono py-2">No prompt aggregates recorded.</p>
                )}
              </div>
            </>
          ) : (
            <p className="text-xs text-rose-400">Failed to load run details.</p>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-surface-border bg-surface-elevated/30 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-surface-elevated hover:bg-surface-hover text-slate-300 text-xs font-semibold rounded-lg border border-surface-border transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
