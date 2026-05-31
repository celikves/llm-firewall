# Jury Presentation Outline (English slides)

## Slide 1 — Title
**Multi-Layer LLM Firewall: Defense-in-Depth Against Prompt Injection**

Vesile Çelik — Ege University, Computer Engineering (M.Sc.)

## Slide 2 — Problem
- LLMs power customer bots, code assistants, RAG apps
- Prompt injection bypasses system instructions
- Keyword filters fail on paraphrases, Unicode tricks, indirect injection

## Slide 3 — Research Questions & Hypotheses
- **RQ1:** Does semantic analysis beat keyword filtering on unseen attacks?
- **RQ2:** Does a layered stack (L1+L2) outperform single layers?
- **H1:** Embedding similarity > keyword lists for unknown variants
- **H2:** Layered defense > any single layer alone (higher F1, controlled FPR)

## Slide 4 — Architecture
```
Input → [Layer 1 Semantic] → [Layer 2 Judge] → LLM → [Layer 3 Output Filter] → User
```
- Layer 1: text-embedding-3-small, cosine vs **100 DB patterns**, threshold 0.85
- Layer 2: gpt-4o-mini → MALICIOUS / BENIGN
- Layer 3: regex + spaCy NER masking

## Slide 5 — Methodology (Data Leakage Fix)
- **Before:** 350/500 eval attacks = exact DB copies → inflated L1 F1
- **After:** 100 DB patterns | 50 holdout | 52 literature reference
- Splits: `eval_seen` (200) | `eval_unseen` (300) | `eval_benign` (500)

## Slide 6 — Live Demo
- Streamlit panel + FastAPI backend
- Scenarios: benign, known attack, subtle jailbreak, PII masking

## Slide 7 — Evaluation Setup
- 500 malicious + 500 benign (combined)
- Modes: keyword | semantic | **judge** | full
- Metrics: F1, FPR, latency, bootstrap CI, McNemar test, ROC/AUC

## Slide 8 — Results: Ablation (Combined, N=1000)

| Mode | F1 | FPR | Mean latency (ms) |
|------|-----|-----|---------------------|
| keyword | … | … | … |
| semantic | … | … | … |
| judge | … | … | … |
| full | … | … | … |

Targets: F1 ≥ 0.90, FPR < 5%, latency < 300 ms

## Slide 9 — Results: Generalization (eval_unseen)

| Mode | F1 | FPR | 95% CI F1 |
|------|-----|-----|-----------|
| keyword | … | … | […, …] |
| semantic | … | … | […, …] |
| full | … | … | […, …] |

## Slide 10 — Statistical Significance

| Comparison | p-value | Result |
|------------|---------|--------|
| keyword vs semantic (H1) | … | … |
| semantic vs full (H2) | … | … |

## Slide 11 — Category Breakdown & ROC
- Bar chart: F1 by attack category (direct, jailbreak, encoding, indirect, social)
- ROC/AUC for Layer 1 threshold selection (0.85 justified)

## Slide 12 — Layer 3 PII Filter

| Metric | Value | Target |
|--------|-------|--------|
| Precision | … | — |
| Recall | … | — |
| F1 | … | ≥ 0.90 |

## Slide 13 — Contributions
- Open middleware (no model retraining)
- Reproducible eval with leakage-free splits
- Statistical validation of layered defense (McNemar + bootstrap CI)
- Reusable attack pattern database with categories

## Slide 14 — Limitations & Future Work
- OpenAI API dependency and cost
- English-centric NER; local embeddings; Turkish models
- Multi-turn / agentic injection; full LLM gateway

## Slide 15 — Q&A
Repository: `llm-firewall` — see `docs/THESIS_METHODOLOGY.md` for full reproduction
