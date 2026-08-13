"""Tests split into fast/deterministic (the RAG pipeline and dataset
construction, no judge-model LLM calls) and slow/live (the actual
framework evaluations, which take up to several minutes each given local
CPU inference — marked so they can be skipped in a quick run).

Real finding from building this suite: running all three `slow` tests
together in one pytest session caused the run to hang indefinitely (low
CPU usage, no progress for 40+ minutes, versus ~30s-4min when run
individually). Root cause not fully isolated — likely cumulative
resource/context buildup in the single shared `llama-server` process
Ollama keeps alive across many sequential heavy calls within one Python
process's lifetime. Each test is independently verified to pass reliably
when run in its own process: `pytest -q -m slow -k <test_name>`. Running
the full `-m slow` selection in one command is NOT currently reliable on
this hardware — documented here rather than silently worked around.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from eval_dataset import EVAL_QUESTIONS


# --- Fast/deterministic ---

def test_eval_dataset_has_ground_truth_for_every_question():
    assert len(EVAL_QUESTIONS) > 0
    for item in EVAL_QUESTIONS:
        assert item["question"]
        assert item["ground_truth"]


def test_eval_dataset_questions_are_unique():
    questions = [item["question"] for item in EVAL_QUESTIONS]
    assert len(questions) == len(set(questions))


def test_rag_pipeline_returns_answer_and_contexts():
    from rag_pipeline import build_index, answer_with_contexts
    build_index()
    result = answer_with_contexts(EVAL_QUESTIONS[0]["question"])
    assert result["answer"]
    assert len(result["contexts"]) > 0


# --- Slow/live: full framework evaluations (several minutes each) ---

@pytest.mark.slow
def test_ragas_faithfulness_and_recall_are_valid_scores():
    from ragas_eval import run_ragas_evaluation
    result = run_ragas_evaluation()
    df = result.to_pandas()
    assert (df["faithfulness"].dropna() >= 0).all()
    assert (df["faithfulness"].dropna() <= 1).all()
    assert (df["context_recall"].dropna() >= 0).all()


@pytest.mark.slow
def test_deepeval_with_unreliable_judge_either_fails_loud_or_succeeds_never_silently_wrong():
    """Regression guard for a real, INTERMITTENT finding: llama3.2:1b's
    JSON reliability with DeepEval's verdict-extraction prompt is not
    deterministic — the exact same code path raised
    'Evaluation LLM outputted an invalid JSON... use a better evaluation
    model' on one manual run and succeeded on a later retry with a
    different (simpler) test case. This is itself the finding: a small
    local judge model's structured-output reliability varies by input,
    not a guaranteed pass or fail. What must ALWAYS hold either way:
    when it fails, it fails LOUD (a specific ValueError), never silently
    returning a wrong/default score."""
    from deepeval_eval import OllamaDeepEvalModel
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    unreliable_judge = OllamaDeepEvalModel(model_name="llama3.2:1b")
    metric = FaithfulnessMetric(threshold=0.5, model=unreliable_judge, include_reason=False)
    test_case = LLMTestCase(
        input="What happens when an EC2 receiver fails health checks?",
        actual_output="The load balancer removes it from rotation.",
        retrieval_context=["The load balancer's health check removes unhealthy instances from rotation."],
    )

    try:
        metric.measure(test_case)
        assert 0 <= metric.score <= 1  # if it succeeded, the score must still be valid
    except ValueError as e:
        assert "invalid JSON" in str(e)  # if it failed, it must be this specific, loud failure


@pytest.mark.slow
def test_deepeval_with_reliable_judge_produces_valid_scores():
    from deepeval_eval import run_deepeval_evaluation
    results = run_deepeval_evaluation()
    assert len(results) == len(EVAL_QUESTIONS)
    for r in results:
        assert 0 <= r["faithfulness_score"] <= 1
        assert 0 <= r["relevancy_score"] <= 1
