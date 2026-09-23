import numpy as np
import pytest
from driftlab.stats.core import (
    bootstrap_ci,
    permutation_test,
    naive_mannwhitney_comparator,
    equivalence_check,
    noise_floor,
    holm_correction,
    benjamini_hochberg,
    simulate_power,
)

@pytest.fixture
def rng():
    return np.random.default_rng(42)

def test_bootstrap_ci_coverage(rng):
    """
    Calibration test for bootstrap_ci.
    Checks that nominal coverage is near 95% for alpha=0.05.
    """
    n_sims = 100
    covered = 0
    alpha = 0.05
    true_mean = 0.5
    
    for _ in range(n_sims):
        # Sample normal distribution
        diffs = rng.normal(loc=true_mean, scale=1.0, size=50)
        est, low, high = bootstrap_ci(diffs, n_resamples=200, rng=rng, alpha=alpha)
        
        # Check coverage
        if low <= true_mean <= high:
            covered += 1
            
    coverage_rate = covered / n_sims
    # Tolerance of 0.1 for a small simulation
    assert 0.85 <= coverage_rate <= 1.0

def test_permutation_test_false_positive_rate(rng):
    """
    Calibration test for permutation_test.
    Checks false positive rate on same-distribution data is near alpha=0.05.
    """
    n_sims = 100
    false_positives = 0
    alpha = 0.05
    n_prompts = 5
    
    for _ in range(n_sims):
        baseline = {f"p{i}": rng.normal(0, 1, size=10) for i in range(n_prompts)}
        candidate = {f"p{i}": rng.normal(0, 1, size=10) for i in range(n_prompts)}
        
        p_val = permutation_test(baseline, candidate, n_permutations=200, rng=rng)
        if p_val < alpha:
            false_positives += 1
            
    fpr = false_positives / n_sims
    # Expect around 0.05, give or take binomial noise
    assert fpr <= 0.15

def test_permutation_test_power(rng):
    """
    Calibration test for permutation_test recovering an injected effect.
    """
    n_prompts = 5
    baseline = {f"p{i}": rng.normal(0, 1, size=10) for i in range(n_prompts)}
    # Inject large effect
    candidate = {f"p{i}": rng.normal(2, 1, size=10) for i in range(n_prompts)}
    
    p_val = permutation_test(baseline, candidate, n_permutations=200, rng=rng)
    assert p_val < 0.05

def test_naive_mannwhitney_comparator(rng):
    """
    Tests naive_mannwhitney_comparator to ensure it returns expected metrics on known effect.
    """
    base = rng.normal(0, 1, size=100)
    cand = rng.normal(1, 1, size=100)
    
    res = naive_mannwhitney_comparator(base, cand)
    assert res["p_value"] < 0.05
    assert res["mean_diff"] > 0.5
    assert res["cohens_d"] > 0.5
    assert res["ci_low"] < res["mean_diff"] < res["ci_high"]

def test_equivalence_check():
    """
    Tests the equivalence_check function.
    """
    assert equivalence_check(-0.5, 0.5, 1.0) is True
    assert equivalence_check(-1.5, 0.5, 1.0) is False
    assert equivalence_check(0.1, 0.2, 0.5) is True

def test_noise_floor():
    """
    Tests noise_floor logic.
    """
    diffs = [0.1, -0.2, 0.05, -0.15, 0.3]
    # 95th percentile of abs(diffs) = [0.05, 0.1, 0.15, 0.2, 0.3] -> 95th is ~0.28
    val = noise_floor(diffs, percentile=95)
    assert 0.25 <= val <= 0.3

def test_multiple_testing_corrections():
    """
    Tests holm_correction and benjamini_hochberg.
    """
    p_vals = np.array([0.01, 0.04, 0.1, 0.5])
    
    holm = holm_correction(p_vals)
    assert len(holm) == 4
    assert holm[0] > 0.01
    
    bh = benjamini_hochberg(p_vals)
    assert len(bh) == 4
    assert bh[0] >= 0.01

def test_simulate_power(rng):
    """
    Tests that simulate_power produces expected power curve.
    Large effect size should yield high power.
    """
    # Large effect size
    power_high = simulate_power(
        n_prompts=30, per_prompt_std=1.0, effect_size=1.0, 
        alpha=0.05, n_simulations=100, rng=rng
    )
    assert power_high > 0.8
    
    # Zero effect size
    power_low = simulate_power(
        n_prompts=30, per_prompt_std=1.0, effect_size=0.0, 
        alpha=0.05, n_simulations=100, rng=rng
    )
    assert power_low < 0.2
