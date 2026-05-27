.PHONY: setup install api demo test eval precompute data

PYTHON ?= python3
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

api:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

demo:
	streamlit run dashboard.py

test:
	pytest tests/ -v

eval:
	python scripts/run_evaluation.py --limit 50 --modes keyword semantic full

eval-full:
	python scripts/run_evaluation.py --modes keyword semantic full
