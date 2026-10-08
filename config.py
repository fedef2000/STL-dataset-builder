import os
from pathlib import Path

# Check HTTPS certificates the way a browser does, using the operating system's certificate store.
# Without this, sites that send an incomplete certificate chain fail with an SSL error in Python
# although they open fine in a browser.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_LATEX_DIR = DATA_DIR / "raw" / "latex"
RAW_PDF_DIR = DATA_DIR / "raw" / "pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
LOG_DIR = DATA_DIR / "logs"

CORPUS_FILE = DATA_DIR / "corpus.json"
LOG_FILE = LOG_DIR / "pipeline.log"

# Credentials live in .env (gitignored); copy .env.example to .env and fill it in.
# Variables already set in the environment take precedence over the file.
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.is_file():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

USER_EMAIL = os.environ.get("USER_EMAIL", "")                      # Enables the OpenAlex polite pool
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")          # Optional: higher daily OpenAlex quota
# Optional: lifts Semantic Scholar's anonymous rate limit (request a key at semanticscholar.org/product/api)
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

HEADERS = {"User-Agent": f"NL2STL-ModularBuilder/3.0 (mailto:{USER_EMAIL})"}
if OPENALEX_API_KEY:
    HEADERS["Authorization"] = f"Bearer {OPENALEX_API_KEY}"

# The 4 foundational STL papers (Hop 0 seeds)
SEED_DOIS = [
    "https://doi.org/10.1007/978-3-540-30206-3_12",  # Maler & Nickovic 2004 (STL) Monitoring Temporal Properties of Continuous Signals
    "https://doi.org/10.1007/978-3-642-15297-9_9",   # Donze & Maler 2010 (Quantitative STL) Robust Satisfaction of Temporal Logic over Real-Valued Signals
    "https://doi.org/10.1016/j.tcs.2009.06.021",     # Fainekos & Pappas 2009 (Robustness / MTL-STL) Robustness of temporal logic specifications for continuous-time signals
    "https://doi.org/10.1007/978-3-642-14295-6_17",  # Donze 2010 (Breach Toolbox) Breach, A Toolbox for Verification and Parameter Synthesis of Hybrid Systems
]

# Default keyword queries for --mode keywords
DEFAULT_KEYWORDS = [
    "Signal Temporal Logic",
    "Metric Temporal Logic",
    "STL specification",
    "STL formulas",
]

for d in (RAW_LATEX_DIR, RAW_PDF_DIR, PROCESSED_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)