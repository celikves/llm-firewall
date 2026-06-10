"""OpenAI embedding helper for RAG indexing."""
import os

from openai import OpenAI

from core.rag.tracing import maybe_traceable

BATCH_SIZE = 50


class Embedder:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    @maybe_traceable(name="rag_embed_texts", run_type="embedding")
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = self.client.embeddings.create(input=batch, model=self.model)
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings
