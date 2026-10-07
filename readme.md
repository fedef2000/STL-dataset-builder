# NL-to-STL Dataset Builder

A modular, resumable pipeline for discovering, harvesting, auditing licenses, and extracting **(Natural Language Requirement, Signal Temporal Logic Formula)** pairs from academic Cyber-Physical Systems (CPS) and formal verification literature.

---

## Key Features

* **Multi-Source & Multi-Hop Paper Discovery:**
  * **1-Hop & 2-Hop Citation Graph Crawling:** Discovers papers citing the foundational STL literature (Maler & Nickovic 2004, Donzé & Maler 2010, Fainekos & Pappas 2009, Breach 2010) via OpenAlex, with batching and local relevance filtering to save API credits.
  * **Direct Keyword Harvesting:** Queries both the arXiv API and OpenAlex by keyword (`"Signal Temporal Logic"`, `"Metric Temporal Logic"`, `"STL specification"`).
  * **Automatic Deduplication:** Deduplicates works across OpenAlex IDs, arXiv IDs, DOIs, and normalized titles inside a single source of truth (`data/corpus.json`).
* **Two-Tier Resumable Harvester:**
  * **Tier 1 (LaTeX `.tex` Sources):** Prioritizes raw `.tex` source bundles from `export.arxiv.org` to preserve exact mathematical macros ($\square_{[a,b]}$, $\lozenge_{[a,b]}$, $\mathcal{U}_{[a,b]}$) without OCR corruption.
  * **Tier 2 (Open-Access PDFs):** Falls back to Open Access PDF mirrors (HAL, Inria, Dagstuhl, institutional repositories) and verifies `%PDF` magic bytes.
* **Strict Multi-Source License Auditing:**
  * Resolves the exact license for every paper by inspecting downloaded `.tex` headers, PDF metadata, arXiv OAI-PMH records, and OpenAlex locations.
  * Tracks license provenance and flags conflicts between publisher metadata and preprint source files.
* **Formula Estimation & Pair Extraction:**
  * Scans inline prose and benchmark tables (`\begin{table}`) for concrete STL formulas while filtering out BNF grammar/semantics definitions.
  * Normalizes diverse author macros (e.g., `\always{0}{200}`, `\mathcal{G}_{[0,200]}`) into canonical STL syntax.

---

## Project Structure

```text
STL_dataset_builder/
├── config.py                          # Central settings: paths, email, API keys, seed DOIs
├── requirements.txt                   # Project dependencies
├── migrate_to_modular.py              # One-time migration script for legacy files
│
├── data/                              # Local dataset storage (gitignored)
│   ├── corpus.json                    # Single Source of Truth (metadata, status, licenses)
│   ├── logs/
│   │   └── pipeline.log               # Timestamped execution logs
│   ├── raw/
│   │   ├── latex/                     # Extracted .tex folders: data/raw/latex/{paper_id}/
│   │   └── pdfs/                      # Downloaded PDFs:        data/raw/pdfs/{paper_id}.pdf
│   └── processed/
│       ├── candidates.json            # Raw extracted (NL context, STL formula) candidates
│       └── final_dataset.json         # Cleaned & canonicalized (NL, STL) dataset
│
├── src/                               # Reusable Python modules
│   ├── storage.py                     # CorpusStore class (deduplication & safe JSON persistence)
│   ├── discovery/
│   │   ├── openalex_client.py         # 1-hop/2-hop citation crawler & OpenAlex search
│   │   └── keyword_search.py          # Direct arXiv API keyword harvester
│   ├── harvesting/
│   │   └── downloader.py              # Resumable .tex & .pdf downloader + S2/HAL recovery
│   ├── licensing/
│   │   ├── resolver.py                # Deep license scanner (.tex, PDF, arXiv OAI, OpenAlex)
│   │   └── stats.py                   # License tier classification & reporting tables
│   └── analysis/
│       ├── estimator.py               # Counts concrete, table, and symbolic STL formulas
│       └── extractor.py               # Extracts and canonicalizes (NL, STL) pairs
│
└── scripts/                           # Executable CLI entrypoints
    ├── 01_build_corpus.py             # Step 1: Discover papers (citations & keywords)
    ├── 02_download_papers.py          # Step 2: Download .tex bundles and fallback PDFs
    ├── 03_audit_and_print_licenses.py # Step 3: Verify licenses & print statistical tables
    └── 04_estimate_formulas.py        # Step 4: Estimate & extract (NL, STL) pairs

```

---

## Installation & Configuration

### 1. Install Dependencies

Create a virtual environment and install the required packages:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install requests pymupdf

