"""Layer 1: Semantic analysis via embeddings and cosine similarity."""
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
ATTACKS_PATH = ROOT / "data" / "known_attacks.json"


class SemanticAnalyzer:
    def __init__(
        self,
        api_key: str | None = None,
        threshold: float | None = None,
        embedding_model: str | None = None,
        attacks_path: Path | None = None,
    ):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.threshold = threshold if threshold is not None else float(
            os.getenv("SEMANTIC_THRESHOLD", "0.85")
        )
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.attacks_path = attacks_path or ATTACKS_PATH
        self.known_attacks = self._load_known_attacks()
        self._attack_matrix = self._build_attack_matrix()

    def _load_known_attacks(self) -> list[dict]:
        if not self.attacks_path.exists():
            raise FileNotFoundError(
                f"Missing {self.attacks_path}. Run: python scripts/precompute_embeddings.py"
            )
        with open(self.attacks_path, encoding="utf-8") as f:
            data = json.load(f)
        if not data or "embedding" not in data[0]:
            raise ValueError("known_attacks.json must include precomputed embeddings.")
        return data

    def _build_attack_matrix(self) -> np.ndarray:
        matrix = np.array([a["embedding"] for a in self.known_attacks], dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    @lru_cache(maxsize=512)
    def _cached_embedding(self, text: str) -> tuple[float, ...]:
        response = self.client.embeddings.create(
            input=[text],
            model=self.embedding_model,
        )
        return tuple(response.data[0].embedding)

    def get_embedding(self, text: str) -> np.ndarray:
        return np.array(self._cached_embedding(text), dtype=np.float64)

    def max_similarity(self, text: str) -> float:
        vec = self.get_embedding(text)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return 0.0
        vec_norm = vec / norm
        similarities = self._attack_matrix @ vec_norm
        return float(np.max(similarities))

    def is_attack(self, text: str) -> bool:
        return self.max_similarity(text) >= self.threshold

    def analyze(self, text: str) -> tuple[bool, float]:
        sim = self.max_similarity(text)
        return sim >= self.threshold, sim
