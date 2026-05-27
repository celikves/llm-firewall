"""Load .env and fix SSL certificates on Windows (certifi)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

try:
    import certifi

    ca_bundle = certifi.where()
    if os.path.isfile(ca_bundle):
        os.environ["SSL_CERT_FILE"] = ca_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
except ImportError:
    pass
