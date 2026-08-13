"""Synthetic large-scale A/B test, deliberately modeled on the resume's
Smith Micro story: 'Ran controlled A/B tests comparing recommendation
algorithm variants, using p-value significance testing to confirm the
7.4% revenue lift was a statistically real effect and not normal
variance.' This generates synthetic binomial trial data at a realistic
subscriber-platform scale (50K users/arm) with a true underlying 7.4%
relative lift baked in, then recovers that lift through the same
two-proportion z-test a real experimentation platform would run.
"""

import numpy as np
from stats_harness import two_proportion_z_test, print_result

RNG_SEED = 42
CONTROL_N = 50_000
TREATMENT_N = 50_000
CONTROL_TRUE_RATE = 0.082      # baseline recommendation click/convert rate
TRUE_RELATIVE_LIFT = 0.074     # the resume's 7.4% figure, baked into the simulation


def run_experiment():
    rng = np.random.default_rng(RNG_SEED)
    treatment_true_rate = CONTROL_TRUE_RATE * (1 + TRUE_RELATIVE_LIFT)

    control_successes = int(rng.binomial(CONTROL_N, CONTROL_TRUE_RATE))
    treatment_successes = int(rng.binomial(TREATMENT_N, treatment_true_rate))

    result = two_proportion_z_test(
        control_successes, CONTROL_N,
        treatment_successes, TREATMENT_N,
        metric_name="recommendation_conversion_rate",
    )
    print_result(result)
    print(f"\nTrue underlying relative lift baked into the simulation: {TRUE_RELATIVE_LIFT*100:.1f}%")
    print(f"Recovered/measured relative lift from the sample: {result.lift_pct:.2f}%")
    return result


if __name__ == "__main__":
    run_experiment()
