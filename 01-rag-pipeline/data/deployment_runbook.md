# Runbook: Promoting a Change to Production

## Pre-checks
1. Confirm the change passed the CI regression gate (unit tests + evaluation
   harness for any AI-assisted logic).
2. Confirm the change has at least one CODEOWNERS approval on the pull
   request.
3. Confirm no active incident is open for the target service.

## Promotion sequence
Changes are promoted through four environments in order: Dev, QA, Stage,
Prod. A change must sit in Stage for at least one full traffic cycle with no
new alarms attributable to it before promotion to Prod is allowed.

## Rollback
Every deployment is tagged with the previous stable version. Rollback is a
single command that repoints traffic at the previous tag; it does not require
a new build. Rollback should be triggered if error rate or p99 latency
exceeds its baseline by more than 2x for more than 5 consecutive minutes
after a promotion.

## AI-assisted automation changes specifically
Any change to AI-assisted automation or remediation logic must additionally
pass the multi-model evaluation gate: the new logic's decisions on a fixed
evaluation set must be approved by the independent judge model above the
configured agreement threshold before the change can merge, regardless of
whether the unit tests pass.
