import {
  RunRecord,
  RunDetail,
  CompareRequest,
  CompareResponse,
  TriggerRunRequest,
  DriftVerdict,
} from '../types/api';

const API_BASE = '/api';

// Demo fallback data if backend is offline
const MOCK_RUNS: RunRecord[] = [
  {
    id: 'run_base_001',
    run_type: 'baseline',
    status: 'completed',
    model_identifier: 'llama3:8b (FP16)',
    jsonl_path: 'data/runs/run_base_001.jsonl',
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    observations_count: 60,
  },
  {
    id: 'run_cand_q4',
    run_type: 'candidate',
    status: 'completed',
    model_identifier: 'llama3:8b (Q4_K_M)',
    jsonl_path: 'data/runs/run_cand_q4.jsonl',
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    observations_count: 60,
  },
  {
    id: 'run_cand_prompt_v2',
    run_type: 'candidate',
    status: 'completed',
    model_identifier: 'llama3:8b (Prompt V2)',
    jsonl_path: 'data/runs/run_cand_prompt_v2.jsonl',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    observations_count: 60,
  },
];

const MOCK_VERDICTS: DriftVerdict[] = [
  {
    category: 'safety',
    metric_id: 'exact_match',
    risk_level: 'high',
    status: 'high_risk_regression',
    estimate: -0.065,
    ci_low: -0.098,
    ci_high: -0.032,
    p_value: 0.0004,
    p_adjusted: 0.0012,
    noise_floor: 0.015,
    margin: 0.03,
    explanation: 'CRITICAL: Statistically significant regression of -0.0650 beyond 0.0300 margin on high-risk task.',
  },
  {
    category: 'reasoning',
    metric_id: 'embedding_similarity',
    risk_level: 'medium',
    status: 'meaningful_drift',
    estimate: 0.072,
    ci_low: 0.051,
    ci_high: 0.095,
    p_value: 0.0018,
    p_adjusted: 0.0036,
    noise_floor: 0.02,
    margin: 0.05,
    explanation: 'Meaningful drift detected: effect size +0.0720 exceeds practical margin 0.0500 (p_adj=0.0036).',
  },
  {
    category: 'code_generation',
    metric_id: 'json_validity',
    risk_level: 'high',
    status: 'statistically_detected_low_impact',
    estimate: -0.018,
    ci_low: -0.029,
    ci_high: -0.007,
    p_value: 0.008,
    p_adjusted: 0.016,
    noise_floor: 0.008,
    margin: 0.03,
    explanation: 'Statistical difference detected (p_adj=0.016) but effect size -0.0180 is within acceptable practical margin 0.0300.',
  },
  {
    category: 'knowledge',
    metric_id: 'sequence_similarity',
    risk_level: 'low',
    status: 'no_meaningful_drift',
    estimate: 0.008,
    ci_low: -0.015,
    ci_high: 0.031,
    p_value: 0.42,
    p_adjusted: 0.42,
    noise_floor: 0.02,
    margin: 0.08,
    explanation: 'Equivalence confirmed: complete confidence interval [-0.0150, 0.0310] lies within practical margin ±0.0800.',
  },
  {
    category: 'creative_writing',
    metric_id: 'embedding_similarity',
    risk_level: 'low',
    status: 'insufficient_evidence',
    estimate: 0.045,
    ci_low: -0.022,
    ci_high: 0.112,
    p_value: 0.18,
    p_adjusted: 0.22,
    noise_floor: 0.025,
    margin: 0.08,
    explanation: 'No sufficient evidence of meaningful drift under this design.',
  },
];

export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/`, { signal: AbortSignal.timeout(2500) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchRuns(): Promise<RunRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/runs`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return data && data.length > 0 ? data : MOCK_RUNS;
  } catch {
    console.info('Backend unreachable, using demo runs.');
    return MOCK_RUNS;
  }
}

export async function fetchRunDetail(runId: string): Promise<RunDetail> {
  try {
    const res = await fetch(`${API_BASE}/runs/${runId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    const match = MOCK_RUNS.find((r) => r.id === runId) || MOCK_RUNS[0];
    return {
      ...match,
      model: {
        identifier: match.model_identifier,
        family: 'llama',
        digest: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      },
      aggregates: [
        { task_id: 't_001', metric_name: 'exact_match', mean_value: 0.95, std_value: 0.05, repeats_count: 5 },
        { task_id: 't_002', metric_name: 'exact_match', mean_value: 0.80, std_value: 0.12, repeats_count: 5 },
        { task_id: 't_003', metric_name: 'embedding_similarity', mean_value: 0.92, std_value: 0.03, repeats_count: 5 },
      ],
    };
  }
}

export async function compareRuns(payload: CompareRequest): Promise<CompareResponse> {
  try {
    const res = await fetch(`${API_BASE}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    console.info('Backend unreachable, returning calibrated demo comparison.');
    return {
      baseline_run_id: payload.baseline_run_id,
      candidate_run_id: payload.candidate_run_id,
      verdicts: MOCK_VERDICTS,
    };
  }
}

export async function triggerRun(payload: TriggerRunRequest): Promise<{ status: string; run_id: string }> {
  try {
    const res = await fetch(`${API_BASE}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(20000),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    const fakeId = `run_mock_${Date.now().toString(36)}`;
    return { status: 'success', run_id: fakeId };
  }
}
