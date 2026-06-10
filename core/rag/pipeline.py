"""End-to-end RAG query pipeline with optional LangSmith tracing."""
import os
from dataclasses import dataclass

from openai import OpenAI

from core.firewall_pipeline import VerifyResult, verify
from core.judge_model import JudgeModel
from core.rag.config import RAGConfig
from core.rag.context_builder import build_context
from core.rag.context_guard import GuardResult, Policy, scan_chunks
from core.rag.output_guard import filter_exfil_output
from core.rag.retriever import RAGRetriever
from core.rag.tracing import maybe_traceable
from core.semantic_analyzer import SemanticAnalyzer

DEFAULT_SYSTEM = (
    "You are Acme Corp customer support. Answer using only the retrieved documents."
)


@dataclass
class RAGQueryResult:
    status: str
    prompt: str | None = None
    guard: GuardResult | None = None
    user_verify: VerifyResult | None = None
    rejected_at: str | None = None
    llm_response: str | None = None
    filtered_response: str | None = None


@maybe_traceable(name="build_prompt", run_type="tool")
def _build_prompt(system: str, user_query: str, chunks: list[dict]) -> str:
    return build_context(system, user_query, chunks)


@maybe_traceable(name="call_llm", run_type="llm")
def _call_llm(prompt: str, client: OpenAI | None = None) -> str:
    llm = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("JUDGE_MODEL", "gpt-4o-mini")
    response = llm.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""


@maybe_traceable(name="user_verify", run_type="chain")
def _verify_user_query(
    user_query: str,
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> VerifyResult:
    return verify(user_query, analyzer, judge)


@maybe_traceable(name="rag_query", run_type="chain")
def rag_query(
    user_query: str,
    system: str = DEFAULT_SYSTEM,
    policy: Policy = "strip",
    collection_name: str | None = None,
    top_k: int | None = None,
    config: RAGConfig | None = None,
    retriever: RAGRetriever | None = None,
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
    call_llm: bool = False,
    llm_client: OpenAI | None = None,
) -> RAGQueryResult:
    """retrieve → L0 context guard → user verify → build_prompt [→ LLM → L3]."""
    cfg = config or RAGConfig.from_env()
    rag = retriever or RAGRetriever(cfg, collection_name=collection_name or cfg.collection_poisoned)

    chunks = rag.retrieve(user_query, top_k=top_k)
    guard = scan_chunks(chunks, policy=policy, analyzer=analyzer, judge=judge)
    if guard.status == "REJECTED":
        return RAGQueryResult(status="REJECTED", guard=guard, rejected_at="L0")

    user_result = _verify_user_query(user_query, analyzer, judge)
    if user_result.status == "REJECTED":
        return RAGQueryResult(
            status="REJECTED",
            guard=guard,
            user_verify=user_result,
            rejected_at="user_verify",
        )

    prompt = _build_prompt(system, user_query, guard.chunks)

    llm_response: str | None = None
    filtered_response: str | None = None
    if call_llm:
        llm_response = _call_llm(prompt, llm_client)
        filtered_response = filter_exfil_output(llm_response)

    return RAGQueryResult(
        status="APPROVED",
        prompt=prompt,
        guard=guard,
        user_verify=user_result,
        llm_response=llm_response,
        filtered_response=filtered_response,
    )
