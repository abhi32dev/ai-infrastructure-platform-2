"""Runs the full query set through the router, counts tokens per call
(tiktoken as an approximation — Ollama models use different tokenizers,
but this is standard practice for cross-model token estimation), and
reports the dollar-cost delta between "route everything to the large
model" and "cost-aware routing" using the illustrative rate card in
config.py.
"""

import tiktoken

from config import (
    SMALL_MODEL, LARGE_MODEL,
    SMALL_MODEL_COST_PER_1M_TOKENS, LARGE_MODEL_COST_PER_1M_TOKENS,
)
from router import route_and_answer, classify
from queries import QUERIES

encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


def cost_of(model: str, tokens: int) -> float:
    rate = SMALL_MODEL_COST_PER_1M_TOKENS if model == SMALL_MODEL else LARGE_MODEL_COST_PER_1M_TOKENS
    return tokens / 1_000_000 * rate


def run_report():
    rows = []
    for q in QUERIES:
        result = route_and_answer(q["text"])
        in_tok = count_tokens(q["text"])
        out_tok = count_tokens(result["answer"])
        total_tok = in_tok + out_tok

        routed_cost = cost_of(result["model_used"], total_tok)
        always_large_cost = cost_of(LARGE_MODEL, total_tok)

        rows.append({
            "id": q["id"],
            "tier": result["tier"],
            "model_used": result["model_used"],
            "tokens": total_tok,
            "routed_cost_usd": routed_cost,
            "always_large_cost_usd": always_large_cost,
        })

    total_routed = sum(r["routed_cost_usd"] for r in rows)
    total_always_large = sum(r["always_large_cost_usd"] for r in rows)
    savings_pct = (1 - total_routed / total_always_large) * 100 if total_always_large else 0

    print(f"{'id':4} {'tier':8} {'model':14} {'tokens':7} {'routed $':>10} {'always-large $':>16}")
    for r in rows:
        print(f"{r['id']:4} {r['tier']:8} {r['model_used']:14} {r['tokens']:7} "
              f"{r['routed_cost_usd']:>10.6f} {r['always_large_cost_usd']:>16.6f}")

    print(f"\nTotal cost, cost-aware routing:     ${total_routed:.6f}")
    print(f"Total cost, always route to large:  ${total_always_large:.6f}")
    print(f"Savings from routing: {savings_pct:.1f}%")
    return rows, total_routed, total_always_large


if __name__ == "__main__":
    run_report()
