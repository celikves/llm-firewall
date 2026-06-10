# Multi-Layer LLM Firewall

Middleware-style security for LLM applications against **prompt injection**. Three layers: semantic similarity, judge LLM, and output PII filtering.

| Layer | Module | Method |
|-------|--------|--------|
| 1 | `core/semantic_analyzer.py` | OpenAI embeddings + cosine similarity (100 DB patterns) |
| 2 | `core/judge_model.py` | GPT-4o-mini → `MALICIOUS` / `BENIGN` |
| 3 | `core/output_filter.py` | Regex + spaCy NER masking |

**RAG extension** (separate API on port 8001): retrieval index poisoning experiments with **L0 context guard** on retrieved chunks and **L3 exfil filter** on LLM output. See [docs/RAG_METHODOLOGY.md](docs/RAG_METHODOLOGY.md).

---

## Requirements

- **Python 3.10–3.12** (3.11 recommended)
- **OpenAI API key** with access to `text-embedding-3-small` and `gpt-4o-mini`
- ~500 MB disk (dependencies + spaCy model)

---

## Configuration

Copy the example env file and set your key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
SEMANTIC_THRESHOLD=0.85
JUDGE_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for Layer 1–2 and evaluation |
| `SEMANTIC_THRESHOLD` | Cosine similarity block threshold (default `0.85`) |
| `JUDGE_MODEL` | Chat model for Layer 2 |
| `EMBEDDING_MODEL` | Embedding model for Layer 1 |

Never commit `.env` to version control.

---

## Setup

### macOS / Linux

```bash
git clone <your-repo-url> llm-firewall
cd llm-firewall
chmod +x scripts/setup.sh
./scripts/setup.sh
source .venv/bin/activate
```

Or with Make:

```bash
make setup
source .venv/bin/activate
```

**spaCy (if setup script fails):**

