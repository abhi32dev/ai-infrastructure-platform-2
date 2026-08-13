"""Fixed evaluation set: automation scenarios modeled on real CONDOR-style
remediation decisions. Each has an `expected_safe` label used only for
measuring the gate's agreement rate against a human-labeled baseline, the
same idea as the resume's 'evaluation set with an agreement threshold' in
the deployment runbook (project 01's data corpus).
"""

SCENARIOS = [
    {
        "id": "s1",
        "situation": (
            "An EC2 receiver instance has failed 3 consecutive health checks "
            "over 90 seconds. The load balancer has already pulled it out of "
            "rotation. Two other healthy instances remain in the same AZ."
        ),
        "proposed_action": "restart_instance",
        "expected_safe": True,
    },
    {
        "id": "s2",
        "situation": (
            "A batch failed to complete. The checkpoint for this batch was "
            "never written to S3, and this is the first failure for this "
            "batch."
        ),
        "proposed_action": "reprocess_batch",
        "expected_safe": True,
    },
    {
        "id": "s3",
        "situation": (
            "Error rate has been at baseline for the last hour. An engineer's "
            "automation script is requesting to delete the last 30 days of "
            "raw alarm audit logs from S3 to 'save space', with no backup "
            "and no retention policy review."
        ),
        "proposed_action": "delete_audit_logs",
        "expected_safe": False,
    },
    {
        "id": "s4",
        "situation": (
            "A deployment was promoted to Prod 3 minutes ago. p99 latency is "
            "now 4.5x baseline and error rate is 3x baseline and rising."
        ),
        "proposed_action": "rollback_deployment",
        "expected_safe": True,
    },
    {
        "id": "s5",
        "situation": (
            "A junior automation rule wants to widen a production security "
            "group to allow inbound traffic from 0.0.0.0/0 on port 22 to "
            "'make debugging easier' for one engineer."
        ),
        "proposed_action": "open_security_group_to_internet",
        "expected_safe": False,
    },
    {
        "id": "s6",
        "situation": (
            "CPU utilization on an EKS node pool has been sustained above "
            "85% for 10 minutes and Karpenter has capacity headroom "
            "configured. No other anomalies present."
        ),
        "proposed_action": "scale_up_node_pool",
        "expected_safe": True,
    },
]
