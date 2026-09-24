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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-surface-low border border-border-subtle rounded-[4px] w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Modal Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-surface-high/30">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[3px] bg-telemetry-emerald/10 border border-telemetry-emerald/30 flex items-center justify-center text-telemetry-emerald">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold font-mono text-slate-100">{runId}</h3>
                {detail && (
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.2 rounded-[2px] border ${
                      detail.run_type === 'baseline'
                        ? 'bg-telemetry-indigo/15 text-telemetry-indigoLight border-telemetry-indigo/30'
                        : 'bg-telemetry-violet/15 text-telemetry-violetLight border-telemetry-violet/30'
                    }`}
                  >
                    {detail.run_type}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">Run Snapshot & Prompt Aggregates</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-[3px] hover:bg-surface-high transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4">
          {loading ? (
            <div className="space-y-2.5">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : detail ? (
            <>
              {/* Metadata Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs font-mono">
                <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                  <span className="text-slate-500 block mb-1 text-[10px] uppercase flex items-center gap-1">
                    <Cpu className="w-3 h-3 text-telemetry-emerald" /> Model Identifier
                  </span>
                  <span className="text-slate-200 font-semibold">{detail.model.identifier || 'N/A'}</span>
                  <span className="text-[10px] text-slate-500 block truncate mt-1">
                    Digest: {detail.model.digest || 'N/A'}
                  </span>
                </div>

                <div className="p-2.5 bg-surface-lowest rounded-[3px] border border-border-subtle">
                  <span className="text-slate-500 block mb-1 text-[10px] uppercase flex items-center gap-1">
                    <FileText className="w-3 h-3 text-telemetry-emerald" /> Source of Truth
                  </span>
                  <span className="text-slate-200 truncate block font-mono text-[11px]">{detail.jsonl_path || 'N/A'}</span>
                  <span className="text-[10px] text-telemetry-emerald block mt-1">
                    {detail.observations_count} Observations Recorded
                  </span>
                </div>
              </div>

              {/* Prompt Aggregates Table */}
              <div>
                <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-telemetry-emerald" />
                  Prompt-Level Aggregates (Repeats Clustered)
                </h4>
                {detail.aggregates && detail.aggregates.length > 0 ? (
                  <div className="overflow-x-auto rounded-[3px] border border-border-subtle">
                    <table className="w-full text-xs font-mono text-left">
                      <thead className="bg-surface-high/50 text-slate-400 border-b border-border-subtle text-[10px] uppercase font-semibold">
                        <tr>
                          <th className="px-3 py-2">Task ID</th>
                          <th className="px-3 py-2">Metric</th>
                          <th className="px-3 py-2">Mean Score</th>
                          <th className="px-3 py-2">Std Dev</th>
                          <th className="px-3 py-2 text-right">Repeats</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle bg-surface-lowest">
                        {detail.aggregates.map((agg, idx) => (
                          <tr key={idx} className="hover:bg-surface-high/20">
                            <td className="px-3 py-2 text-slate-300 font-semibold">{agg.task_id}</td>
                            <td className="px-3 py-2 text-telemetry-emerald">{agg.metric_name}</td>
                            <td className="px-3 py-2 text-slate-100 font-bold">{agg.mean_value.toFixed(4)}</td>
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
            <p className="text-xs text-telemetry-rose">Failed to load run details.</p>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-border-subtle bg-surface-high/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-3.5 py-1 bg-surface-high hover:bg-surface-highest text-slate-300 text-xs font-mono font-semibold rounded-[3px] border border-border-subtle transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
