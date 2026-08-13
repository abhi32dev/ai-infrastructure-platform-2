"""Runs the RAG pipeline's outputs through Ragas' RAG-specific metrics,
using the local Ollama models as the judge (via Ragas' Langchain wrapper)
instead of the OpenAI default — the whole point being zero API cost,
consistent with every other project in this portfolio.
"""

from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_ollama import ChatOllama, OllamaEmbeddings

from rag_pipeline import answer_with_contexts, build_index
from eval_dataset import EVAL_QUESTIONS

JUDGE_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"


def build_ragas_dataset() -> Dataset:
    rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    for item in EVAL_QUESTIONS:
        result = answer_with_contexts(item["question"])
        rows["question"].append(item["question"])
        rows["answer"].append(result["answer"])
        rows["contexts"].append(result["contexts"])
        rows["ground_truth"].append(item["ground_truth"])
    return Dataset.from_dict(rows)


def run_ragas_evaluation():
    build_index()
    dataset = build_ragas_dataset()

    judge_llm = LangchainLLMWrapper(ChatOllama(model=JUDGE_MODEL, temperature=0.0))
    judge_embeddings = LangchainEmbeddingsWrapper(OllamaEmbeddings(model=EMBED_MODEL))

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=RunConfig(timeout=180, max_workers=2),  # lower concurrency: the local 1B judge model
                                                             # serializes CPU work regardless of Python-level
                                                             # concurrency, and high concurrency was observed
                                                             # to cause request timeouts (see README)
    )
    return result


if __name__ == "__main__":
    result = run_ragas_evaluation()
    print(result)
    df = result.to_pandas()
    print("\n" + df.to_string(index=False))
