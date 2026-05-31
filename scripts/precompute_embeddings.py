"""Precompute embeddings for known attack patterns."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core.env_setup  # noqa: F401, E402 — SSL + .env

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "known_attacks_raw.json"
OUTPUT = ROOT / "data" / "known_attacks.json"
BATCH_SIZE = 50


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: Set OPENAI_API_KEY in .env before running this script.")
        sys.exit(1)

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    client = OpenAI(api_key=api_key)

    with open(INPUT, encoding="utf-8") as f:
        raw = json.load(f)

    patterns = [item["pattern"] for item in raw]
    all_embeddings = []

    for i in range(0, len(patterns), BATCH_SIZE):
        batch = patterns[i : i + BATCH_SIZE]
        response = client.embeddings.create(input=batch, model=model)
        batch_emb = [d.embedding for d in response.data]
        all_embeddings.extend(batch_emb)
        print(f"Embedded {min(i + BATCH_SIZE, len(patterns))}/{len(patterns)}")

    result = []
    for item, embedding in zip(raw, all_embeddings):
        entry = {
            "id": item["id"],
            "pattern": item["pattern"],
            "embedding": embedding,
        }
        if "category" in item:
            entry["category"] = item["category"]
        result.append(entry)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)} patterns with embeddings to {OUTPUT}")


if __name__ == "__main__":
    main()
