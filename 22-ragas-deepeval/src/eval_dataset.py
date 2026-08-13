"""Fixed evaluation set with ground-truth answers curated directly from
the source corpus — required by Ragas' context_recall metric (which
checks whether the retrieved contexts contain enough information to
support the ground truth, not just the model's own answer)."""

EVAL_QUESTIONS = [
    {
        "question": "What happens when an EC2 receiver fails health checks?",
        "ground_truth": "The Network Load Balancer's target-health check detects the failing instance and automatically pulls it out of rotation.",
    },
    {
        "question": "What caused the 2026-02-14 duplicate alarm incident?",
        "ground_truth": "A rolling deployment briefly ran two versions of the classification Lambda concurrently, and both read the same batch manifest before either had written its completion marker.",
    },
    {
        "question": "Who approves a rollback?",
        "ground_truth": "Rollback below the 2x latency/error-rate threshold does not need approval; above that threshold, the platform lead must be paged before rolling back.",
    },
    {
        "question": "What must AI-assisted automation changes pass before merging?",
        "ground_truth": "They must pass the multi-model evaluation gate, where an independent judge model must approve the new logic's decisions above the configured agreement threshold.",
    },
]
