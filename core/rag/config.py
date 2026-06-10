"""RAG configuration loaded from environment variables."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class RAGConfig:
    chroma_persist_dir: Path
    collection_clean: str
    collection_poisoned: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    corpus_benign_dir: Path
    corpus_poisoned_dir: Path

    @classmethod
    def from_env(cls) -> "RAGConfig":
        return cls(
            chroma_persist_dir=Path(
                os.getenv("CHROMA_PERSIST_DIR", str(ROOT / "chroma_db"))
            ),
            collection_clean=os.getenv("RAG_COLLECTION_CLEAN", "rag_clean"),
            collection_poisoned=os.getenv("RAG_COLLECTION_POISONED", "rag_poisoned"),
            top_k=int(os.getenv("RAG_TOP_K", "5")),
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "64")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            corpus_benign_dir=ROOT / "data" / "rag_corpus" / "benign",
            corpus_poisoned_dir=ROOT / "data" / "rag_corpus" / "poisoned",
        )
