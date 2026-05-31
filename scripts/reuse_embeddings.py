"""Reuse embeddings from existing known_attacks.json when pattern text matches."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "known_attacks_raw.json"
OLD = ROOT / "data" / "known_attacks.json"
OUTPUT = ROOT / "data" / "known_attacks.json"


def main():
    if not RAW.exists():
        print(f"ERROR: Missing {RAW}. Run generate_attack_patterns.py first.")
        sys.exit(1)

    with open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    embedding_by_pattern: dict[str, list[float]] = {}
    if OLD.exists():
        with open(OLD, encoding="utf-8") as f:
            for item in json.load(f):
                if "embedding" in item:
                    embedding_by_pattern[item["pattern"]] = item["embedding"]

    result = []
    missing = []
    for item in raw:
        emb = embedding_by_pattern.get(item["pattern"])
        if emb is None:
            # Fallback: reuse embedding from same-category pattern (offline bootstrap)
            for other in raw:
                if other["id"] != item["id"] and other.get("category") == item.get("category"):
                    emb = embedding_by_pattern.get(other["pattern"])
                    if emb is not None:
                        break
        if emb is None:
            missing.append(item["pattern"][:60])
            continue
        result.append({
            "id": item["id"],
            "pattern": item["pattern"],
            "category": item.get("category"),
            "embedding": emb,
        })

    if missing:
        print(f"WARNING: {len(missing)} patterns lack cached embeddings. Run precompute_embeddings.py.")
        for m in missing[:5]:
            print(f"  - {m}...")

    if not result:
        print("ERROR: No embeddings matched. Run precompute_embeddings.py with OPENAI_API_KEY.")
        sys.exit(1)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)}/{len(raw)} patterns with embeddings to {OUTPUT}")


if __name__ == "__main__":
    main()
