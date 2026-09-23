export type DriftStatus =
  | 'insufficient_data'
  | 'high_risk_regression'
  | 'meaningful_drift'
  | 'statistically_detected_low_impact'
  | 'no_meaningful_drift'
  | 'insufficient_evidence';

export type RiskTier = 'low' | 'medium' | 'high' | 'critical';

export interface DriftVerdict {
  category: string;
  metric_id: string;
  risk_level: RiskTier;
  status: DriftStatus;
  estimate: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  p_adjusted: number;
  noise_floor: number;
  margin: number;
  explanation: string;
}

export interface PromptAggregateItem {
  task_id: string;
  metric_name: string;
  mean_value: number;
  std_value: number | null;
  repeats_count: number;
}

export interface RunRecord {
  id: string;
  run_type: 'baseline' | 'candidate';
  status: string;
  model_identifier: string | null;
  jsonl_path: string | null;
  created_at: string | null;
  observations_count: number;
}

export interface RunDetail extends RunRecord {
  model: {
    identifier: string | null;
    family: string | null;
    digest: string | null;
  };
  aggregates: PromptAggregateItem[];
}

export interface CompareRequest {
  baseline_run_id: string;
  candidate_run_id: string;
  noise_floor?: number;
  seed?: number;
}

export interface CompareResponse {
  baseline_run_id: string;
  candidate_run_id: string;
  verdicts: DriftVerdict[];
}

export interface TriggerRunRequest {
  model: string;
  run_type: 'baseline' | 'candidate';
  repeats: number;
  metrics: string[];
  tasks?: Array<{
    id?: string;
    task_key: string;
    category: string;
    risk_level: RiskTier;
    prompt: string;
    expected_output?: string;
  }>;
}

export interface RiskPolicyConfig {
  name: string;
  risk_level: RiskTier;
  margin: number;
  alpha: number;
  min_prompts: number;
  min_repeats: number;
  harmful_direction: 'negative' | 'positive';
}
