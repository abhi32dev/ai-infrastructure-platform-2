"""End-to-end CLI: builds the index (if missing) and answers a question,
running through all 7 stages: ingest -> chunk -> embed -> index -> retrieve
-> assemble context -> generate.
"""

import argparse
import json

from config import CHROMA_DIR
from embed_index import build_index
from generate import answer


def main():
    parser = argparse.ArgumentParser(description="Query the Aegis RAG pipeline")
    parser.add_argument("question", nargs="*", help="Question to ask")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild the vector index")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    if args.rebuild or not CHROMA_DIR.exists():
        print("Building vector index...")
        build_index()

    question = " ".join(args.question) or "What happens automatically when an EC2 receiver fails health checks?"
    result = answer(question)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nQ: {result['query']}\n")
        print(f"A: {result['answer']}\n")
        print(f"Sources: {result['sources']}")


if __name__ == "__main__":
    main()
