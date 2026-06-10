"""Seed Chroma collections from RAG corpus directories."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core.env_setup  # noqa: F401, E402 — SSL + .env

from core.rag import RAGConfig, RAGIndexer


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Chroma RAG index from corpus files.")
    parser.add_argument(
        "--mode",
        choices=("clean", "poisoned"),
        required=True,
        help="clean: benign corpus only; poisoned: benign + poisoned corpus",
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY in .env before running this script.")
        sys.exit(1)

    config = RAGConfig.from_env()
    indexer = RAGIndexer(config)

    if args.mode == "clean":
        count = indexer.seed_clean()
        collection = config.collection_clean
    else:
        count = indexer.seed_poisoned()
        collection = config.collection_poisoned

    print(
        f"Indexed {count} chunks into collection '{collection}' "
        f"at {config.chroma_persist_dir} (mode={args.mode})"
    )


if __name__ == "__main__":
    main()
