import React, { useState } from 'react';
import { FileText, CheckCircle2, Search, Cpu } from 'lucide-react';


interface PromptItem {
  id: string;
  category: 'high_divergence' | 'format_drift' | 'syntax_error' | 'nominal';
  prompt: string;
  cosineSim: number;
  delta: number;
  baselineLatency: string;
  candidateLatency: string;
  baselineOutput: string;
  candidateOutput: string;
  diffSummary: string;
}

const SAMPLE_PROMPTS: PromptItem[] = [
  {
    id: '#PR-042',
    category: 'high_divergence',
    prompt: 'Extract financial metrics from Q3 report into JSON',
    cosineSim: 0.984,
    delta: 0.016,
    baselineLatency: '142ms',
    candidateLatency: '88ms',
    baselineOutput: `{\n  "fiscal_year": 2024,\n  "quarter": "Q3",\n  "revenue_usd": 18400000,\n  "operating_margin": 0.24,\n  "ebitda_growth_yoy": 0.082\n}`,
    candidateOutput: `{\n  "fiscal_year": 2024,\n  "quarter": "Q3",\n  "revenue_usd": 18400000,\n  "operating_margin": 24.0%,\n  "ebitda_growth_yoy": 0.082\n}`,
    diffSummary: 'Numerical formatting variance (0.24 vs 24.0%). Semantic schema equivalence preserved.',
  },
  {
    id: '#PR-089',
    category: 'nominal',
    prompt: 'Synthesize multi-turn RFC dialogue into 3 concise bullet points',
    cosineSim: 0.997,
    delta: 0.003,
    baselineLatency: '210ms',
    candidateLatency: '115ms',
    baselineOutput: `• Propose backward-compatible schema migration via JSONL log append.\n• Defer relational indexing until batch ingestion completes.\n• Require cryptographic hashing for dataset version integrity.`,
    candidateOutput: `• Propose backward-compatible schema migration via JSONL log append.\n• Defer relational indexing until batch ingestion completes.\n• Enforce cryptographic hashing for dataset version integrity.`,
    diffSummary: 'Minor synonym substitution ("Require" vs "Enforce"). Zero structural drift.',
  },
  {
    id: '#PR-017',
    category: 'nominal',
    prompt: 'Generate strict TypeScript type definition for UserProfile record',
    cosineSim: 1.000,
    delta: 0.000,
    baselineLatency: '96ms',
    candidateLatency: '54ms',
    baselineOutput: `export interface UserProfile {\n  readonly id: string;\n  name: string;\n  email: string;\n  role: 'admin' | 'auditor' | 'engineer';\n  createdAt: Date;\n}`,
    candidateOutput: `export interface UserProfile {\n  readonly id: string;\n  name: string;\n  email: string;\n  role: 'admin' | 'auditor' | 'engineer';\n  createdAt: Date;\n}`,
    diffSummary: 'Identical token sequence AST. 100% exact match ratio.',
  },
  {
    id: '#PR-063',
    category: 'high_divergence',
    prompt: 'SQL query optimization for PostgreSQL temporal time-series tables',
    cosineSim: 0.979,
    delta: 0.021,
    baselineLatency: '185ms',
    candidateLatency: '102ms',
    baselineOutput: `SELECT time_bucket('5 minutes', recorded_at) AS five_min,\n       model_id,\n       avg(metric_value) AS avg_drift\nFROM observations\nWHERE recorded_at >= NOW() - INTERVAL '24 hours'\nGROUP BY 1, 2\nORDER BY 1 DESC;`,
    candidateOutput: `SELECT date_trunc('hour', recorded_at) AS hourly_bucket,\n       model_id,\n       avg(metric_value) AS avg_drift\nFROM observations\nWHERE recorded_at >= NOW() - INTERVAL '24 hours'\nGROUP BY 1, 2\nORDER BY 1 DESC;`,
    diffSummary: 'Timescale time_bucket vs vanilla date_trunc syntax variation. Query intent maintained.',
  },
];

