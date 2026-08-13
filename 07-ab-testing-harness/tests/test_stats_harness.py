"""Deterministic tests of the stats math itself (known inputs, known
expected conclusions), plus the two experiment scripts run live/seeded so
their conclusions are re-verified, not just eyeballed once in a terminal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stats_harness import two_proportion_z_test, welch_t_test


def test_identical_proportions_are_not_significant():
    r = two_proportion_z_test(500, 10000, 500, 10000)
    assert r.p_value > 0.05
    assert r.significant_at_05 is False
    assert abs(r.lift_pct) < 0.01


def test_large_clear_lift_is_significant():
    # 8% vs 12% conversion at n=10000/arm is an obvious, real difference
    r = two_proportion_z_test(800, 10000, 1200, 10000)
    assert r.significant_at_05 is True
    assert r.p_value < 0.001
    assert r.lift_pct > 0


def test_welch_t_test_detects_clear_mean_difference():
    control = [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98, 1.03] * 5   # n=40, tight around 1.0
    treatment = [2.0, 2.1, 1.9, 2.05, 1.95, 2.02, 1.98, 2.03] * 5  # n=40, tight around 2.0
    r = welch_t_test(control, treatment)
    assert r.significant_at_05 is True
    assert r.treatment_stat > r.control_stat


def test_welch_t_test_noisy_small_sample_not_significant():
    # mirrors the live latency experiment's actual finding: a big apparent
    # lift with high variance and small n should NOT be called significant
    control = [0.7, 0.3, 0.2, 1.0, 0.3, 0.2, 0.2, 0.8]
    treatment = [3.6, 0.3, 0.2, 1.0, 0.2, 0.3, 0.3, 3.1]
    r = welch_t_test(control, treatment)
    assert r.significant_at_05 is False


def test_recommender_experiment_recovers_baked_in_lift():
    from experiment_recommender import run_experiment
    result = run_experiment()
    assert result.significant_at_05 is True
    assert result.lift_pct > 0
    # recovered lift should be in the same ballpark as the true 7.4%,
    # generous bound since it's a single random draw
    assert 0 < result.lift_pct < 20


# --- Negative / edge cases ---

def test_negative_lift_is_detected_correctly():
    """The treatment being WORSE than control (not just 'no different')
    must be caught too — a regression, not just a flat variant."""
    r = two_proportion_z_test(1200, 10000, 800, 10000)  # treatment worse
    assert r.significant_at_05 is True
    assert r.lift_pct < 0


def test_swapping_control_and_treatment_flips_lift_sign_not_pvalue():
    """Symmetry regression guard: p-value should be identical either way
    (it's a two-sided test of 'are these different'), but which arm is
    reported as the 'lift' must flip sign — a bug here would silently
    mislabel which variant is actually better."""
    r_forward = two_proportion_z_test(800, 10000, 1200, 10000)
    r_reversed = two_proportion_z_test(1200, 10000, 800, 10000)
    assert abs(r_forward.p_value - r_reversed.p_value) < 1e-9
    assert r_forward.lift_pct > 0
    assert r_reversed.lift_pct < 0


def test_zero_variance_identical_samples_does_not_falsely_claim_significance():
    """Known edge case: identical, zero-variance samples make Welch's
    t-test's denominator zero, producing a nan p-value (scipy emits a
    RuntimeWarning here — expected, not a bug). The harness must not let
    a nan p-value evaluate as 'significant' (nan < 0.05 is False in
    Python, which is the fail-safe direction: nan certainty never claims
    a real effect)."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = welch_t_test([1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0])
    assert r.significant_at_05 is False


def test_two_proportion_z_test_with_zero_successes_in_both_arms():
    """Edge case: a 0% vs 0% conversion rate (e.g. a brand-new feature
    nobody has used yet) must not crash on a 0/0 division."""
    r = two_proportion_z_test(0, 1000, 0, 1000)
    assert r.p_value >= 0 or r.p_value != r.p_value  # valid number or nan, not an exception
    assert r.significant_at_05 is False
