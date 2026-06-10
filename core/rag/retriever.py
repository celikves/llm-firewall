"""Chroma retrieval for RAG queries."""
import chromadb

from core.rag.config import RAGConfig
from core.rag.embedder import Embedder
from core.rag.tracing import maybe_traceable, set_run_metadata

POISONED_SOURCES = frozenset({"index_poisoning.txt", "exfil_instructions.txt"})


def is_poisoned_source(source: str) -> bool:
    return source in POISONED_SOURCES


class RAGRetriever:
    def __init__(
        self,
        config: RAGConfig | None = None,
        embedder: Embedder | None = None,
        collection_name: str | None = None,
    ):
        self.config = config or RAGConfig.from_env()
        self.embedder = embedder or Embedder(model=self.config.embedding_model)
        self.collection_name = collection_name or self.config.collection_clean
        self.client = chromadb.PersistentClient(path=str(self.config.chroma_persist_dir))

    def _get_collection(self):
        try:
            return self.client.get_collection(self.collection_name)
        except (ValueError, chromadb.errors.NotFoundError) as exc:
            raise FileNotFoundError(
                f"Chroma collection '{self.collection_name}' not found at {self.config.chroma_persist_dir}. "
                "Run: python scripts/seed_rag_index.py"
            ) from exc

    @maybe_traceable(name="chroma_retrieve", run_type="retriever")
    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k if top_k is not None else self.config.top_k
        collection = self._get_collection()
        query_embedding = self.embedder.embed_texts([query])[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        chunks = [
            {
                "id": doc_id,
                "text": text,
                "metadata": meta or {},
                "score": round(1.0 - distance, 6),
            }
            for doc_id, text, meta, distance in zip(ids, documents, metadatas, distances)
        ]
        set_run_metadata(
            poisoned_in_results=any(
                is_poisoned_source(c["metadata"].get("source", "")) for c in chunks
            ),
            chunk_ids=[c["id"] for c in chunks],
        )
        return chunks
