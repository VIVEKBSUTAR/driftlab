export type Task = {
    id: string;
    task_key: string;
    category: string;
    risk_level: string;
    prompt: string;
    expected_output?: string;
    output_spec?: Record<string, unknown>;
};
export type Policy = {
    risk_level: string;
    margin: number;
    alpha: number;
    min_prompts: number;
    min_repeats: number;
};
export type Run = {
    id: string;
    run_type: string;
    status: string;
    model_identifier: string;
    model_digest?: string;
    created_at: string;
    observations_count: number;
    expected_observations: number;
    synthetic: boolean;
    error?: string;
    dataset_digest?: string;
};
export type Observation = {
    task_id: string;
    task_key: string;
    prompt: string;
    reference: string;
    category: string;
    risk_level: string;
    repeat_index: number;
    raw_output: string;
    finish_reason?:string|null;
    prompt_tokens?:number|null;
    completion_tokens?:number|null;
    latency_ms: number;
    error?: string;
    scores: Record<string, number>;
};
export type Detail = Run & {
    model: {
        identifier: string;
        family: string;
        digest: string;
    };
    observations: Observation[];
    observations_total: number;
    aggregates: {task_id:string;metric_name:string;mean_value:number;std_value:number|null;repeats_count:number}[];
};
export type Verdict = {
    category: string;
    metric_id: string;
    risk_level: string;
    status: string;
    estimate: number;
    ci_low: number;
    ci_high: number;
    p_value: number;
    p_adjusted: number;
    noise_floor: number;
    margin: number;
    explanation: string;
    details: {
        n_prompts: number;
        n_repeats: number;
        confidence_level: number;
        alpha: number;
        noise_source: string;
    };
};
export type Comparison = {
    id: string;
    baseline_run_id: string;
    candidate_run_id: string;
    recommendation: string;
    created_at: string;
    verdicts: Verdict[];
    config: Record<string, unknown>;
    baseline: Run;
    candidate: Run;
};
export type DatasetChoice = { id: string; name: string; tasks: Task[]; description: string; source?: Record<string,unknown> };
export type Catalog = {
    version:string;
    datasets?: DatasetChoice[];
    tasks: Task[];
    policies: Policy[];
    metrics: string[];
    dataset_name: string;
    dataset_description: string;
};

export type RunRecord = Run;
export type RunDetail = Detail;
export type WorkspaceSummary = {runs:number; models:number; observations:number; comparisons:number; alerts:number; statuses:Record<string,number>; worker_running:boolean; version:string};
