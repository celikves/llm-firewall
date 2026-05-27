"""Layer 3: Output filtering for PII and sensitive data."""
import re

import spacy

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
API_KEY_PATTERN = re.compile(
    r"\b(sk-[A-Za-z0-9]{20,}|api[_-]?key\s*[:=]\s*[A-Za-z0-9_-]{16,})\b",
    re.I,
)
PHONE_PATTERN = re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")


class OutputFilter:
    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError as exc:
            raise OSError(
                f"spaCy model '{model_name}' not found. "
                "Run: python -m spacy download en_core_web_sm"
            ) from exc
        self._ner_labels = {"PERSON", "ORG", "GPE"}

    def filter_output(self, raw_output: str) -> str:
        text = API_KEY_PATTERN.sub("[MASKED_API_KEY]", raw_output)
        text = EMAIL_PATTERN.sub("[MASKED_EMAIL]", text)
        text = CREDIT_CARD_PATTERN.sub("[MASKED_CARD]", text)
        text = PHONE_PATTERN.sub("[MASKED_PHONE]", text)

        doc = self.nlp(text)
        entities = sorted(doc.ents, key=lambda e: e.start_char, reverse=True)
        for ent in entities:
            if ent.label_ in self._ner_labels:
                text = (
                    text[: ent.start_char]
                    + f"[MASKED_{ent.label_}]"
                    + text[ent.end_char :]
                )
        return text
