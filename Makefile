.PHONY: setup install api demo dashboard test eval eval-full eval-stats eval-threshold eval-pii eval-exfil thesis-report precompute data \
	rag-seed rag-eval rag-demo-trace langsmith-figures rag-api

# Prefer 3.11+ when default python3 is 3.9 (see scripts/setup.sh)
PYTHON ?= $(shell for p in python3.12 python3.11 python3.10 python3; do \
	$$p -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null && echo $$p && break; done)
VENV = .venv/bin/activate

setup:
	bash scripts/setup.sh

install:
	pip install -r requirements.txt

precompute:
	python scripts/precompute_embeddings.py

data:
	python scripts/generate_attack_patterns.py
	python scripts/build_eval_dataset.py
	python scripts/generate_pii_eval.py
	python scripts/reuse_embeddings.py

api:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

demo dashboard:
	@echo "Dashboard: http://localhost:8501  (tabs: Firewall :8000 | RAG :$(RAG_API_PORT))"
	@echo "Start APIs first: make api  AND  make rag-api"
	streamlit run dashboard.py

test:
	pytest tests/ -v

eval:
	python scripts/run_evaluation.py --limit 50 --modes keyword semantic judge full

eval-full:
	python scripts/run_evaluation.py --modes keyword semantic judge full

eval-stats:
	python scripts/run_statistical_analysis.py

eval-threshold:
	python scripts/threshold_sweep.py

eval-pii:
	python scripts/evaluate_output_filter.py

eval-exfil:
	$(RAG_PYTHON) scripts/evaluate_exfil_filter.py

thesis-report: eval-full eval-stats eval-threshold eval-pii
	@echo "Thesis reports written to results/"

RAG_PYTHON ?= .venv/bin/python
RAG_API_PORT ?= 8010

rag-seed:
	$(RAG_PYTHON) scripts/seed_rag_index.py --mode clean
	$(RAG_PYTHON) scripts/seed_rag_index.py --mode poisoned

rag-eval:
	RAG_TRACE_ENABLED=false $(RAG_PYTHON) scripts/run_poisoning_eval.py

rag-demo-trace:
	RAG_TRACE_ENABLED=true $(RAG_PYTHON) scripts/run_poisoning_eval.py --demo-only

langsmith-figures:
	RAG_TRACE_ENABLED=true $(RAG_PYTHON) scripts/run_langsmith_figures.py

rag-api:
	@echo "RAG API :$(RAG_API_PORT) — LangSmith traces when LANGSMITH_TRACING=true in .env"
	uvicorn app_rag:app --reload --host 0.0.0.0 --port $(RAG_API_PORT)
