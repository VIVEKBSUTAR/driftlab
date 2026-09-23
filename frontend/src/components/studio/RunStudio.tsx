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
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Benchmark Execution Studio</h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure and execute prompt benchmark sweeps across local model adapters. Observations are logged immediately to append-only JSONL files.
        </p>
      </div>

      {successRunId && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <span className="font-bold text-sm block">Run Triggered & Logged Successfully!</span>
              <span className="text-xs font-mono text-emerald-400/80">Run ID: {successRunId}</span>
            </div>
          </div>
          <button
            onClick={() => onRunCreated(successRunId)}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-bold rounded-lg transition-colors cursor-pointer"
          >
            <span>Analyze Drift</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center space-x-3 text-xs">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-surface-card border border-surface-border rounded-xl p-6 space-y-6 shadow-xl shadow-black/20">
        {/* Model and Run Type */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 uppercase mb-2">
              Model Adapter Backend
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setModel('mock')}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                  model === 'mock'
                    ? 'bg-brand-500/15 border-brand-500 text-white shadow-sm'
                    : 'bg-surface-base border-surface-border text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs font-mono">Mock Adapter</span>
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                </div>
                <p className="text-[11px] text-slate-500">Distribution sampler (No GPU needed)</p>
              </button>

              <button
                type="button"
                onClick={() => setModel('llama3:8b')}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                  model !== 'mock'
                    ? 'bg-brand-500/15 border-brand-500 text-white shadow-sm'
                    : 'bg-surface-base border-surface-border text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs font-mono">Ollama Local</span>
                  <Cpu className="w-3.5 h-3.5 text-brand-400" />
                </div>
                <p className="text-[11px] text-slate-500">llama3:8b via localhost:11434</p>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-medium text-slate-400 uppercase mb-2">
              Run Role & Classification
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRunType('baseline')}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                  runType === 'baseline'
                    ? 'bg-blue-500/15 border-blue-500 text-white shadow-sm'
                    : 'bg-surface-base border-surface-border text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold text-xs font-mono block">Baseline (Control)</span>
                <p className="text-[11px] text-slate-500 mt-1">Reference benchmark state</p>
              </button>

              <button
                type="button"
                onClick={() => setRunType('candidate')}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                  runType === 'candidate'
                    ? 'bg-purple-500/15 border-purple-500 text-white shadow-sm'
                    : 'bg-surface-base border-surface-border text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold text-xs font-mono block">Candidate (Treatment)</span>
                <p className="text-[11px] text-slate-500 mt-1">Updated weights or prompt state</p>
              </button>
            </div>
          </div>
        </div>

        {/* Repetitions per prompt */}
        <div className="pt-4 border-t border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-mono font-medium text-slate-400 uppercase flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-brand-400" />
              Repeats per Prompt ($k$): <span className="text-white font-bold font-mono">{repeats} repeats</span>
            </label>
            <span className="text-[11px] text-slate-500 font-mono">Within-prompt noise estimation</span>
          </div>
          <input
            type="range"
            min="2"
            max="10"
            step="1"
            value={repeats}
            onChange={(e) => setRepeats(parseInt(e.target.value, 10))}
            className="w-full h-2 bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-brand-500"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
            <span>2 (Fast)</span>
            <span>3 (Standard Default)</span>
            <span>5 (Recommended for High Risk)</span>
            <span>10 (Exhaustive)</span>
          </div>
        </div>

        {/* Evaluation Metrics Checklist */}
        <div className="pt-4 border-t border-surface-border">
          <label className="block text-xs font-mono font-medium text-slate-400 uppercase mb-3">
            Evaluation Metrics to Compute
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {availableMetrics.map((m) => {
              const active = selectedMetrics.includes(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => toggleMetric(m.id)}
                  className={`p-3 rounded-lg border flex items-start space-x-3 cursor-pointer transition-all ${
                    active
                      ? 'bg-brand-500/10 border-brand-500/40 text-slate-200'
                      : 'bg-surface-base border-surface-border text-slate-500 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => {}}
                    className="mt-0.5 rounded border-slate-700 text-brand-600 focus:ring-brand-500"
                  />
                  <div>
                    <span className="text-xs font-mono font-bold text-white block">{m.name}</span>
                    <span className="text-[11px] text-slate-400 leading-tight block mt-0.5">{m.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-5 border-t border-surface-border flex items-center justify-end">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-2 px-6 py-2.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-brand-500/25 disabled:opacity-50 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Running Benchmark...</span>
              </>
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
