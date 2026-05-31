# Thesis Methodology — Multi-Layer LLM Firewall

This document supports thesis Chapters 3–4 (Methodology and Evaluation).  
Author: Vesile Çelik — Ege University, Computer Engineering (M.Sc.)

---

## 1. Threat Model

### 1.1 Assets
- System prompts and hidden instructions
- User PII in model outputs (email, phone, payment data, API keys)
- Application logic and downstream tool access

### 1.2 Attack Surface
- **Direct prompt injection:** User overrides system instructions in the same message
- **Jailbreaks:** Role-play and policy-bypass framing (DAN, developer mode)
- **Encoding evasion:** Unicode homoglyphs, Base64, multilingual variants
- **Indirect injection:** Malicious content in RAG documents, emails, web pages
- **Social engineering:** Authority impersonation, false compliance requests

### 1.3 Assumptions
- Attacker can send arbitrary text to the LLM input channel
- The firewall sits as middleware **before** the target LLM (input) and **after** generation (output)
- OpenAI API is available for embeddings and judge inference

### 1.4 Out of Scope
- Multi-turn conversational attacks across many sessions
- Image/OCR and audio-based injection
- Model weight poisoning or fine-tuning attacks
- Agentic tool-chain exploitation beyond text-level indirect injection

---

## 2. System Architecture

```
Input → [L1 Semantic] → [L2 Judge] → LLM → [L3 Output Filter] → User
```

| Layer | Module | Method | Latency target |
|-------|--------|--------|----------------|
| L1 | `core/semantic_analyzer.py` | OpenAI `text-embedding-3-small`, cosine similarity vs 100 DB patterns, threshold 0.85 | ~8 ms (cached) |
| L2 | `core/judge_model.py` | `gpt-4o-mini` → MALICIOUS / BENIGN | ~200 ms |
| L3 | `core/output_filter.py` | Regex + spaCy NER masking | ~5 ms |

Short-circuit: if L1 blocks, L2 is skipped.

---

## 3. Experimental Design

### 3.1 Data Leakage Prevention

**Problem (prior version):** 350/500 malicious eval samples were identical to L1 pattern DB strings, inflating semantic F1.

**Fix:**
- **100 patterns** → L1 embedding database (`data/known_attacks.json`)
- **50 patterns** → holdout only (`data/eval_holdout.json`), never embedded
- **52 patterns** → literature reference seeds (`split=reference`), eval_unseen only

### 3.2 Evaluation Splits

| Dataset | N | Purpose |
|---------|---|---------|
| `eval_seen.json` | 200 malicious | Paraphrases of holdout patterns — tests generalization to known attack *types* |
| `eval_unseen.json` | 300 malicious | Literature-curated + synthetic novel variants — tests H1 on unseen attacks |
| `eval_benign.json` | 500 benign | False-positive resistance (includes security-adjacent edge cases) |
| `eval_dataset.json` | 1000 combined | Full ablation benchmark |

Each sample: `{ id, text, label, category, source }`.

### 3.3 Ablation Modes

| Mode | Layers | Hypothesis |
|------|--------|------------|
| `keyword` | Regex + keyword lists | H1 baseline |
| `semantic` | L1 only | H1 test |
| `judge` | L2 only | H2 single-layer |
| `full` | L1 + L2 | H2 layered defense |

### 3.4 Reproducibility
- `random.seed(42)` in all dataset builders
- Environment variables in `.env` (threshold, models)
- Run full pipeline: `make thesis-report`

---

## 4. Metrics

### 4.1 Classification (L1/L2)
- **Precision, Recall, F1** on malicious class
- **False Positive Rate (FPR):** FP / (FP + TN) on benign samples
- **Latency:** mean, p50, p95 (ms)

### 4.2 Targets
- F1 ≥ 0.90
- FPR < 0.05
- Mean latency < 300 ms per request

### 4.3 Layer 3 (PII)
- Span-level **precision, recall, F1** on `data/pii_eval.json`
- Target: F1 ≥ 0.90

