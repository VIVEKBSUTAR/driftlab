import React, { useState } from 'react';
import { PlayCircle, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import { triggerRun } from '../../services/api';
import { TriggerRunRequest } from '../../types/api';

interface RunStudioProps {
  onRunCreated: (runId: string) => void;
}

const AVAILABLE_METRICS = [
  { id: 'exact_match',          name: 'Exact Match',        desc: 'Checks if the output text matches exactly (normalized)' },
  { id: 'embedding_similarity', name: 'Semantic Similarity', desc: 'Measures meaning similarity using sentence embeddings' },
  { id: 'sequence_similarity',  name: 'Character Similarity', desc: 'Character-level SequenceMatcher ratio' },
  { id: 'json_validity',        name: 'JSON Validity',       desc: 'Checks whether the output is valid, parseable JSON' },
];

export const RunStudio: React.FC<RunStudioProps> = ({ onRunCreated }) => {
  const [model, setModel]                   = useState<string>('mock');
  const [runType, setRunType]               = useState<'baseline' | 'candidate'>('baseline');
  const [repeats, setRepeats]               = useState<number>(5);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['exact_match', 'sequence_similarity']);
  const [loading, setLoading]               = useState(false);
  const [successRunId, setSuccessRunId]     = useState<string | null>(null);
  const [errorMsg, setErrorMsg]             = useState<string | null>(null);

  const toggleMetric = (id: string) =>
    setSelectedMetrics((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedMetrics.length === 0) {
      setErrorMsg('Select at least one evaluation metric.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const payload: TriggerRunRequest = { model, run_type: runType, repeats, metrics: selectedMetrics };
      const res = await triggerRun(payload);
      setSuccessRunId(res.run_id);
    } catch (err: any) {
      setErrorMsg(err?.message ?? 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text-primary tracking-tight mb-1">New Benchmark Run</h1>
        <p className="text-sm text-text-secondary">
          Configure and record a benchmark run. Run your baseline first, then your modified model as a candidate.
        </p>
      </div>

      {/* Success */}
      {successRunId && (
        <div className="flex items-center justify-between gap-4 p-4 rounded-lg bg-status-greenDim border border-status-green/25">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-status-green shrink-0" />
            <div>
              <p className="text-sm font-semibold text-status-green">Run recorded successfully</p>
              <p className="text-xs text-text-secondary font-mono mt-0.5">ID: {successRunId}</p>
            </div>
          </div>
          <button
            onClick={() => onRunCreated(successRunId)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent hover:bg-accent-light text-text-inverse text-sm font-medium transition-colors shrink-0"
          >
            Compare <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-status-redDim border border-status-red/25">
          <AlertCircle className="w-5 h-5 text-status-red shrink-0" />
          <p className="text-sm text-status-red">{errorMsg}</p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-bg-card border border-border-base rounded-lg divide-y divide-border-muted">

        {/* Model backend */}
        <div className="p-5">
          <label className="block text-sm font-semibold text-text-primary mb-3">Model backend</label>
          <div className="grid grid-cols-2 gap-3">
            <ToggleCard
              active={model === 'mock'}
              onClick={() => setModel('mock')}
              title="Mock (Demo)"
              description="Generates synthetic data — no GPU needed"
            />
            <ToggleCard
              active={model === 'llama3:8b'}
              onClick={() => setModel('llama3:8b')}
              title="Ollama (Local)"
              description="Runs llama3:8b via localhost:11434"
            />
          </div>
        </div>

        {/* Run type */}
        <div className="p-5">
          <label className="block text-sm font-semibold text-text-primary mb-1">Run type</label>
          <p className="text-xs text-text-muted mb-3">
            Baseline = your original model. Candidate = the modified/compressed version.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <ToggleCard
              active={runType === 'baseline'}
              onClick={() => setRunType('baseline')}
              title="Baseline"
              description="The original, unmodified model"
              color="blue"
            />
            <ToggleCard
              active={runType === 'candidate'}
              onClick={() => setRunType('candidate')}
              title="Candidate"
              description="The modified or compressed model"
              color="purple"
            />
          </div>
        </div>

        {/* Repeats */}
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <label className="text-sm font-semibold text-text-primary">Repeats per prompt</label>
              <p className="text-xs text-text-muted mt-0.5">
                Each prompt is run this many times to measure natural variance.
              </p>
            </div>
            <span className="text-lg font-semibold text-text-primary font-mono w-8 text-right">{repeats}</span>
          </div>
          <input
            type="range" min="2" max="10" step="1"
            value={repeats}
            onChange={(e) => setRepeats(parseInt(e.target.value, 10))}
            className="w-full accent-accent cursor-pointer"
          />
          <div className="flex justify-between text-xs text-text-muted mt-1">
            <span>2 – Fast</span>
            <span>3 – Minimum (medium risk)</span>
            <span>5 – More repeats</span>
            <span>10 – More sampling</span>
          </div>
        </div>

        {/* Metrics */}
        <div className="p-5">
          <label className="block text-sm font-semibold text-text-primary mb-1">Evaluation metrics</label>
          <p className="text-xs text-text-muted mb-3">Select which quality metrics to compute for each output.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {AVAILABLE_METRICS.map((m) => {
              const active = selectedMetrics.includes(m.id);
              return (
                <label
                  key={m.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    active
                      ? 'bg-accent-dim border-accent-border'
                      : 'bg-bg-page border-border-base hover:border-border-focus'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => toggleMetric(m.id)}
                    className="mt-0.5 accent-accent cursor-pointer"
                  />
                  <div>
                    <p className="text-sm font-medium text-text-primary">{m.name}</p>
                    <p className="text-xs text-text-secondary mt-0.5">{m.desc}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Submit */}
        <div className="p-5 flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-light text-text-inverse text-sm font-medium rounded transition-colors disabled:opacity-50"
          >
            <PlayCircle className="w-4 h-4" />
            {loading ? 'Running…' : 'Start Benchmark'}
          </button>
        </div>
      </form>
    </div>
  );
};

// ─── Helper ──────────────────────────────────────────────────────────────────

function ToggleCard({
  active, onClick, title, description, color = 'green',
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  description: string;
  color?: 'green' | 'blue' | 'purple';
}) {
  const activeClass = {
    green:  'bg-accent-dim border-accent-border',
    blue:   'bg-status-blueDim border-status-blue/30',
    purple: 'bg-status-purpleDim border-status-purple/30',
  }[color];

  return (
    <button
      type="button"
      onClick={onClick}
      className={`p-3 rounded-lg border text-left transition-colors ${
        active ? activeClass : 'bg-bg-page border-border-base hover:border-border-focus'
      }`}
    >
      <p className="text-sm font-semibold text-text-primary">{title}</p>
      <p className="text-xs text-text-secondary mt-0.5">{description}</p>
    </button>
  );
}
