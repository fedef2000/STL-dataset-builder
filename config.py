from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_LATEX_DIR = DATA_DIR / "raw" / "latex"
RAW_PDF_DIR = DATA_DIR / "raw" / "pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
LOG_DIR = DATA_DIR / "logs"

CORPUS_FILE = DATA_DIR / "corpus.json"
LOG_FILE = LOG_DIR / "pipeline.log"

USER_EMAIL = "federico.ferrari@ait.ac.at"
OPENALEX_API_KEY = "bsBCSjRR8mkCoERfh5chhh"

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