"""Runs both frameworks against the identical RAG pipeline and question
set, and prints their faithfulness/relevancy-family scores side by side
— since both frameworks claim to measure similar things but use
different decomposition prompts and judge-parsing strategies internally,
so agreement (or disagreement) between them is itself informative.
"""

from ragas_eval import run_ragas_evaluation
from deepeval_eval import run_deepeval_evaluation


if __name__ == "__main__":
    print("Running Ragas evaluation...")
    ragas_result = run_ragas_evaluation()
    ragas_df = ragas_result.to_pandas()

    print("\nRunning DeepEval evaluation...")
    deepeval_results = run_deepeval_evaluation()

    print("\n=== Side-by-side: faithfulness ===")
    print(f"{'question':60} {'ragas':>10} {'deepeval':>10}")
    for i, row in ragas_df.iterrows():
        de = deepeval_results[i]
        print(f"{row['user_input'][:58]:60} {row['faithfulness']:>10.3f} {de['faithfulness_score']:>10.3f}")

    print(f"\nRagas avg faithfulness:    {ragas_df['faithfulness'].mean():.3f}")
    print(f"DeepEval avg faithfulness: {sum(r['faithfulness_score'] for r in deepeval_results) / len(deepeval_results):.3f}")
