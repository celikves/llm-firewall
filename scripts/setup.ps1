# Windows setup for llm-firewall
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$SpacyWheel = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

Write-Host "==> Creating virtual environment..."
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

Write-Host "==> Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "==> Installing spaCy English model..."
python -m spacy download en_core_web_sm 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    spacy download failed; installing wheel directly..."
    pip install $SpacyWheel
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "==> Created .env from .env.example — add your OPENAI_API_KEY"
} else {
    Write-Host "==> .env already exists"
}

if (-not (Test-Path data\known_attacks.json)) {
    Write-Host "==> data\known_attacks.json missing."
    Write-Host "    After setting OPENAI_API_KEY in .env, run:"
    Write-Host "    python scripts\precompute_embeddings.py"
} else {
    Write-Host "==> data\known_attacks.json found"
}

Write-Host ""
Write-Host "Setup complete. Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Verify:  pytest tests/ -v"
Write-Host "API:     uvicorn app:app --reload --port 8000"
Write-Host "Demo:    streamlit run dashboard.py"
