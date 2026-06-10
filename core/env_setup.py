"""Load .env and fix SSL certificates on Windows (certifi)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def _apply_export_style_env_lines() -> None:
    """Parse `export KEY=value` lines that dotenv may skip on some setups."""
    if not ENV_PATH.is_file():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_apply_export_style_env_lines()
load_dotenv(ENV_PATH, override=False)

try:
    import certifi

    ca_bundle = certifi.where()
    if os.path.isfile(ca_bundle):
        os.environ["SSL_CERT_FILE"] = ca_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
except ImportError:
    pass
