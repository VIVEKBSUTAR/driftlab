import React, { useState } from 'react';
import { PlayCircle, CheckCircle, Cpu, Sliders, Sparkles, AlertCircle, ArrowRight } from 'lucide-react';
import { triggerRun } from '../../services/api';
import { TriggerRunRequest } from '../../types/api';

interface RunStudioProps {
  onRunCreated: (runId: string) => void;
}

export const RunStudio: React.FC<RunStudioProps> = ({ onRunCreated }) => {
  const [model, setModel] = useState<string>('mock');
  const [runType, setRunType] = useState<'baseline' | 'candidate'>('baseline');
  const [repeats, setRepeats] = useState<number>(3);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'exact_match',
    'embedding_similarity',
  ]);
  const [loading, setLoading] = useState(false);
  const [successRunId, setSuccessRunId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const availableMetrics = [
    { id: 'exact_match', name: 'Exact Match', desc: 'Normalized string equality (0.0 or 1.0)' },
    { id: 'embedding_similarity', name: 'Embedding Cosine Sim', desc: 'Sentence-Transformers all-MiniLM-L6-v2' },
    { id: 'sequence_similarity', name: 'Sequence Similarity', desc: 'Character-level edit distance ratio' },
    { id: 'json_validity', name: 'JSON Format Validity', desc: 'Validates parseable JSON structure and keys' },
  ];

  const toggleMetric = (mId: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(mId) ? prev.filter((id) => id !== mId) : [...prev, mId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedMetrics.length === 0) {
      setErrorMsg('Please select at least one evaluation metric.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    try {
      const payload: TriggerRunRequest = {
        model,
        run_type: runType,
        repeats,
        metrics: selectedMetrics,
      };
      const res = await triggerRun(payload);
      setSuccessRunId(res.run_id);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to trigger run.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="pb-3 border-b border-border-subtle">
        <h1 className="text-xl font-bold font-sans text-slate-100 tracking-tight">Benchmark Execution Studio</h1>
        <p className="text-xs text-slate-400 mt-0.5 font-sans">
          Configure and execute prompt benchmark sweeps across local model adapters. Observations are logged immediately to append-only JSONL files.
        </p>
      </div>

      {successRunId && (
        <div className="p-3.5 rounded-[4px] bg-telemetry-emerald/10 border border-telemetry-emerald/30 text-telemetry-emerald flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-4 h-4 text-telemetry-emerald shrink-0" />
            <div>
              <span className="font-semibold text-xs font-mono block">Run Triggered & Logged Successfully!</span>
              <span className="text-[11px] font-mono text-telemetry-emeraldLight">Run ID: {successRunId}</span>
            </div>
          </div>
          <button
            onClick={() => onRunCreated(successRunId)}
            className="flex items-center gap-1.5 px-3 py-1 bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest text-xs font-mono font-semibold rounded-[3px] transition-colors cursor-pointer"
          >
            <span>Analyze Drift</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-[4px] bg-telemetry-rose/10 border border-telemetry-rose/30 text-telemetry-roseLight flex items-center gap-2.5 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-telemetry-rose shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-surface-low border border-border-subtle rounded-[4px] p-5 space-y-5">
        {/* Model and Run Type */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-[11px] font-mono font-semibold text-slate-400 uppercase mb-2">
              Model Adapter Backend
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setModel('mock')}
                className={`p-2.5 rounded-[3px] border text-left transition-colors cursor-pointer ${
                  model === 'mock'
                    ? 'bg-telemetry-emerald/10 border-telemetry-emerald text-slate-100'
                    : 'bg-surface-lowest border-border-subtle text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs font-mono">Mock Adapter</span>
                  <Sparkles className="w-3 h-3 text-telemetry-emerald" />
                </div>
                <p className="text-[10px] text-slate-500 font-sans">Distribution sampler (No GPU needed)</p>
              </button>

              <button
                type="button"
                onClick={() => setModel('llama3:8b')}
                className={`p-2.5 rounded-[3px] border text-left transition-colors cursor-pointer ${
                  model !== 'mock'
                    ? 'bg-telemetry-emerald/10 border-telemetry-emerald text-slate-100'
                    : 'bg-surface-lowest border-border-subtle text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs font-mono">Ollama Local</span>
                  <Cpu className="w-3 h-3 text-telemetry-emerald" />
                </div>
                <p className="text-[10px] text-slate-500 font-sans">llama3:8b via localhost:11434</p>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono font-semibold text-slate-400 uppercase mb-2">
              Run Role & Classification
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRunType('baseline')}
                className={`p-2.5 rounded-[3px] border text-left transition-colors cursor-pointer ${
                  runType === 'baseline'
                    ? 'bg-telemetry-indigo/15 border-telemetry-indigo text-slate-100'
                    : 'bg-surface-lowest border-border-subtle text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold text-xs font-mono block">Baseline (Control)</span>
                <p className="text-[10px] text-slate-500 font-sans mt-0.5">Reference benchmark state</p>
              </button>

              <button
                type="button"
                onClick={() => setRunType('candidate')}
                className={`p-2.5 rounded-[3px] border text-left transition-colors cursor-pointer ${
                  runType === 'candidate'
                    ? 'bg-telemetry-violet/15 border-telemetry-violet text-slate-100'
                    : 'bg-surface-lowest border-border-subtle text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold text-xs font-mono block">Candidate (Treatment)</span>
                <p className="text-[10px] text-slate-500 font-sans mt-0.5">Updated weights or prompt state</p>
              </button>
            </div>
          </div>
        </div>

        {/* Repetitions per prompt */}
        <div className="pt-3 border-t border-border-subtle">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-[11px] font-mono font-semibold text-slate-400 uppercase flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-telemetry-emerald" />
              Repeats per Prompt ($k$): <span className="text-slate-100 font-bold font-mono">{repeats} repeats</span>
            </label>
            <span className="text-[10px] text-slate-500 font-mono">Within-prompt noise estimation</span>
          </div>
          <input
            type="range"
            min="2"
            max="10"
            step="1"
            value={repeats}
            onChange={(e) => setRepeats(parseInt(e.target.value, 10))}
            className="w-full accent-telemetry-emerald cursor-pointer"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
            <span>2 (Fast)</span>
            <span>3 (Standard Default)</span>
            <span>5 (Recommended for High Risk)</span>
            <span>10 (Exhaustive)</span>
          </div>
        </div>

        {/* Evaluation Metrics Checklist */}
        <div className="pt-3 border-t border-border-subtle">
          <label className="block text-[11px] font-mono font-semibold text-slate-400 uppercase mb-2">
            Evaluation Metrics to Compute
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {availableMetrics.map((m) => {
              const active = selectedMetrics.includes(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => toggleMetric(m.id)}
                  className={`p-2.5 rounded-[3px] border flex items-start gap-2.5 cursor-pointer transition-colors ${
                    active
                      ? 'bg-telemetry-emerald/10 border-telemetry-emerald/40 text-slate-200'
                      : 'bg-surface-lowest border-border-subtle text-slate-500 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => {}}
                    className="mt-0.5 rounded-[2px] border-slate-700 text-telemetry-emerald focus:ring-0"
                  />
                  <div>
                    <span className="text-xs font-mono font-semibold text-slate-200 block">{m.name}</span>
                    <span className="text-[10px] text-slate-400 font-sans block mt-0.5">{m.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4 border-t border-border-subtle flex items-center justify-end">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 bg-telemetry-emerald hover:bg-telemetry-emeraldLight text-surface-lowest text-xs font-mono font-semibold rounded-[4px] shadow-sm disabled:opacity-50 transition-colors cursor-pointer"
          >
            {loading ? (
              <span>Running Benchmark Sweep...</span>
            ) : (
              <>
                <PlayCircle className="w-4 h-4" />
                <span>Launch Benchmark Sweep</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
