#!/usr/bin/env bash
# macOS / Linux setup for llm-firewall
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MIN_PYTHON="3.10"
SPACY_MODEL_URL="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

python_meets_minimum() {
  "$1" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null
}

resolve_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    echo "$PYTHON"
    return
  fi
  local candidate
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_meets_minimum "$candidate"; then
      echo "$candidate"
      return
    fi
  done
  return 1
}

if ! PYTHON="$(resolve_python)"; then
  echo "error: Python ${MIN_PYTHON}+ is required (spaCy 3.8+ does not support 3.9)." >&2
  echo "  Install Python 3.11 (e.g. pyenv install 3.11.12) and run:" >&2
  echo "    PYTHON=python3.11 ./scripts/setup.sh" >&2
  exit 1
fi

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "==> Using $PYTHON (Python $PY_VERSION)"

if [[ -x .venv/bin/python ]] && ! .venv/bin/python -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "==> Removing existing .venv (Python 3.10+ required)"
  rm -rf .venv
fi

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
