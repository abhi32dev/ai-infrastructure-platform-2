"""Reusable statistical-significance harness — the same two test families
covering the resume's 'A/B testing & p-value significance testing' bullets
at both Comcast (pipeline dispatch/config variants) and Smith Micro
(recommendation algorithm variants, the 7.4% revenue lift).

Two-proportion z-test: for binary outcomes (converted / didn't, correct /
incorrect) — e.g. recommendation click-through, judge agreement rate.

Welch's t-test: for continuous outcomes (latency, response length) where
the two groups may have different variances — the safer default over
Student's t-test when you can't assume equal variance, which you generally
can't between a small and large model.
"""

from dataclasses import dataclass
import numpy as np
from scipy import stats


@dataclass
class ABResult:
    metric_name: str
    control_n: int
    treatment_n: int
    control_stat: float
    treatment_stat: float
    lift_pct: float
    p_value: float
    significant_at_05: bool
    ci_95: tuple[float, float]
    test_used: str


def two_proportion_z_test(control_successes: int, control_n: int,
                           treatment_successes: int, treatment_n: int,
                           metric_name: str = "conversion_rate") -> ABResult:
    p1 = control_successes / control_n
    p2 = treatment_successes / treatment_n
    p_pool = (control_successes + treatment_successes) / (control_n + treatment_n)

    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / control_n + 1 / treatment_n))
    z = (p2 - p1) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    se_diff = np.sqrt(p1 * (1 - p1) / control_n + p2 * (1 - p2) / treatment_n)
    diff = p2 - p1
    ci_low = diff - 1.96 * se_diff
    ci_high = diff + 1.96 * se_diff

    lift_pct = ((p2 - p1) / p1 * 100) if p1 > 0 else float("nan")

    return ABResult(
        metric_name=metric_name,
        control_n=control_n, treatment_n=treatment_n,
        control_stat=p1, treatment_stat=p2,
        lift_pct=lift_pct, p_value=p_value,
        significant_at_05=bool(p_value < 0.05),
        ci_95=(ci_low, ci_high),
        test_used="two-proportion z-test",
    )


def welch_t_test(control_samples: list[float], treatment_samples: list[float],
                  metric_name: str = "latency_sec") -> ABResult:
    control = np.array(control_samples)
    treatment = np.array(treatment_samples)

    t_stat, p_value = stats.ttest_ind(treatment, control, equal_var=False)

    mean_c, mean_t = control.mean(), treatment.mean()
    diff = mean_t - mean_c
    se_diff = np.sqrt(control.var(ddof=1) / len(control) + treatment.var(ddof=1) / len(treatment))
    ci_low = diff - 1.96 * se_diff
    ci_high = diff + 1.96 * se_diff

    lift_pct = (diff / mean_c * 100) if mean_c != 0 else float("nan")

    return ABResult(
        metric_name=metric_name,
        control_n=len(control), treatment_n=len(treatment),
        control_stat=mean_c, treatment_stat=mean_t,
        lift_pct=lift_pct, p_value=p_value,
        significant_at_05=bool(p_value < 0.05),
        ci_95=(ci_low, ci_high),
        test_used="Welch's t-test (unequal variance)",
    )


def print_result(r: ABResult):
    print(f"\n--- {r.metric_name} ({r.test_used}) ---")
    print(f"control:   n={r.control_n:6d}  stat={r.control_stat:.4f}")
    print(f"treatment: n={r.treatment_n:6d}  stat={r.treatment_stat:.4f}")
    print(f"lift: {r.lift_pct:+.2f}%")
    print(f"95% CI of difference: [{r.ci_95[0]:.5f}, {r.ci_95[1]:.5f}]")
    print(f"p-value: {r.p_value:.5f}  ->  {'SIGNIFICANT' if r.significant_at_05 else 'NOT significant'} at alpha=0.05")
