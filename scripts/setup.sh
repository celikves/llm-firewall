#!/usr/bin/env bash
# macOS / Linux setup for llm-firewall
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
SPACY_MODEL_URL="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

echo "==> Creating virtual environment..."
"$PYTHON" -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Installing spaCy English model..."
if ! python -m spacy download en_core_web_sm 2>/dev/null; then
  echo "    spacy download failed; installing wheel directly..."
  pip install "$SPACY_MODEL_URL"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — add your OPENAI_API_KEY"
else
  echo "==> .env already exists"
fi

if [[ ! -f data/known_attacks.json ]]; then
  echo "==> data/known_attacks.json missing."
  echo "    After setting OPENAI_API_KEY in .env, run:"
  echo "    python scripts/precompute_embeddings.py"
else
  echo "==> data/known_attacks.json found"
fi

echo ""
echo "Setup complete. Activate with:"
echo "  source .venv/bin/activate"
echo ""
echo "Verify:  pytest tests/ -v"
echo "API:     uvicorn app:app --reload --port 8000"
echo "Demo:    streamlit run dashboard.py"
