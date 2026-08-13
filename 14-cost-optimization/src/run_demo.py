"""Simulates a realistic query stream with paraphrased near-duplicates —
the exact case a plain string-match cache would miss but a semantic cache
catches — and reports the resulting cost savings from the ledger.
"""

from cached_pipeline import CachedPipeline
from cost_ledger import summary, reset
from config import LEDGER_DB

QUERY_STREAM = [
    "What happens when an EC2 receiver fails health checks?",
    "What should I do if a batch is stuck in-progress?",
    "How does the load balancer handle an unhealthy instance?",       # paraphrase of query 1
    "What's the process to restart an instance that's failing checks?",  # another paraphrase of query 1
    "Who approves a rollback?",
    "What is the retention TTL for the dedup marker?",
    "When an instance fails its health check, what happens automatically?",  # paraphrase of query 1 again
    "Who signs off on rolling back a deployment?",                    # paraphrase of query 5
]


def run_demo():
    reset()  # fresh ledger for this demo run
    pipeline = CachedPipeline()

    for i, query in enumerate(QUERY_STREAM, 1):
        result = pipeline.query(query)
        if result["cache_hit"]:
            print(f"{i}. [CACHE HIT sim={result['similarity']:.3f}] {query!r}")
            print(f"   matched: {result['matched_query']!r}")
        else:
            print(f"{i}. [CACHE MISS -> LLM call] {query!r}")

    stats = summary(pipeline.ledger_conn)
    print(f"\n=== Cost summary ===")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Cache hits: {stats['cache_hits']} ({stats['cache_hit_rate']*100:.1f}%)")
    print(f"Actual cost: ${stats['actual_cost_usd']:.6f}")
    print(f"Would-be cost (no cache): ${stats['would_be_cost_usd']:.6f}")
    print(f"Savings: ${stats['savings_usd']:.6f} ({stats['savings_pct']:.1f}%)")
    return stats


if __name__ == "__main__":
    run_demo()
