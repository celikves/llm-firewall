# Jury Presentation Outline (English slides)

## Slide 1 — Title
**Multi-Layer LLM Firewall: Defense-in-Depth Against Prompt Injection**

Vesile Çelik — Ege University, Computer Engineering (M.Sc.)

## Slide 2 — Problem
- LLMs power customer bots, code assistants, RAG apps
- Prompt injection bypasses system instructions
- Keyword filters fail on paraphrases, Unicode tricks, indirect injection

## Slide 3 — Research Questions & Hypotheses
- **RQ1:** Does semantic analysis beat keyword filtering?
- **RQ2:** Does a 3-layer stack improve F1 while limiting false positives?
- **H1:** Embedding similarity > keyword lists for unknown variants
- **H2:** Layered defense > any single layer alone

## Slide 4 — Architecture
```
Input → [Layer 1 Semantic] → [Layer 2 Judge] → LLM → [Layer 3 Output Filter] → User
```
- Layer 1: text-embedding-3-small, cosine vs 150 patterns, threshold 0.85
- Layer 2: gpt-4o-mini → MALICIOUS / BENIGN
- Layer 3: regex + spaCy NER masking

## Slide 5 — Live Demo
- Streamlit panel + FastAPI backend
- Scenarios: benign, known attack, subtle jailbreak, PII masking

## Slide 6 — Evaluation Setup
- 500 malicious + 500 benign prompts
- Modes: keyword | semantic | full
- Metrics: F1, FP rate, mean/p95 latency

## Slide 7 — Results Table
Paste from `results/eval_report.json`:

| Mode | F1 | FP rate | Mean latency (ms) |
|------|-----|---------|---------------------|
| keyword | … | … | … |
| semantic | … | … | … |
| full | … | … | … |

Targets: F1 ≥ 0.90, FP < 5%, latency < 300 ms

## Slide 8 — Contributions
- Open middleware (no model retraining)
- Reusable attack pattern database
- Measurable comparison of defense layers

## Slide 9 — Limitations & Future Work
- OpenAI API dependency and cost
- English-centric NER
- Local embeddings, Turkish models, on-prem judge

## Slide 10 — Q&A
Repository: `llm-firewall` — README for reproducibility
