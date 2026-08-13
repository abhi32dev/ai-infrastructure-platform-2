"""Live experiment: is the latency difference between the small routed
model (llama3.2:1b) and the large routed model (qwen2.5:3b) from project
04 statistically real, or could it be noise from one lucky/unlucky run?
Uses real Ollama calls — no simulation — with Welch's t-test since the two
models' latency variance is not assumed equal.
"""

import time
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from stats_harness import welch_t_test, print_result

SMALL_MODEL = "llama3.2:1b"
LARGE_MODEL = "qwen2.5:3b"

PROMPTS = [
    "What is 12 + 15?",
    "Name the capital of France.",
    "Is the sky blue? Answer in one word.",
    "What year did WWII end?",
    "Spell the word 'latency'.",
    "What is 7 times 6?",
    "Name one primary color.",
    "True or false: water boils at 100C at sea level.",
]


def measure_latencies(model: str) -> list[float]:
    llm = ChatOllama(model=model, temperature=0.0)
    latencies = []
    for prompt in PROMPTS:
        start = time.time()
        llm.invoke([HumanMessage(content=prompt)])
        latencies.append(time.time() - start)
    return latencies


def run_experiment():
    print(f"Measuring latency: {len(PROMPTS)} prompts x 2 models (real Ollama calls)...")
    small_latencies = measure_latencies(SMALL_MODEL)
    large_latencies = measure_latencies(LARGE_MODEL)

    result = welch_t_test(small_latencies, large_latencies, metric_name="response_latency_sec")
    print_result(result)
    print(f"\nRaw small-model ({SMALL_MODEL}) latencies: {[round(x,3) for x in small_latencies]}")
    print(f"Raw large-model ({LARGE_MODEL}) latencies: {[round(x,3) for x in large_latencies]}")
    return result


if __name__ == "__main__":
    run_experiment()
