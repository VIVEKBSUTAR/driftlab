import numpy as np
import scipy.stats
from typing import Dict, Tuple, List

def bootstrap_ci(differences: np.ndarray, n_resamples: int, rng: np.random.Generator, alpha: float = 0.05) -> Tuple[float, float, float]:
    """Calculates point estimate, lower bound, and upper bound using the BCa method, clustered by prompt."""
    point_estimate = float(np.mean(differences))
    if len(differences) < 2:
        return point_estimate, point_estimate, point_estimate
    
    res = scipy.stats.bootstrap(
        (differences,), 
        np.mean, 
        n_resamples=n_resamples, 
        random_state=rng, 
        method='BCa', 
        confidence_level=1.0 - alpha
    )
    return point_estimate, float(res.confidence_interval.low), float(res.confidence_interval.high)

def permutation_test(baseline: Dict[str, np.ndarray], candidate: Dict[str, np.ndarray], n_permutations: int, rng: np.random.Generator) -> float:
    """Returns a two-sided p-value from within-prompt label permutation given prompt IDs mapped to per-repeat metric values."""
    prompt_ids = list(baseline.keys())
    if not prompt_ids:
        return 1.0

    # Compute observed stat
    def get_diff(b_dict, c_dict):
        return np.mean([np.mean(c_dict[pid]) - np.mean(b_dict[pid]) for pid in prompt_ids])
        
    obs_stat = get_diff(baseline, candidate)
    
    pooled = {}
    n_b = {}
    for pid in prompt_ids:
        pooled[pid] = np.concatenate([baseline[pid], candidate[pid]])
        n_b[pid] = len(baseline[pid])
        
    count_extreme = 0
    for _ in range(n_permutations):
        b_perm = {}
        c_perm = {}
        for pid in prompt_ids:
            perm = rng.permutation(pooled[pid])
            b_perm[pid] = perm[:n_b[pid]]
            c_perm[pid] = perm[n_b[pid]:]
        
        perm_stat = get_diff(b_perm, c_perm)
        if abs(perm_stat) >= abs(obs_stat):
            count_extreme += 1
            
    return count_extreme / max(1, n_permutations)

def naive_mannwhitney_comparator(baseline_run_scores: np.ndarray, candidate_run_scores: np.ndarray) -> dict:
    """
    Intentionally naive baseline comparator (as used by agent-eval). 
    Implements scipy.stats.mannwhitneyu + Cohen's d + bootstrap CI on run-level means,
    without prompt clustering or equivalence checks.
    """
    if len(baseline_run_scores) == 0 or len(candidate_run_scores) == 0:
        return {"p_value": 1.0, "cohens_d": 0.0, "ci_low": 0.0, "ci_high": 0.0, "mean_diff": 0.0}

    # Mann-Whitney U
    _, p_value = scipy.stats.mannwhitneyu(candidate_run_scores, baseline_run_scores, alternative='two-sided')
    
    # Cohen's d
    n1, n2 = len(candidate_run_scores), len(baseline_run_scores)
    var1, var2 = np.var(candidate_run_scores, ddof=1), np.var(baseline_run_scores, ddof=1)
    pooled_sd = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    mean_diff = np.mean(candidate_run_scores) - np.mean(baseline_run_scores)
    cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else 0.0
    
    # Bootstrap CI on the difference of means
    # For independent samples, we bootstrap the difference directly.
    rng = np.random.default_rng(42) # fixed for naive determinism if not passed
    
    def mean_diff_func(x, y):
        return np.mean(x) - np.mean(y)
    
    # scipy.stats.bootstrap handles 2-sample cases if we pass (cand, base) and a paired statistic
    res = scipy.stats.bootstrap((candidate_run_scores, baseline_run_scores), mean_diff_func, n_resamples=1000, random_state=rng, method='percentile')
    
    return {
        "p_value": float(p_value),
        "cohens_d": float(cohens_d),
        "ci_low": float(res.confidence_interval.low),
        "ci_high": float(res.confidence_interval.high),
        "mean_diff": float(mean_diff)
    }

def equivalence_check(ci_low: float, ci_high: float, margin: float) -> bool:
    """Returns True only if the entire confidence interval lies within the plus/minus margin."""
    return ci_low >= -margin and ci_high <= margin

def noise_floor(same_model_comparisons: List[float], percentile: float = 95) -> float:
    """Calculates the noise floor based on a percentile of differences from same-model comparisons."""
    if not same_model_comparisons:
        return 0.0
    return float(np.percentile(np.abs(same_model_comparisons), percentile))

def holm_correction(p_values: np.ndarray) -> np.ndarray:
    """Applies the Holm step-down method to correct p-values for multiple testing."""
    # implemented via statsmodels
    from statsmodels.stats.multitest import multipletests
    if len(p_values) == 0:
        return np.array([])
    _, pvals_corrected, _, _ = multipletests(p_values, method='holm')
    return pvals_corrected

def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """Applies the Benjamini-Hochberg procedure to control the false discovery rate."""
    from statsmodels.stats.multitest import multipletests
    if len(p_values) == 0:
        return np.array([])
    _, pvals_corrected, _, _ = multipletests(p_values, method='fdr_bh')
    return pvals_corrected

def simulate_power(n_prompts: int, per_prompt_std: float, effect_size: float, alpha: float, n_simulations: int, rng: np.random.Generator) -> float:
    """Simulates statistical power for a given effect size and sample size."""
    # Assuming paired t-test logic for power simulation of difference of means
    rejections = 0
    for _ in range(n_simulations):
        # Simulate differences directly: normally distributed around effect_size with given std
        diffs = rng.normal(loc=effect_size, scale=per_prompt_std, size=n_prompts)
        _, p_val = scipy.stats.ttest_1samp(diffs, popmean=0)
        if p_val < alpha:
            rejections += 1
    return rejections / n_simulations
