# Production Readiness — Named LLM Eval Tools (Ragas & DeepEval)

## Current state
Both frameworks wired to real local Ollama judges (zero API cost). Found
and fixed a real multi-hour cross-package dependency break (pinned exact
working versions). Found and characterized two distinct failure modes:
Ragas degrades silently (NaN) under judge-model resource contention;
DeepEval crashes loud on unreliable structured-JSON output from a small
judge model. 6 tests, with a documented finding that the 3 slow tests
must run individually, not together, on this hardware.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Pinned exact dependency versions | The only way to get a working install given the ragas/langchain-community break | This version pin will likely need re-verification the next time any of these packages releases a new version — documented explicitly as a maintenance burden, not a one-time fix |
| Different judge models for Ragas (llama3.2:1b) vs. DeepEval (qwen2.5:1.5b) | Each framework's reliability issue was fixed independently as found | Explicitly flagged as NOT a controlled comparison — the judge model itself is a confounding variable between the two frameworks' results |
| `max_workers=2` for Ragas, down from default | Fixed a real timeout/NaN issue caused by CPU resource contention with a local judge model | Slower wall-clock evaluation time than the (broken) default concurrency |

## What's missing for real production use
- **A single, controlled judge-model comparison** — explicitly documented
  as a known limitation: a tighter comparison would hold the judge model
  fixed across both frameworks
- **CI integration** — neither framework's evaluation is wired into an
  automated gate (project 03's pattern exists separately, not connected
  here)
- **Larger evaluation set** — 4 questions proves the frameworks work;
  production evaluation needs a set sized to the actual decision space
- **Cost-optimized judge selection** — no systematic method here for
  choosing which judge model is "good enough" for which metric beyond
  trial-and-error (which is honestly documented, not hidden)

## Scaling considerations
- Ragas' concurrency-tuning finding (`max_workers=2` for a local CPU
  judge) is the key scaling lesson: a cloud-API judge (OpenAI) tolerates
  high concurrency because it's not competing for the same local compute;
  a local judge model needs concurrency matched to its actual serving
  capacity
- At scale, running full framework evaluations (minutes per run) becomes
  a real CI bottleneck — would need the same "skip when unchanged" logic
  as project 03's CI workflow

## Security & compliance considerations
- All evaluation happens against local models — no data leaves the
  machine, a real advantage over a cloud-judge-based evaluation pipeline
  for compliance-sensitive evaluation datasets
- The dependency-pinning finding has a security angle too: pinning old
  package versions means NOT getting security patches those packages'
  newer releases might include — a production maintenance process needs
  to periodically re-verify newer versions rather than pinning forever

## Operational readiness
- No dashboard comparing Ragas vs. DeepEval scores over time — `compare.py`
  prints to console; project 14's dashboard pattern isn't applied here
- The documented test-suite hang (3 slow tests together) is itself an
  operational finding: a CI pipeline running this suite needs to run
  these tests as separate jobs/steps, not one combined invocation
