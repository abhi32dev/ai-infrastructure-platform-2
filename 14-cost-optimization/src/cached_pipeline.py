"""Ties the semantic cache and cost ledger around a real Ollama call:
cache lookup first; on a hit, log the cost that WOULD have been spent
(for the savings comparison) without calling the model at all; on a miss,
call the model, cache the response, and log actual cost.
"""

import tiktoken
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import GEN_MODEL, MODEL_COST_PER_1M_TOKENS
from semantic_cache import SemanticCache
from cost_ledger import get_connection, log_request

encoder = tiktoken.get_encoding("cl100k_base")


def estimate_cost(tokens: int) -> float:
    return tokens / 1_000_000 * MODEL_COST_PER_1M_TOKENS


class CachedPipeline:
    def __init__(self):
        self.cache = SemanticCache()
        self.ledger_conn = get_connection()
        self.llm = ChatOllama(model=GEN_MODEL, temperature=0.0)

    def query(self, text: str) -> dict:
        hit = self.cache.lookup(text)

        if hit is not None:
            response_tokens = len(encoder.encode(hit["response"]))
            input_tokens = len(encoder.encode(text))
            would_be_cost = estimate_cost(input_tokens + response_tokens)

            log_request(self.ledger_conn, text, cache_hit=True, similarity=hit["similarity"],
                        tokens=input_tokens + response_tokens, actual_cost=0.0, would_be_cost=would_be_cost)

            return {"query": text, "response": hit["response"], "cache_hit": True,
                    "similarity": hit["similarity"], "matched_query": hit["query"]}

        response = self.llm.invoke([HumanMessage(content=text)]).content
        input_tokens = len(encoder.encode(text))
        response_tokens = len(encoder.encode(response))
        total_tokens = input_tokens + response_tokens
        cost = estimate_cost(total_tokens)

        self.cache.store(text, response)
        log_request(self.ledger_conn, text, cache_hit=False, similarity=None,
                    tokens=total_tokens, actual_cost=cost, would_be_cost=cost)

        return {"query": text, "response": response, "cache_hit": False, "similarity": None}
