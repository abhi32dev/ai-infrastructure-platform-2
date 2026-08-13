"""Runs the fixed evaluation set against a given versioned judge prompt and
logs the run to MLflow: params (prompt version, model, temperature),
metrics (agreement_rate, per-scenario correctness, latency), and an
artifact (the raw per-scenario results as JSON) — the same reproducible,
comparable-across-versions history the resume's 'Automation Logic Version
Tracking (MLflow)' bullet describes.
"""

import json
import time

import mlflow
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config import (
    PROMPTS_DIR, MLFLOW_DB, ARTIFACTS_DIR, JUDGE_MODEL, JUDGE_TEMPERATURE,
    CURRENT_PROMPT_VERSION, MLFLOW_EXPERIMENT_NAME,
)
from scenarios import SCENARIOS


def load_prompt(version: str) -> str:
    return (PROMPTS_DIR / f"judge_prompt_{version}.txt").read_text()


def run_judge(system_prompt: str, situation: str, action: str) -> tuple[dict, float]:
    llm = ChatOllama(model=JUDGE_MODEL, temperature=JUDGE_TEMPERATURE, format="json")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Situation: {situation}\nAction under review: {action}"),
    ]
    start = time.time()
    raw = llm.invoke(messages).content
    latency = time.time() - start
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"verdict": "REJECT", "reasoning": f"unparsable: {raw[:150]}"}
    return parsed, latency


def evaluate(prompt_version: str = CURRENT_PROMPT_VERSION) -> dict:
    system_prompt = load_prompt(prompt_version)
    results = []
    for sc in SCENARIOS:
        verdict, latency = run_judge(system_prompt, sc["situation"], sc["proposed_action"])
        approved = verdict.get("verdict") == "APPROVE"
        correct = approved == sc["expected_safe"]
        results.append({
            "id": sc["id"],
            "action": sc["proposed_action"],
            "verdict": verdict.get("verdict"),
            "reasoning": verdict.get("reasoning"),
            "expected_safe": sc["expected_safe"],
            "correct": correct,
            "latency_sec": round(latency, 3),
        })

    agreement_rate = sum(r["correct"] for r in results) / len(results)
    avg_latency = sum(r["latency_sec"] for r in results) / len(results)

    return {
        "prompt_version": prompt_version,
        "model": JUDGE_MODEL,
        "temperature": JUDGE_TEMPERATURE,
        "agreement_rate": agreement_rate,
        "avg_latency_sec": round(avg_latency, 3),
        "results": results,
    }


def evaluate_and_log(prompt_version: str = CURRENT_PROMPT_VERSION) -> dict:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB}")
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    summary = evaluate(prompt_version)

    with mlflow.start_run(run_name=f"judge_{prompt_version}"):
        mlflow.log_param("prompt_version", summary["prompt_version"])
        mlflow.log_param("model", summary["model"])
        mlflow.log_param("temperature", summary["temperature"])
        mlflow.log_metric("agreement_rate", summary["agreement_rate"])
        mlflow.log_metric("avg_latency_sec", summary["avg_latency_sec"])

        results_path = ARTIFACTS_DIR / f"_last_results_{prompt_version}.json"
        results_path.write_text(json.dumps(summary["results"], indent=2))
        mlflow.log_artifact(str(results_path))
        results_path.unlink()

    return summary


if __name__ == "__main__":
    import sys

    version = sys.argv[1] if len(sys.argv) > 1 else CURRENT_PROMPT_VERSION
    summary = evaluate_and_log(version)
    print(f"Prompt version: {summary['prompt_version']}")
    print(f"Agreement rate: {summary['agreement_rate']:.2f}")
    print(f"Avg latency: {summary['avg_latency_sec']}s")
    for r in summary["results"]:
        flag = "OK " if r["correct"] else "MISS"
        print(f"  [{flag}] {r['id']}: {r['action']} -> {r['verdict']} ({r['reasoning']})")