```bash
python -m spacy download en_core_web_sm
# fallback:
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

### Windows (PowerShell)

```powershell
cd llm-firewall
.\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
```

---

## First-time data

The repo includes `data/known_attacks.json` (100 DB patterns + precomputed embeddings). To regenerate:

```bash
make data
# or manually:
python scripts/generate_attack_patterns.py
python scripts/build_eval_dataset.py
python scripts/generate_pii_eval.py
python scripts/reuse_embeddings.py   # reuse cached embeddings
# python scripts/precompute_embeddings.py  # if patterns changed (requires API key)
```

**Data split (leakage-free):**
- 100 patterns → L1 embedding DB (`known_attacks.json`)
- 50 patterns → holdout eval only (`eval_holdout.json`)
- 52 patterns → literature reference seeds (eval_unseen)

---

## Run

**Terminal 1 — API**

```bash
uvicorn app:app --reload --port 8000
# macOS/Linux with Make:
make api
```

**Terminal 2 — Demo dashboard (English UI)**

```bash
streamlit run dashboard.py
# macOS/Linux with Make:
make demo
```

- API docs: http://127.0.0.1:8000/docs  
- Dashboard: http://localhost:8501  

---

## Verify installation

```bash
pytest tests/ -v
# or: make test
```

---

## Evaluation (thesis metrics)

Pilot (50 samples per split):

```bash
python scripts/run_evaluation.py --limit 50 --modes keyword semantic judge full
# or: make eval
```

Full thesis report (requires `OPENAI_API_KEY`):

```bash
make thesis-report
```

This runs: ablation eval → statistical analysis → threshold/ROC → PII eval.

Outputs (git-ignored, regenerated locally):

- `results/eval_report.json` — F1, FPR, latency per mode and split
- `results/eval_predictions.json` — raw predictions for McNemar tests
- `results/statistical_report.json` — bootstrap CI, McNemar, category breakdown
- `results/threshold_sweep.json`, `results/roc_curve.png`
- `results/pii_eval_report.json`
- `results/confusion_matrix.png`, `results/category_breakdown.png`

| Mode | Purpose |
|------|---------|
| `keyword` | Baseline (H1) |
| `semantic` | Layer 1 only (H1) |
| `judge` | Layer 2 only (H2) |
| `full` | Layer 1 + 2 (H2) |

| Split | Purpose |
|-------|---------|
| `eval_seen` | Holdout paraphrases (known attack types) |
| `eval_unseen` | Literature + novel variants (unseen attacks) |
| `combined` | Full 1000-sample benchmark |

See [docs/THESIS_METHODOLOGY.md](docs/THESIS_METHODOLOGY.md) for full experimental design.

---

## RAG module

Separate from the firewall on port 8000. Requires `OPENAI_API_KEY` and seeded Chroma index.

```bash
make rag-seed          # index benign + poisoned corpora → chroma_db/
make rag-eval          # bulk poisoning metrics → results/poisoning_eval.json
make rag-demo-trace    # 3 demo scenarios with LangSmith tracing
make rag-api           # FastAPI on http://127.0.0.1:8001
make eval-exfil        # L3 URL/exfil phrase metrics
```

Example request:

```bash
curl -X POST http://localhost:8001/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the refund policy?","collection":"rag_poisoned","policy":"strip","call_llm":false}'
```

LangSmith (optional): set `RAG_TRACE_ENABLED=true` and LangSmith vars in `.env`, then `make rag-demo-trace`.

---

## Project structure

```
llm-firewall/
├── app.py                      # FastAPI firewall (/verify, /filter-output) :8000
├── app_rag.py                  # FastAPI RAG pipeline (/rag/query) :8001
├── dashboard.py                # Streamlit demo
├── Makefile                    # macOS/Linux shortcuts
├── .env.example                # Configuration template
├── core/                       # Security layers
├── data/
│   ├── known_attacks.json      # 100 DB patterns + embeddings
│   ├── attack_patterns_all.json
│   ├── eval_holdout.json
│   ├── eval_seen.json          # 200 malicious (holdout paraphrases)
│   ├── eval_unseen.json        # 300 malicious (literature/novel)
│   ├── eval_benign.json        # 500 benign
│   ├── eval_dataset.json       # 1000 combined
│   ├── pii_eval.json           # Layer 3 PII eval (~100 samples)
│   ├── exfil_eval.json         # RAG L3 exfil eval
│   └── rag_corpus/             # benign + poisoned .txt for Chroma seed
├── scripts/
│   ├── setup.sh
│   ├── precompute_embeddings.py
│   ├── reuse_embeddings.py
│   ├── generate_attack_patterns.py
│   ├── build_eval_dataset.py
│   ├── generate_pii_eval.py
│   ├── run_evaluation.py
│   ├── run_statistical_analysis.py
│   ├── threshold_sweep.py
│   ├── evaluate_output_filter.py
│   ├── evaluate_exfil_filter.py
│   ├── seed_rag_index.py
│   └── run_poisoning_eval.py
├── docs/
│   ├── PRESENTATION.md
│   ├── THESIS_METHODOLOGY.md
│   └── RAG_METHODOLOGY.md
└── results/                    # Generated metrics (local only)
```

---

## Make targets (macOS / Linux)

| Command | Action |
|---------|--------|
| `make setup` | Run `scripts/setup.sh` |
| `make api` | Start FastAPI on port 8000 |
| `make demo` | Start Streamlit dashboard |
| `make test` | Run pytest |
| `make eval` | Pilot evaluation (50 samples, all modes) |
| `make eval-full` | Full ablation on all splits |
| `make eval-stats` | Bootstrap CI + McNemar tests |
| `make eval-threshold` | ROC/AUC + threshold sweep |
| `make eval-pii` | Layer 3 PII metrics |
| `make thesis-report` | Full thesis evaluation pipeline |
| `make data` | Regenerate patterns + eval datasets |
| `make precompute` | Rebuild attack embeddings |
| `make rag-seed` | Seed Chroma (`rag_clean` + `rag_poisoned`) |
| `make rag-eval` | RAG poisoning bulk eval |
| `make rag-demo-trace` | Traced demo scenarios (LangSmith) |
| `make rag-api` | RAG FastAPI on port 8001 |
| `make eval-exfil` | RAG L3 exfil filter metrics |

---

## Presentation

See [docs/PRESENTATION.md](docs/PRESENTATION.md) for a jury slide outline.

Demo flow: benign → known attack (Layer 1) → subtle jailbreak (Layer 2) → PII masking (Layer 3).

---

## Limitations

- Depends on OpenAI API (latency and cost).
- spaCy `en_core_web_sm` is English-centric.
- Ambiguous judge responses default to `MALICIOUS` (safe side).

---

## Author

Vesile Çelik — Ege University, Computer Engineering (M.Sc.)  
Thesis: *Multi-Layer LLM Firewall — Defense-in-Depth Against Prompt Injection*
