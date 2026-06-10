"""FastAPI entry point for the RAG pipeline (separate from firewall on :8000)."""
import os
import time
from functools import lru_cache
from typing import Literal

import core.env_setup  # noqa: F401 — SSL + .env
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.judge_model import JudgeModel
from core.rag import RAGConfig, rag_query
from core.rag.response_utils import serialize_retrieved_chunks
from core.rag.retriever import is_poisoned_source
from core.rag.tracing import is_rag_trace_enabled
from core.semantic_analyzer import SemanticAnalyzer

app = FastAPI(
    title="LLM Firewall — RAG API",
    description="RAG retrieval with L0 context guard and optional LLM call",
    version="1.0.0",
)

Policy = Literal["strip", "block"]


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    collection: str = Field(default="rag_poisoned", description="rag_clean, rag_poisoned, clean, or poisoned")
    policy: Policy = Field(default="strip")
    call_llm: bool = Field(default=False)
    top_k: int | None = Field(default=None, ge=1, le=20)


def _get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not set. Copy .env.example to .env and add your key.",
        )
    return key


def _resolve_collection(name: str, config: RAGConfig) -> str:
    aliases = {
        "clean": config.collection_clean,
        "rag_clean": config.collection_clean,
        "poisoned": config.collection_poisoned,
        "rag_poisoned": config.collection_poisoned,
    }
    return aliases.get(name, name)


@lru_cache(maxsize=1)
def _semantic_layer() -> SemanticAnalyzer:
    return SemanticAnalyzer(api_key=_get_api_key())


@lru_cache(maxsize=1)
def _judge_layer() -> JudgeModel:
    return JudgeModel(api_key=_get_api_key())


@app.get("/health")
async def health():
    config = RAGConfig.from_env()
    return {
        "status": "ok",
        "collections": {
            "clean": config.collection_clean,
            "poisoned": config.collection_poisoned,
        },
        "rag_trace_enabled": is_rag_trace_enabled(),
        "langsmith_tracing": os.getenv("LANGSMITH_TRACING", ""),
        "langsmith_project": os.getenv("LANGSMITH_PROJECT", ""),
    }


@app.post("/rag/query")
async def rag_query_endpoint(body: RAGQueryRequest):
    start = time.perf_counter()
    config = RAGConfig.from_env()
    collection_name = _resolve_collection(body.collection, config)

    try:
        result = rag_query(
            body.query,
            policy=body.policy,
            collection_name=collection_name,
            top_k=body.top_k,
            analyzer=_semantic_layer(),
            judge=_judge_layer(),
            call_llm=body.call_llm,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    retrieved_chunks = serialize_retrieved_chunks(result.guard, body.policy)
    poisoned_chunks = [c for c in retrieved_chunks if c["poisoned_source"]]
    poisoned_in_retrieval = len(poisoned_chunks) > 0

    response: dict = {
        "status": result.status,
        "rejected_at": result.rejected_at,
        "collection": collection_name,
        "policy": body.policy,
        "retrieved_count": len(retrieved_chunks),
        "chunks_kept": len(result.guard.chunks) if result.guard else 0,
        "poisoned_in_retrieval": poisoned_in_retrieval,
        "poisoned_chunk_count": len(poisoned_chunks),
        "retrieved_chunks": retrieved_chunks,
        "poisoned_chunks": poisoned_chunks,
        "prompt": result.prompt,
        "llm_response": result.llm_response,
        "filtered_response": result.filtered_response,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
    }

    if result.user_verify:
        response["user_verify"] = {
            "status": result.user_verify.status,
            "layer": result.user_verify.layer,
            "similarity": round(result.user_verify.similarity, 4),
        }

    return response
