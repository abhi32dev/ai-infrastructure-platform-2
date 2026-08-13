# 07 — A/B Testing & p-Value Significance Harness

A reusable statistical-significance library (`stats_harness.py`, two
tests: two-proportion z-test for binary outcomes, Welch's t-test for
continuous outcomes) plus two concrete experiments — one synthetic at
realistic scale, one live against real local models.

## Maps to resume claims
- "Statistically Validated Rollouts" (Comcast): controlled A/B tests on
  pipeline dispatch/config variants, p-value significance testing before
  rolling out platform-wide
- "Statistically Validated Recommendation Variants" (Smith Micro): A/B
  tests confirming the 7.4% revenue lift was real, not normal variance

## Setup (isolated venv)

```bash
cd 07-ab-testing-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b   # for the live latency experiment
ollama pull qwen2.5:3b
```

## Run it

```bash
source .venv/bin/activate
cd src

python experiment_recommender.py   # synthetic, 50K users/arm, Smith Micro-style
python experiment_latency.py       # live, real Ollama calls, small vs large model
```

## Results — two very different lessons from the same harness

### Experiment A: synthetic recommendation A/B (n=50,000/arm)
A true 7.4% relative lift (matching the resume's Smith Micro figure) is
baked into the simulation via `numpy.random.binomial`. The z-test recovers
it correctly:

| | control | treatment |
|---|---|---|
| conversion rate | 7.98% | 8.73% |
| **measured lift** | | **+9.43%** |
| 95% CI of difference | [0.0041, 0.0110] | (excludes zero) |
| p-value | | **0.00002 — significant** |

At 50K users/arm, a 7.4%-scale lift is easily distinguishable from chance
— this is what justifies rolling a change out platform-wide with
confidence, the exact decision the resume bullet describes.

### Experiment B: live latency A/B (n=8/arm, real Ollama calls)
Small model (`llama3.2:1b`) vs large model (`qwen2.5:3b`) response
latency on 8 short prompts each:

| | control (small) | treatment (large) |
|---|---|---|
| mean latency | 0.72s | 1.13s |
| **measured lift** | | **+56.2%** |
| 95% CI of difference | | **[-0.735, 1.547] — includes zero** |
| p-value | | **0.499 — NOT significant** |

A 56% apparent slowdown, and the test correctly says **don't trust it** —
at n=8, one cold-start outlier per model (2.77s and 3.57s vs a normal
~0.2-0.3s) dominates the small sample, and the wide confidence interval
spans zero. This is not a bug in the harness; it's the harness doing its
job. Rerunning with a larger, warmed-up sample would very likely show a
real, smaller, significant difference — but *this* sample doesn't support
claiming one.

## Tests

```bash
cd 07-ab-testing-harness && source .venv/bin/activate && pytest -q
```
9 tests, in three categories:
- **Positive/negative significance calls (4):** identical-proportions-not-significant, large-clear-lift-is-significant, Welch's-test-detects-a-clear-difference, Welch's-test correctly stays silent on a noisy small sample (the exact shape of Experiment B's real result, verified with fixed numbers so this specific test has no LLM dependency)
- **Negative / edge cases (4):** a negative lift (treatment WORSE than control) is correctly detected as significant, not just "different"; swapping control/treatment flips the lift's sign but not the p-value (symmetry guard against mislabeling which variant is better); zero-variance identical samples produce a `nan` p-value that correctly evaluates as NOT significant rather than crashing or false-claiming an effect; a 0%-vs-0% conversion edge case doesn't crash on a 0/0 division
- **Live integration (1):** the seeded recommender experiment recovers its baked-in ~7.4% lift

## What to say in an interview

- **Why two different test families instead of one generic test?** A
  proportion (converted/didn't, correct/incorrect) and a continuous
  measurement (latency) have different variance structures — a
  two-proportion z-test assumes a binomial distribution, a t-test assumes
  (approximately) normal, continuous data. Using the wrong test for the
  data type is a real, common mistake; keeping them as two explicit
  functions makes the choice visible rather than implicit.
- **Why Welch's t-test, not Student's?** Welch's doesn't assume equal
  variance between groups. Two different-sized models will very plausibly
  have different latency variance (confirmed here — the large model's
  latencies are both slower on average AND more volatile), so assuming
  equal variance would understate the uncertainty and could produce a
  false positive.
- **Experiment B is the more valuable interview story than Experiment A.**
  Anyone can show a test that finds significance on a big, obvious effect.
  Showing a test correctly *declining* to call a 56%-looking difference
  real, and explaining why (n=8, cold-start variance, CI spans zero) — and
  proposing the fix (warm the models first, increase n, or use paired
  differences per-prompt) — demonstrates the actual judgment a p-value
  process exists to enforce.
- **Known limitation to volunteer:** Experiment A's "true lift" is known
  because I baked it into the simulation myself — real A/B tests never
  get that ground truth, only the sample. Its purpose here is narrowly to
  prove the z-test's recovered lift and significance call line up with a
  known-correct answer, i.e. that the harness itself is implemented
  correctly, not to claim a real recommendation system was tested.