export const PromptDiffExplorer: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string>('#PR-042');
  const [filter, setFilter] = useState<'all' | 'high_divergence' | 'format_drift'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPrompts = SAMPLE_PROMPTS.filter((p) => {
    if (filter === 'high_divergence' && p.category !== 'high_divergence') return false;
    if (searchQuery && !p.prompt.toLowerCase().includes(searchQuery.toLowerCase()) && !p.id.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const activePrompt = SAMPLE_PROMPTS.find((p) => p.id === selectedId) || SAMPLE_PROMPTS[0];

  return (
    <div className="telemetry-card p-5 flex flex-col gap-4">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-telemetry-emerald" />
          <h3 className="font-sans font-semibold text-base text-slate-100">
            Prompt Divergence & Output Inspector
          </h3>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
          <button
            onClick={() => setFilter('all')}
            className={`px-2.5 py-1 rounded-[3px] border transition-colors ${
              filter === 'all'
                ? 'bg-telemetry-emerald/15 text-telemetry-emerald border-telemetry-emerald/30 font-semibold'
                : 'bg-surface-low text-slate-400 border-border-subtle hover:text-slate-200'
            }`}
          >
            All Prompts ({SAMPLE_PROMPTS.length})
          </button>
          <button
            onClick={() => setFilter('high_divergence')}
            className={`px-2.5 py-1 rounded-[3px] border transition-colors ${
              filter === 'high_divergence'
                ? 'bg-telemetry-amber/15 text-telemetry-amber border-telemetry-amber/30 font-semibold'
                : 'bg-surface-low text-slate-400 border-border-subtle hover:text-slate-200'
            }`}
          >
            Highest Divergence (2)
          </button>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2 top-2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter prompts..."
              className="bg-surface-low border border-border-subtle text-slate-200 text-[11px] rounded-[3px] pl-7 pr-2.5 py-1 focus:outline-none focus:border-border-focus font-mono"
            />
          </div>
        </div>
      </div>

      {/* Split Grid Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
        {/* Left Suite Table (5 Cols) */}
        <div className="xl:col-span-5 border border-border-subtle rounded-[4px] overflow-hidden bg-surface-lowest">
          <div className="px-3 py-2 border-b border-border-subtle bg-surface-low flex items-center justify-between">
            <span className="font-mono text-[11px] text-slate-400 uppercase font-semibold">
              Prompt Test Suite
            </span>
            <span className="font-mono text-[11px] text-slate-500">
              Showing {filteredPrompts.length} of {SAMPLE_PROMPTS.length}
            </span>
          </div>

          <div className="divide-y divide-border-subtle">
            {filteredPrompts.map((item) => {
              const isSelected = item.id === selectedId;
              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`p-3 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-surface-high/50 border-l-2 border-telemetry-emerald'
                      : 'hover:bg-surface-high/20 border-l-2 border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`font-mono font-semibold text-xs ${isSelected ? 'text-telemetry-emerald' : 'text-slate-300'}`}>
                      {item.id}
                    </span>
                    <span className="px-1.5 py-0.5 rounded-[2px] bg-surface-low border border-border-subtle text-[10px] font-mono text-slate-300">
                      Δ {item.delta.toFixed(3)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-200 line-clamp-1 font-sans">
                    {item.prompt}
                  </p>
                  <div className="flex items-center justify-between mt-2 font-mono text-[10px] text-slate-400">
                    <span>Cosine: {item.cosineSim.toFixed(3)}</span>
                    <span className={isSelected ? 'text-telemetry-emerald flex items-center gap-1 font-semibold' : 'text-slate-500'}>
                      {isSelected ? 'Active Inspect' : 'Inspect Diff'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Split Diff Pane (7 Cols) */}
        <div className="xl:col-span-7 border border-border-subtle rounded-[4px] bg-surface-lowest overflow-hidden flex flex-col">
          {/* Inspection Header */}
          <div className="p-3 bg-surface-low border-b border-border-subtle flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-telemetry-emerald text-xs">
                  INSPECTING {activePrompt.id}
                </span>
                <span className="text-slate-600 text-xs">|</span>
                <span className="font-sans text-xs text-slate-300 font-medium">
                  {activePrompt.prompt}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono mt-0.5 block">
                Cosine Similarity: {activePrompt.cosineSim.toFixed(3)} • Latency: {activePrompt.baselineLatency} vs {activePrompt.candidateLatency}
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px]">
              <span className="px-2 py-0.5 rounded-[2px] bg-surface-high text-slate-200 border border-border-subtle">
                Δ {activePrompt.delta.toFixed(3)}
              </span>
            </div>
          </div>

          {/* Side-by-side Code/Text Diff Container */}
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border-subtle text-xs font-mono p-3 gap-3">
            {/* Baseline Model Output */}
            <div className="flex flex-col gap-1 p-2.5 bg-surface-low/60 rounded-[3px] border border-border-subtle/40">
              <div className="flex items-center justify-between pb-1.5 border-b border-border-subtle text-telemetry-indigo font-semibold">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" />
                  FP16 Baseline
                </span>
                <span className="text-[10px] text-slate-400">{activePrompt.baselineLatency}</span>
              </div>
              <pre className="mt-2 text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono text-[11px]">
                {activePrompt.baselineOutput}
              </pre>
            </div>

            {/* Candidate Model Output */}
            <div className="flex flex-col gap-1 p-2.5 bg-surface-low/60 rounded-[3px] border border-border-subtle/40">
              <div className="flex items-center justify-between pb-1.5 border-b border-border-subtle text-telemetry-violet font-semibold">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" />
                  Q4_K_M Quantized
                </span>
                <span className="text-[10px] text-telemetry-emerald font-semibold">
                  {activePrompt.candidateLatency} (faster)
                </span>
              </div>
              <pre className="mt-2 text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono text-[11px]">
                {activePrompt.candidateOutput}
              </pre>
            </div>
          </div>

          {/* Diff Footnote */}
          <div className="px-4 py-2 bg-surface-low border-t border-border-subtle flex items-center justify-between text-[11px] text-slate-300 font-mono">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-telemetry-emerald" />
              <span>{activePrompt.diffSummary}</span>
            </span>
            <span className="text-slate-500">AST Validated</span>
          </div>
        </div>
      </div>
    </div>
  );
};