### 4.4 Statistical Tests
- **Bootstrap 95% CI** (1000 iterations) for F1 and FPR
- **McNemar test** for paired classifier comparison:
  - H1: `keyword` vs `semantic` on `eval_unseen`
  - H2: `semantic` vs `full`; `judge` vs `full`
- Decision criterion: p < 0.05

### 4.5 Threshold Analysis (L1)
- Sweep threshold 0.70–0.95 (step 0.05)
- ROC curve and AUC on combined eval set
- Justify default 0.85 via F1/FPR trade-off

---

## 5. Hypothesis Test Plan

### H1: Semantic > Keyword for unknown variants
- **Test set:** `eval_unseen`
- **Comparison:** McNemar(`keyword`, `semantic`)
- **Expected:** semantic F1 > keyword F1, p < 0.05

### H2: Layered defense > single layers
- **Test set:** `combined`
- **Comparisons:** McNemar(`semantic`, `full`), McNemar(`judge`, `full`)
- **Expected:** full F1 ≥ max(semantic, judge) with FPR < 5%

---

## 6. Results Tables (Template)

Paste from `results/eval_report.json` after `make thesis-report`:

### Table 1 — Ablation on Combined Set (N=1000)

| Mode | F1 | FPR | Mean latency (ms) |
|------|-----|-----|-------------------|
| keyword | … | … | … |
| semantic | … | … | … |
| judge | … | … | … |
| full | … | … | … |

### Table 2 — Generalization (eval_unseen + benign)

| Mode | F1 | FPR | 95% CI F1 |
|------|-----|-----|-----------|
| keyword | … | … | […, …] |
| semantic | … | … | […, …] |
| full | … | … | […, …] |

### Table 3 — McNemar Tests

| Comparison | b | c | χ² | p-value | Significant? |
|------------|---|---|-----|---------|--------------|
| keyword vs semantic (H1) | … | … | … | … | … |
| semantic vs full (H2) | … | … | … | … | … |

### Table 4 — Layer 3 PII Filter

| Metric | Value |
|--------|-------|
| Precision | … |
| Recall | … |
| F1 | … |

### Table 5 — Category Breakdown (full mode, eval_unseen malicious)

| Category | F1 | Recall |
|----------|-----|--------|
| direct_injection | … | … |
| jailbreak | … | … |
| encoding_evasion | … | … |
| indirect_injection | … | … |
| social_engineering | … | … |

---

## 7. Limitations

1. **OpenAI dependency:** Embeddings and judge require API access and incur cost
2. **English-centric NER:** spaCy `en_core_web_sm` limits multilingual PII detection
3. **Synthetic eval data:** ~70% of malicious samples are template-generated; external benchmark is a curated subset, not a full public benchmark import
4. **No end-to-end LLM proxy:** Evaluation tests firewall modules, not a live ChatGPT integration
5. **Static pattern DB:** Novel zero-day attacks may require community updates to `known_attacks.json`

---

## 8. Future Work

- Unicode/homoglyph normalization pre-processing layer
- Local embeddings (sentence-transformers) for on-prem deployment
- Multi-turn and agentic injection test suites
- Turkish NER model for Layer 3
- Full LLM gateway with audit logging and rate limiting

---

## 9. Reproduction Commands

```bash
# Setup
make setup && source .venv/bin/activate

# Regenerate data (no API needed for patterns/eval)
python scripts/generate_attack_patterns.py
python scripts/build_eval_dataset.py
python scripts/generate_pii_eval.py
python scripts/reuse_embeddings.py   # or precompute_embeddings.py with API key

# Full thesis evaluation (requires OPENAI_API_KEY)
make thesis-report
```

Outputs:
- `results/eval_report.json`
- `results/eval_predictions.json`
- `results/statistical_report.json`
- `results/threshold_sweep.json`
- `results/roc_curve.png`
- `results/category_breakdown.png`
- `results/pii_eval_report.json`
