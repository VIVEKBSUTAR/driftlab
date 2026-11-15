import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { RunDetail } from '../../types/api';
import { fetchRunDetail } from '../../services/api';

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
    setDetail(null);
    fetchRunDetail(runId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [runId]);

  if (!runId) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-bg-card border border-border-base rounded-lg w-full max-w-xl max-h-[80vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-base">
          <div>
            <h3 className="text-sm font-semibold text-text-primary font-mono">{runId}</h3>
            {detail && (
              <p className="text-xs text-text-secondary mt-0.5 capitalize">{detail.run_type} run</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-5">
          {loading ? (
            <div className="space-y-3">
              <div className="h-12 bg-bg-elevated rounded animate-pulse" />
              <div className="h-32 bg-bg-elevated rounded animate-pulse" />
            </div>
          ) : detail ? (
            <>
              {/* Model info */}
              <div className="grid grid-cols-2 gap-3">
                <InfoField label="Model" value={detail.model.identifier ?? '—'} />
                <InfoField label="Observations" value={String(detail.observations_count)} />
                <InfoField label="Family" value={detail.model.family ?? '—'} />
                <InfoField label="Data file" value={detail.jsonl_path ?? '—'} mono truncate />
              </div>

              {/* Aggregates table */}
              {detail.aggregates && detail.aggregates.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                    Score Aggregates
                  </h4>
                  <div className="rounded-lg border border-border-base overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border-base text-xs text-text-muted uppercase tracking-wide">
                          <th className="px-4 py-2.5 font-medium text-left">Task</th>
                          <th className="px-4 py-2.5 font-medium text-left">Metric</th>
                          <th className="px-4 py-2.5 font-medium text-right">Mean</th>
                          <th className="px-4 py-2.5 font-medium text-right">Std</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-muted bg-bg-page">
                        {detail.aggregates.map((agg, i) => (
                          <tr key={i} className="hover:bg-bg-elevated transition-colors">
                            <td className="px-4 py-2.5 font-mono text-text-primary text-xs">{agg.task_id}</td>
                            <td className="px-4 py-2.5 text-text-secondary text-xs">{agg.metric_name}</td>
                            <td className="px-4 py-2.5 text-right font-mono font-semibold text-text-primary text-xs">
                              {agg.mean_value.toFixed(4)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono text-text-muted text-xs">
                              {agg.std_value?.toFixed(4) ?? '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-status-red">Could not load run details.</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border-base flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-bg-elevated hover:bg-bg-hover text-text-primary border border-border-base text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

function InfoField({
  label, value, mono, truncate,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
}) {
  return (
    <div className="bg-bg-page border border-border-base rounded px-3 py-2">
      <p className="text-2xs text-text-muted uppercase tracking-wide mb-0.5">{label}</p>
      <p className={`text-sm text-text-primary ${mono ? 'font-mono' : 'font-medium'} ${truncate ? 'truncate' : ''}`}>
        {value || '—'}
      </p>
    </div>
  );
}
