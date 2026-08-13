# On-Call FAQ

**Q: An EC2 receiver instance is failing health checks. What happens
automatically?**
A: The Network Load Balancer's target-health check will detect the failing
instance within its configured interval and pull it out of rotation
automatically. No manual escalation is needed for this case alone. You should
still investigate why the instance is unhealthy, since Karpenter/autoscaling
will replace it but won't tell you the root cause.

**Q: A batch is stuck in "in-progress" and never completes. What do I do?**
A: Check whether the batch's checkpoint was written to S3. If not, the
self-healing re-invocation should pick it up on the next cycle automatically.
If the checkpoint exists but the batch is still marked in-progress, the
completion-marker write likely failed; manually re-trigger the batch via the
orchestrator's replay endpoint.

**Q: How do I tell if an alarm spike is real traffic or a duplicate-delivery
bug?**
A: Compare the DynamoDB trace table count against the raw S3 audit table
count for the same window. If they match, it's real traffic. If the trace
table count is higher, suspect duplicate delivery and check the dedup marker
timing (see the 2026-02-14 postmortem for a known failure mode here).

**Q: Who approves a rollback?**
A: Rollback below the 2x-latency/error-rate threshold does not need approval
and should be executed immediately by whoever is on call. Above that
threshold, page the platform lead before rolling back, since a rollback that
large may itself cause a second incident if the previous version is also
degraded.
