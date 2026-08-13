# Postmortem: Duplicate Alarm Delivery — 2026-02-14

## Summary
Between 03:12 and 03:41 UTC, roughly 4,200 alarms were delivered twice to the
downstream analytics system, inflating the incident dashboard's alarm count
for that window.

## Root cause
A deployment briefly ran two versions of the classification Lambda
concurrently during a rolling update. Both versions read the same batch
manifest from S3 before either had written its completion marker, so both
processed the same files.

## Why existing safeguards did not catch it
The platform's TTL-based DynamoDB dedup marker is written *after* successful
delivery to the queue, not before processing starts. Because both Lambda
versions were mid-processing simultaneously, neither had written the marker
yet when the other started, so the dedup check passed for both.

## Fix
Moved the dedup marker write to occur immediately after the manifest is
claimed (a compare-and-swap on the DynamoDB item), before processing begins,
rather than after delivery succeeds. This closes the race window: a second
process attempting to claim the same manifest entry now fails the
compare-and-swap and skips the item instead of reprocessing it.

## Follow-up actions
- Added a three-pass reconciliation job that diffs delivered records against
  the S3 audit trail nightly, to catch any future duplicate or missing
  delivery within 24 hours instead of relying solely on real-time dedup.
- Added an automated regression test that simulates two concurrent workers
  claiming the same manifest entry.
