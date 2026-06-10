"""RAG infrastructure: chunking, embedding, retrieval, and L0 context guard."""
from core.rag.chunker import TextChunk, chunk_text, load_and_chunk_directory
from core.rag.config import RAGConfig
from core.rag.context_builder import build_context
from core.rag.context_guard import ChunkScanResult, GuardResult, scan_chunk, scan_chunks
from core.rag.embedder import Embedder
from core.rag.guard_wrappers import full_scan, judge_scan, semantic_scan
from core.rag.indexer import RAGIndexer
from core.rag.output_guard import filter_exfil_output
from core.rag.pipeline import RAGQueryResult, rag_query
from core.rag.retriever import POISONED_SOURCES, RAGRetriever, is_poisoned_source
from core.rag.tracing import is_rag_trace_enabled, maybe_traceable

__all__ = [
    "RAGConfig",
    "RAGIndexer",
    "RAGRetriever",
    "Embedder",
    "TextChunk",
    "chunk_text",
    "load_and_chunk_directory",
    "build_context",
    "scan_chunk",
    "scan_chunks",
    "ChunkScanResult",
    "GuardResult",
    "semantic_scan",
    "judge_scan",
    "full_scan",
    "is_poisoned_source",
    "POISONED_SOURCES",
    "rag_query",
    "RAGQueryResult",
    "is_rag_trace_enabled",
    "maybe_traceable",
    "filter_exfil_output",
]
