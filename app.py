"""FastAPI entry point for the multi-layer LLM firewall."""
import os
import time
from functools import lru_cache

import core.env_setup 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.judge_model import JudgeModel
from core.output_filter import OutputFilter
from core.semantic_analyzer import SemanticAnalyzer

app = FastAPI(
    title="Multi-Layer LLM Firewall",
    description="BDM security middleware: semantic analysis, judge model, output filtering",
    version="1.0.0",
)


class VerifyRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)


class FilterRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32000)


def _get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not set. Copy .env.example to .env and add your key.",
        )
    return key


@lru_cache(maxsize=1)
def _semantic_layer() -> SemanticAnalyzer:
    return SemanticAnalyzer(api_key=_get_api_key())


@lru_cache(maxsize=1)
def _judge_layer() -> JudgeModel:
    return JudgeModel(api_key=_get_api_key())


@lru_cache(maxsize=1)
def _output_layer() -> OutputFilter:
    return OutputFilter()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "semantic_threshold": os.getenv("SEMANTIC_THRESHOLD", "0.85"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "judge_model": os.getenv("JUDGE_MODEL", "gpt-4o-mini"),
    }


@app.post("/verify")
async def verify_prompt(body: VerifyRequest):
    start = time.perf_counter()
    semantic = _semantic_layer()
    judge = _judge_layer()

    is_attack, similarity = semantic.analyze(body.prompt)
    if is_attack:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "status": "REJECTED",
            "layer": "semantic",
            "similarity": round(similarity, 4),
            "latency_ms": round(elapsed, 2),
        }

    layer1_ms = (time.perf_counter() - start) * 1000
    judge_start = time.perf_counter()
    is_malicious = judge.analyze(body.prompt)
    total_ms = (time.perf_counter() - start) * 1000
    judge_ms = (time.perf_counter() - judge_start) * 1000

    if is_malicious:
        return {
            "status": "REJECTED",
            "layer": "judge",
            "similarity": round(similarity, 4),
            "latency_ms": round(total_ms, 2),
            "layer_breakdown_ms": {
                "semantic": round(layer1_ms, 2),
                "judge": round(judge_ms, 2),
            },
        }

    return {
        "status": "APPROVED",
        "similarity": round(similarity, 4),
        "latency_ms": round(total_ms, 2),
        "layer_breakdown_ms": {
            "semantic": round(layer1_ms, 2),
            "judge": round(judge_ms, 2),
        },
    }


@app.post("/filter-output")
async def filter_output(body: FilterRequest):
    start = time.perf_counter()
    try:
        filtered = _output_layer().filter_output(body.text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "original": body.text,
        "filtered": filtered,
        "latency_ms": round(elapsed, 2),
    }
