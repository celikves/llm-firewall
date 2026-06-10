"""ChromaDB indexing for RAG corpora."""
from pathlib import Path

import chromadb

from core.rag.tracing import maybe_traceable
from core.rag.chunker import TextChunk, load_and_chunk_directory
from core.rag.config import RAGConfig
from core.rag.embedder import Embedder


def _chunk_id(source: str, chunk_index: int) -> str:
    return f"{source}::{chunk_index}"


class RAGIndexer:
    def __init__(self, config: RAGConfig | None = None, embedder: Embedder | None = None):
        self.config = config or RAGConfig.from_env()
        self.embedder = embedder or Embedder(model=self.config.embedding_model)
        self.config.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.config.chroma_persist_dir))

    def _get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def _reset_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except (ValueError, chromadb.errors.NotFoundError):
            pass
        return self._get_collection(name)

    @maybe_traceable(name="rag_index_chunks", run_type="tool")
    def index_chunks(self, collection_name: str, chunks: list[TextChunk], *, reset: bool = True) -> int:
        if not chunks:
            raise ValueError("No chunks to index")

        collection = self._reset_collection(collection_name) if reset else self._get_collection(collection_name)
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)

        collection.add(
            ids=[_chunk_id(chunk.source, chunk.chunk_index) for chunk in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {"source": chunk.source, "chunk_index": chunk.chunk_index}
                for chunk in chunks
            ],
        )
        return len(chunks)

    def index_corpus_dirs(self, collection_name: str, directories: list[Path], *, reset: bool = True) -> int:
        chunks: list[TextChunk] = []
        for directory in directories:
            chunks.extend(
                load_and_chunk_directory(
                    directory,
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                )
            )
        return self.index_chunks(collection_name, chunks, reset=reset)

    def seed_clean(self) -> int:
        return self.index_corpus_dirs(self.config.collection_clean, [self.config.corpus_benign_dir])

    def seed_poisoned(self) -> int:
        return self.index_corpus_dirs(
            self.config.collection_poisoned,
            [self.config.corpus_benign_dir, self.config.corpus_poisoned_dir],
        )
