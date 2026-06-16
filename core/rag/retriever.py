"""Chroma retrieval for RAG queries."""
import chromadb

from core.rag.config import RAGConfig
from core.rag.embedder import Embedder
from core.rag.tracing import maybe_traceable, set_run_metadata, set_run_outputs

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

        chunks = []
        for doc_id, text, meta, distance in zip(ids, documents, metadatas, distances):
            source = (meta or {}).get("source", "")
            poisoned = is_poisoned_source(source)
            chunks.append(
                {
                    "id": doc_id,
                    "text": text,
                    "metadata": meta or {},
                    "score": round(1.0 - distance, 6),
                    "poisoned_source": poisoned,
                    "source": source or "unknown",
                }
            )

        poisoned_chunks = [c for c in chunks if c["poisoned_source"]]
        set_run_metadata(
            collection=self.collection_name,
            poisoned_in_results=bool(poisoned_chunks),
            poisoned_chunk_count=len(poisoned_chunks),
            poisoned_chunk_ids=[c["id"] for c in poisoned_chunks],
            poisoned_sources=sorted({c["source"] for c in poisoned_chunks}),
            chunk_ids=[c["id"] for c in chunks],
            chunk_sources=[c["source"] for c in chunks],
        )
        set_run_outputs(
            retrieved_count=len(chunks),
            poisoned_in_results=bool(poisoned_chunks),
            chunks=[
                {
                    "id": c["id"],
                    "source": c["source"],
                    "poisoned_source": c["poisoned_source"],
                    "score": c["score"],
                    "text_preview": c["text"][:120] + ("…" if len(c["text"]) > 120 else ""),
                }
                for c in chunks
            ],
        )
        return chunks
