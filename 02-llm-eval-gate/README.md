# 02 — Multi-Model LLM-as-Judge Evaluation Gate

An automation decision only executes if TWO independent models both approve
it: a generator proposes APPROVE/REJECT, and a second, differently-sized,
differently-trained judge model reviews the same situation independently
(it never sees the generator's rationale, to avoid anchoring) and issues
its own verdict. The action only runs if both agree to approve.

## Maps to resume claims
- "Multi-Model Evaluation Gate" (CONDOR): routes every AI-generated decision
  through a second, independent model before it's allowed to act
- "Multi-Model AI Output Evaluation": LLM-as-judge pattern used both in
  production automation review and personal AI/ML practice

## Setup (isolated venv)

```bash
cd 02-llm-eval-gate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:1b     # generator
ollama pull qwen2.5:1.5b    # judge — deliberately a different model family/size
```

## Run it

```bash
source .venv/bin/activate
cd src
python gate.py          # runs all 6 scenarios, prints agreement rate
python generator.py     # generator's raw decisions in isolation
python judge.py         # judge's raw verdicts in isolation
```

Every decision — generator output, judge output, final gate verdict,
execution result — is appended to `logs/audit.jsonl`, one JSON line per
decision, so every gate decision has a reproducible record (same spirit as
the resume's MLflow version-tracking bullet; project 03 adds MLflow proper).

## Tests

```bash
cd 02-llm-eval-gate && source .venv/bin/activate && pytest -q
```

8 tests, in four categories:
- **Positive/negative gate logic (4):** judge-rejects-blocks, generator-rejects-blocks, both-approve-executes, both-reject-blocks — all deterministic, mocked models, no flakiness
- **Fail-safe on malformed output (2):** generator returns unparsable JSON → fails safe to REJECT; judge returns unparsable JSON → fails safe to REJECT (two independent code paths, tested separately)
- **Regression guard (1):** every gate decision is appended to the audit log exactly once, with the correct scenario ID
- **Live integration (1):** against the real local models, the one scenario that's consistently unambiguous (destructive action with no backup → both models reliably reject)

## Results on the fixed evaluation set (6 scenarios)

5/6 gate decisions agree with the human-labeled expected outcome. The one
mismatch: the **rollback-a-degrading-deployment** scenario. The judge model
(qwen2.5:1.5b) correctly approves it, but the generator model
(llama3.2:1b) itself rejects it, over-weighting "this is a production
change" without registering that a rollback to a known-good prior version
is the standard, reversible response to active degradation. Because the
gate requires both models to approve, this scenario gets blocked even
though it shouldn't be.

## What to say in an interview

- **Why require both to approve instead of averaging/voting?** An AND-gate
  is intentionally conservative — the cost of a false REJECT (an engineer
  has to manually approve one extra time) is much lower than the cost of a
  false APPROVE (a bad automated action reaches production). This mirrors
  the real tradeoff in the CONDOR gate: a single model's blind spot should
  never be sufficient to authorize a production action alone.
- **The rollback false-reject is not a bug I'm hiding — it's the finding.**
  It's a concrete demonstration of exactly why an AND-gate over independent
  models is safer than trusting either one alone: even though the judge
  got it right, the generator's mistake was still caught by the gate's
  conservative default (BLOCK), not silently allowed through. In
  production this is the kind of case you'd route to a human reviewer and
  track as a **false-reject rate** metric — too high a false-reject rate
  means the gate is over-blocking and creating manual-approval fatigue,
  which is exactly the kind of concurrency/failure-rate telemetry the
  CONDOR platform tracks to tune thresholds.
- **Why judge the situation independently instead of "does the generator's
  rationale sound right"?** Reviewing the generator's stated rationale
  invites the judge to rubber-stamp confident-sounding but wrong reasoning
  (anchoring bias). Reviewing the raw situation independently forces a
  second, uncorrelated pass at the same facts — closer to how a human
  second-reviewer actually works.
- **Why two different model families (llama vs qwen), not two calls to the
  same model?** Two calls to the same model share the same blind spots and
  training biases — that doesn't catch anything a single call wouldn't
  already miss. Independence has to come from a genuinely different model.
- **Known limitation to volunteer:** the evaluation set is only 6
  hand-written scenarios — enough to demonstrate the mechanism, not enough
  to certify accuracy. Project 03 adds MLflow tracking so this evaluation
  set and its pass rate become versioned artifacts you can compare across
  prompt/model changes over time, and a CI gate that blocks a merge if the
  pass rate regresses.
