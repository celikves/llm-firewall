"""Split corpus documents into overlapping text chunks."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TextChunk:
    text: str
    source: str
    chunk_index: int


def chunk_text(text: str, source: str, chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(normalized):
        end = start + chunk_size
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(TextChunk(text=chunk, source=source, chunk_index=index))
            index += 1
        if end >= len(normalized):
            break
        start = end - chunk_overlap
    return chunks


def load_and_chunk_directory(
    directory: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {directory}")

    all_chunks: list[TextChunk] = []
    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        all_chunks.extend(chunk_text(text, source=path.name, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return all_chunks
