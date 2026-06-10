"""Layer 3 (RAG extension): block exfiltration URLs and poisoned-output phrases."""
import re

from core.rag.tracing import maybe_traceable

URL_PATTERN = re.compile(r"https?://[^\s<>\"'\)\]]+", re.IGNORECASE)

EXFIL_PHRASE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bEXPORT_COMPLETE\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\baudit\s+mode\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bexfiltrat(?:e|ion|ing)\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bunauthorized\s+(?:compliance\s+)?audit\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bAPPEND\s+THE\s+TEXT\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bEXPORT[_\s]+COMPLETE\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bleak\s+(?:all|the)\s+(?:api\s+)?keys?\b", re.I), "[BLOCKED_EXFIL]"),
    (re.compile(r"\bverbatim\s+contents?\s+of\s+every\s+retrieved\b", re.I), "[BLOCKED_EXFIL]"),
]


@maybe_traceable(name="L3_output_filter", run_type="tool")
def filter_exfil_output(raw_output: str) -> str:
    """Mask suspicious URLs and exfiltration trigger phrases in LLM output."""
    text = URL_PATTERN.sub("[BLOCKED_URL]", raw_output)
    for pattern, replacement in EXFIL_PHRASE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
