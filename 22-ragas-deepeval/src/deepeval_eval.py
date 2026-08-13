"""Runs the same RAG outputs through DeepEval's metrics, using a custom
DeepEvalBaseLLM subclass wrapping local Ollama — DeepEval defaults to
OpenAI's API unless you provide a custom model, so this wrapper is
required, not optional, to run this framework at zero API cost.
"""

from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
from langchain_ollama import ChatOllama

from rag_pipeline import answer_with_contexts, build_index
from eval_dataset import EVAL_QUESTIONS

JUDGE_MODEL = "qwen2.5:1.5b"  # llama3.2:1b failed here — see README's real finding on
                                # this exact swap and why it matters


class OllamaDeepEvalModel(DeepEvalBaseLLM):
    """The required adapter: DeepEval's metrics call generate()/a_generate()
    on whatever model object they're given — this maps those calls onto a
    local ChatOllama instance instead of OpenAI's API."""

    def __init__(self, model_name: str = JUDGE_MODEL):
        self.model_name = model_name
        self.chat = ChatOllama(model=model_name, temperature=0.0)

    def load_model(self):
        return self.chat

    def generate(self, prompt: str) -> str:
        return self.chat.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        response = await self.chat.ainvoke(prompt)
        return response.content

    def get_model_name(self) -> str:
        return self.model_name


def run_deepeval_evaluation() -> list[dict]:
    build_index()
    judge = OllamaDeepEvalModel()

    faithfulness_metric = FaithfulnessMetric(threshold=0.5, model=judge, include_reason=False)
    relevancy_metric = AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=False)

    results = []
    for item in EVAL_QUESTIONS:
        rag_result = answer_with_contexts(item["question"])
        test_case = LLMTestCase(
            input=item["question"],
            actual_output=rag_result["answer"],
            retrieval_context=rag_result["contexts"],
            expected_output=item["ground_truth"],
        )

        faithfulness_metric.measure(test_case)
        relevancy_metric.measure(test_case)

        results.append({
            "question": item["question"],
            "faithfulness_score": faithfulness_metric.score,
            "faithfulness_passed": faithfulness_metric.is_successful(),
            "relevancy_score": relevancy_metric.score,
            "relevancy_passed": relevancy_metric.is_successful(),
        })

    return results


if __name__ == "__main__":
    results = run_deepeval_evaluation()
    for r in results:
        print(f"\nQ: {r['question']}")
        print(f"  faithfulness: {r['faithfulness_score']:.3f} ({'PASS' if r['faithfulness_passed'] else 'FAIL'})")
        print(f"  answer_relevancy: {r['relevancy_score']:.3f} ({'PASS' if r['relevancy_passed'] else 'FAIL'})")