```

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your email address and (optionally) your API keys. `.env` is gitignored and is loaded by `config.py`:

```bash
USER_EMAIL=your.name@university.edu        # Enables OpenAlex Polite Pool
OPENALEX_API_KEY=your_free_openalex_key    # Optional: Increases daily quota 10x (get at openalex.org)
SEMANTIC_SCHOLAR_API_KEY=your_s2_key       # Optional: Lifts the anonymous rate limit (semanticscholar.org/product/api)

```

---

## Pipeline Usage

All steps read from and update **`data/corpus.json`** incrementally. You can interrupt (`Ctrl+C`) and resume any script at any time without losing progress.

### Step 1: Build & Expand the Paper Corpus

Discover papers via 1-hop foundational citations, 2-hop citation cycles, or keyword searches:

```bash
# 1A. Fetch Hop-1 papers citing the 4 foundational STL papers
python scripts/01_build_corpus.py --mode citations --hops 1

# 1B. Expand to Hop-2 (papers citing Hop-1 papers that have >= 5 citations)
python scripts/01_build_corpus.py --mode citations --hops 2 --min-hop1-citations 5

# 1C. Discover additional preprints and papers via keywords (arXiv + OpenAlex)
python scripts/01_build_corpus.py --mode keywords --keywords "Signal Temporal Logic" "Metric Temporal Logic" "STL specification"

# Run all discovery modes together
python scripts/01_build_corpus.py --mode all --hops 2

```

### Step 2: Download Papers Locally (`.tex` & `.pdf`)

Downloads raw LaTeX source files (`data/raw/latex/{paper_id}/`) whenever available on arXiv, or falls back to Open Access PDFs (`data/raw/pdfs/{paper_id}.pdf`):

```bash
python scripts/02_download_papers.py

```

### Step 3: Audit Exact Licenses & Print Statistics

Scans local `.tex` files, PDF metadata, and arXiv OAI-PMH headers to verify exact paper licenses, flags any conflicts with OpenAlex metadata, updates `data/corpus.json`, and prints a full breakdown report:

```bash
python scripts/03_audit_and_print_licenses.py

```

### Step 4: Estimate & Extract `(NL, STL)` Pairs

Scans all downloaded `.tex` folders and `.pdf` files to count and extract concrete STL specifications, benchmark table rows, and parametric templates:

```bash
python scripts/04_estimate_formulas.py

```

---

## Data Schema (`data/corpus.json`)

Each entry in `data/corpus.json` follows a standardized schema tracking discovery provenance, local file state, and multi-source license resolution:

```json
{
  "W1511164163": {
    "paper_id": "W1511164163",
    "openalex_id": "[https://openalex.org/W1511164163](https://openalex.org/W1511164163)",
    "arxiv_id": "1409.1234",
    "doi": "[https://doi.org/10.1007/](https://doi.org/10.1007/)...",
    "title": "Learning and Designing Stochastic Processes from Logical Constraints",
    "year": 2015,
    "cited_by_count": 42,
    "is_oa": true,
    "discovery": {
      "methods": ["citation_hop_1"],
      "hop_distance": 1,
      "parent_ids": ["W1547304883"]
    },
    "urls": {
      "eprint_source": "[https://export.arxiv.org/e-print/1409.1234](https://export.arxiv.org/e-print/1409.1234)",
      "pdf_mirrors": ["[https://arxiv.org/pdf/1409.1234](https://arxiv.org/pdf/1409.1234)"]
    },
    "local_files": {
      "status": "downloaded_latex",
      "path": "data/raw/latex/W1511164163"
    },
    "license_info": {
      "effective_license": "cc-by-4.0",
      "effective_licenses_all": ["cc-by-4.0"],
      "effective_source": "tex_source",
      "tier": "permissive_cc",
      "has_conflict": false,
      "sources": {
        "openalex_locations": [],
        "tex_source": ["cc-by-4.0"],
        "arxiv_oai": ["[http://creativecommons.org/licenses/by/4.0/](http://creativecommons.org/licenses/by/4.0/)"],
        "pdf_metadata": []
      }
    }
  }
}

```

### License Tiers

Every paper and extracted `(NL, STL)` pair is categorized into one of four legal tiers:

1. **`permissive_cc` (`CC0`, `CC-BY`, `CC-BY-SA`):** Safe for verbatim redistribution and commercial/academic use with attribution.
2. **`restricted_cc` (`CC-BY-NC`, `CC-BY-ND`):** Permitted for non-commercial academic research; requires paraphrasing if used in derivative commercial datasets.
3. **`custom_or_arxiv` (`arXiv non-exclusive`, HAL, institutional repository):** Governed by Text & Data Mining (TDM) research exceptions; mathematical formulas are non-copyrightable facts, and natural language context should be normalized/paraphrased before redistribution.
4. **`unspecified`:** License not declared in metadata or source files.
