"""Cost-aware model router.

Classifies each incoming query as SIMPLE (single-fact lookup) or COMPLEX
(multi-step reasoning, comparison, synthesis) using a cheap classification
call on the small model itself, then routes generation to the small model
for SIMPLE queries and the larger model only for COMPLEX ones — instead of
sending every query to the expensive model by default.
"""

import json
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config import SMALL_MODEL, LARGE_MODEL, COMPLEXITY_ROUTER_MODEL

CLASSIFY_PROMPT = (
    "Classify the following question as SIMPLE (a direct single-fact lookup, "
    "answerable by finding one sentence) or COMPLEX (requires multi-step "
    "reasoning, comparison across multiple facts, or synthesis). "
    'Respond with ONLY JSON: {"tier": "SIMPLE"|"COMPLEX"}'
)


def classify(question: str) -> str:
    llm = ChatOllama(model=COMPLEXITY_ROUTER_MODEL, temperature=0.0, format="json")
    messages = [SystemMessage(content=CLASSIFY_PROMPT), HumanMessage(content=question)]
    raw = llm.invoke(messages).content
    try:
        tier = json.loads(raw).get("tier", "COMPLEX")
    except json.JSONDecodeError:
        tier = "COMPLEX"  # fail safe: route unparsable classification to the stronger model
    return tier if tier in ("SIMPLE", "COMPLEX") else "COMPLEX"


def route_and_answer(question: str) -> dict:
    tier = classify(question)
    model_name = SMALL_MODEL if tier == "SIMPLE" else LARGE_MODEL

    llm = ChatOllama(model=model_name, temperature=0.1)
    response = llm.invoke([HumanMessage(content=question)])

    return {
        "question": question,
        "tier": tier,
        "model_used": model_name,
        "answer": response.content,
    }


if __name__ == "__main__":
    from queries import QUERIES

    for q in QUERIES:
        result = route_and_answer(q["text"])
        match = "OK" if result["tier"].lower() == q["expected_tier"] else "MISMATCH"
        print(f"[{match}] {q['id']}: routed={result['tier']} -> {result['model_used']}")
