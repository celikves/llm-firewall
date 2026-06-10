"""Build delimiter-structured prompts from system text, user query, and retrieved chunks."""


def build_context(system: str, user_query: str, chunks: list[dict]) -> str:
    """Assemble <system>, <user_query>, and <retrieved_documents> sections."""
    doc_blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("metadata", {}).get("source", "unknown")
        doc_blocks.append(f"[doc {index} source={source}]\n{chunk['text']}")

    retrieved = "\n\n".join(doc_blocks) if doc_blocks else "(none)"

    return (
        f"<system>\n{system.strip()}\n</system>\n\n"
        f"<user_query>\n{user_query.strip()}\n</user_query>\n\n"
        f"<retrieved_documents>\n{retrieved}\n</retrieved_documents>"
    )
