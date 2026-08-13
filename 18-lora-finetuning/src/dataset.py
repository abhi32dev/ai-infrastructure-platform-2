"""Small instruction dataset, same 'Aegis platform' theme as projects
01/02/13 for portfolio consistency — 24 Q&A pairs, deliberately terse and
consistent in style so a tiny model fine-tuned on very little data can
plausibly learn the pattern (this is a demonstration of the LoRA/QLoRA
mechanism, not a claim of building a production instruction-tuned model
from 24 examples).
"""

QA_PAIRS = [
    ("What runs the Aegis receiver fleet?", "The receiver fleet runs on Amazon EC2 with a Network Load Balancer."),
    ("What happens when a receiver fails health checks?", "The load balancer pulls it out of rotation automatically."),
    ("What decouples ingestion from processing?", "Amazon SQS decouples ingestion from downstream processing."),
    ("What caused the 2026-02-14 incident?", "A race condition in the dedup marker write timing."),
    ("How was the 2026-02-14 incident fixed?", "The dedup marker is now written before processing, closing the race window."),
    ("When should a rollback trigger?", "If error rate exceeds twice baseline for five consecutive minutes."),
    ("Who approves a rollback?", "The platform lead approves a rollback above the automatic threshold."),
    ("What must automation changes pass before merging?", "The multi-model evaluation gate."),
    ("What does the evaluation gate require?", "Both an independent judge model and the generator model to approve."),
    ("What database backs the vector index?", "Chroma backs the vector index in this local demo."),
    ("What replaces Chroma at production scale?", "A managed vector store such as pgvector or OpenSearch."),
    ("What is the chunk size for retrieval?", "Chunk size and overlap are tunable knobs affecting retrieval cost and quality."),
    ("What backend does distributed training use here?", "The gloo backend, which is CPU-compatible."),
    ("What backend would real multi-GPU training use?", "The nccl backend, on real GPU hardware."),
    ("What tool orchestrates local Kubernetes testing?", "kind, which runs Kubernetes inside Docker."),
    ("What does a readiness probe control?", "Whether a pod receives traffic through the Service."),
    ("What does a liveness probe control?", "Whether Kubernetes restarts the pod."),
    ("Why is llama.cpp used instead of vLLM here?", "vLLM targets CUDA GPUs; llama.cpp runs natively on Apple Silicon."),
    ("What does continuous batching improve?", "Aggregate throughput under concurrent request load."),
    ("What is a circuit breaker used for?", "Fast-failing requests to a known-unhealthy downstream instead of hanging."),
    ("What state does a circuit breaker start in?", "CLOSED, meaning requests pass through normally."),
    ("What happens when a circuit breaker opens?", "Requests fail fast without waiting for a timeout."),
    ("What is a semantic cache used for?", "Skipping a model call for a near-duplicate query."),
    ("What metric confirms a real cost saving?", "A measured comparison against a would-be-cost baseline."),
]


def format_example(question: str, answer: str) -> str:
    return f"Q: {question}\nA: {answer}\n"


def build_training_texts() -> list[str]:
    return [format_example(q, a) for q, a in QA_PAIRS]


def held_out_questions() -> list[str]:
    """A few questions NOT worded identically to the training set, to
    check generalization rather than memorization."""
    return [
        "What happens if a receiver instance fails its health check?",
        "What is the purpose of the multi-model evaluation gate?",
        "Why does this project use llama.cpp rather than vLLM?",
    ]
