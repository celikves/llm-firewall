"""Keyword and regex baseline for H1 comparison (not used in production pipeline)."""
import re

KEYWORDS_EN = [
    "ignore previous",
    "ignore all previous",
    "ignore prior",
    "disregard",
    "forget everything",
    "system prompt",
    "reveal the",
    "jailbreak",
    "dan mode",
    "developer mode",
    "override",
    "bypass",
    "no restrictions",
    "unrestricted",
    "admin password",
    "confidential",
    "exfiltrate",
    "do anything now",
]

KEYWORDS_TR = [
    "onceki talimat",
    "tum kurallari unut",
    "yoksay",
    "sistem prompt",
    "gizli bilgi",
    "admin sifre",
]

PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.I),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|secret)", re.I),
    re.compile(r"jailbreak|DAN\s+mode|developer\s+mode", re.I),
    re.compile(r"bypass\s+(content|safety|filter)", re.I),
    re.compile(r"disregard\s+(your\s+)?(guidelines|rules)", re.I),
]


class KeywordBaseline:
    def is_attack(self, text: str) -> bool:
        lowered = text.lower()
        for kw in KEYWORDS_EN + KEYWORDS_TR:
            if kw in lowered:
                return True
        for pat in PATTERNS:
            if pat.search(text):
                return True
        return False
