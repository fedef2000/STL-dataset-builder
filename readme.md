# NL-to-STL Dataset Builder

A modular, resumable pipeline that discovers academic papers on Signal Temporal Logic (STL), downloads their LaTeX sources or PDFs, audits their licences, and estimates how many STL formulas each one contains. It prepares the corpus for building a dataset of **(Natural Language Requirement, Signal Temporal Logic Formula)** pairs from Cyber-Physical Systems (CPS) and formal verification literature.

**Current state:** steps 1 to 4 (discovery, download, licence audit, formula estimation) are implemented. The extraction of the (requirement, formula) pairs themselves is not implemented yet.

---

## Key Features

* **Multi-Source & Multi-Hop Paper Discovery:**
  * **1-Hop & 2-Hop Citation Graph Crawling:** Discovers papers citing the foundational STL literature (Maler & Nickovic 2004, Donzé & Maler 2010, Fainekos & Pappas 2009, Breach 2010) via OpenAlex, with batching and local relevance filtering to save API credits. Each paper records which papers of the previous hop it cites (`parent_ids`).
  * **Direct Keyword Harvesting:** Queries both the arXiv API and OpenAlex by keyword (`"Signal Temporal Logic"`, `"Metric Temporal Logic"`, `"STL specification"`, `"STL formulas"`). OpenAlex results are kept only if their title or abstract matches the STL relevance terms.
  * **Automatic Deduplication:** Deduplicates works across OpenAlex IDs, arXiv IDs, DOIs, and normalized titles inside a single source of truth (`data/corpus.json`).
* **Resumable Harvester with Recovery:**
  * **Tier 1 (LaTeX Sources):** Prioritizes source bundles from `export.arxiv.org` to preserve exact mathematical macros ($\square_{[a,b]}$, $\lozenge_{[a,b]}$, $\mathcal{U}_{[a,b]}$) without OCR corruption. Keeps the `.tex`, `.sty`, `.cls` and `.def` files with their folder structure, so author macros defined outside the main file are not lost.
  * **Tier 2 (Recovery, optional):** For papers without a working arXiv source, asks Semantic Scholar, the arXiv title search and HAL for an arXiv version or an open PDF.
  * **Tier 3 (Open-Access PDFs):** Falls back to Open Access PDF mirrors (HAL, Inria, Dagstuhl, institutional repositories) and verifies the `%PDF` magic bytes.
  * **Rate-Limit Handling:** Recovery lookups are paced, retried with backoff, and paused for 15 minutes when a service keeps refusing. Papers whose lookup was cut short are marked so they can be retried on their own.
  * **Descriptive Failure Reasons & Stats:** Every paper that could not be downloaded stores why, and `--stats` prints the breakdown for the whole corpus.
* **Strict Multi-Source License Auditing:**
  * Resolves the exact license for every downloaded paper by inspecting `.tex` headers, PDF metadata, arXiv OAI-PMH records, and OpenAlex locations.
  * Tracks license provenance and flags conflicts between publisher metadata and preprint source files.
* **Formula Yield Estimation:**
  * Counts temporal operators that carry a time interval (e.g. `\Box_{[0,5]}`, `\mathcal{G}_{[0,200]}`, `\always{0}{200}`), split into **concrete** (both bounds numeric) and **symbolic** (parametric bounds).
  * Recognises each paper's own operator macros (`\newcommand`, `\def`, `\DeclareMathOperator`, `\NewDocumentCommand`), including macros defined in terms of other macros.
  * Ignores commented-out lines, `comment` environments and `\iffalse ... \fi` blocks.
  * For PDF-only papers, falls back to a plain-text approximation that counts concrete formulas only.

---

## Project Structure

```text
STL_dataset_builder/
├── config.py                          # Central settings: paths, .env loading, seed DOIs, default keywords
├── .env.example                       # Template for the local .env file (email and API keys)
├── readme.md
│
├── data/
│   ├── corpus.json                    # Single Source of Truth (metadata, status, licenses) - tracked in git
│   ├── logs/                          # (gitignored)
│   │   └── pipeline.log               # Timestamped log of the download step
│   ├── raw/                           # (gitignored)
│   │   ├── latex/                     # Extracted source folders: data/raw/latex/{paper_id}/
│   │   └── pdfs/                      # Downloaded PDFs:          data/raw/pdfs/{paper_id}.pdf
│   └── processed/                     # (gitignored) derived files, e.g. a hand-labelled evaluation set
│
├── src/                               # Reusable Python modules
│   ├── storage.py                     # CorpusStore class (deduplication & atomic JSON persistence)
│   ├── discovery/
│   │   ├── openalex_client.py         # 1-hop/2-hop citation crawler & OpenAlex keyword search
│   │   └── keyword_search.py          # Direct arXiv API keyword harvester
│   ├── harvesting/
│   │   └── downloader.py              # LaTeX & PDF downloader, Semantic Scholar/arXiv/HAL recovery, rate-limit handling
│   ├── licensing/
│   │   ├── resolver.py                # Deep license scanner (.tex, PDF, arXiv OAI, OpenAlex)
│   │   └── stats.py                   # License tier classification & reporting tables
│   └── analysis/
│       └── estimator.py               # Counts concrete and symbolic STL formulas (macro-aware)
│
└── scripts/                           # Executable CLI entrypoints
    ├── 01_build_corpus.py             # Step 1: Discover papers (citations & keywords)
    ├── 02_download_papers.py          # Step 2: Download LaTeX sources and fallback PDFs; download stats
    ├── 03_audit_and_print_licenses.py # Step 3: Verify licenses & print statistical tables
    └── 04_estimate_formulas.py        # Step 4: Estimate the STL formula yield per paper

```

---

## Installation & Configuration

### 1. Install Dependencies

Requires Python 3.10 or newer. Create a virtual environment and install the required packages:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install requests pymupdf truststore

```

* `requests`: all HTTP calls.
* `pymupdf`: reads PDF text and metadata (license audit, formula estimation).
* `truststore`: makes Python check HTTPS certificates with the operating system's certificate store, like a browser. Without it the pipeline still runs, but some repositories that send an incomplete certificate chain fail with `SSL Certificate Error`.

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your email address and (optionally) your API keys. `.env` is gitignored and is loaded by `config.py`; variables already set in the environment take precedence over the file:

```bash
USER_EMAIL=your.name@university.edu        # Enables OpenAlex Polite Pool
OPENALEX_API_KEY=your_free_openalex_key    # Optional: Increases daily quota 10x (get at openalex.org)
SEMANTIC_SCHOLAR_API_KEY=your_s2_key       # Optional: Lifts the anonymous rate limit (semanticscholar.org/product/api)

```

Without a Semantic Scholar key, the recovery lookups of step 2 are likely to be refused; the download script reports the state of that service at start-up when `--with-recovery` is used.

---

## Pipeline Usage

All steps read from and update **`data/corpus.json`** incrementally. You can interrupt (`Ctrl+C`) and resume any script at any time without losing progress.

Every script also accepts `-h` / `--help`, which prints its flags and exits.

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

| Flag | Default | What it does |
|---|---|---|
| `--mode {citations,keywords,all}` | `citations` | Which discovery to run: the citation crawl, the keyword search (arXiv + OpenAlex), or both. |
| `--hops {1,2}` | `1` | Citation depth. `1` fetches (or refreshes) the papers citing the 4 seed papers. `2` also fetches the papers citing those Hop-1 papers; Hop-1 itself is only fetched if it is not in the corpus yet. Ignored with `--mode keywords`. |
| `--min-hop1-citations N` | `5` | With `--hops 2`: only Hop-1 papers with at least `N` citations are expanded. |
| `--hop2-require-stl-text` / `--no-hop2-require-stl-text` | on | With `--hops 2`: keep a Hop-2 paper only if its title or abstract matches the STL relevance terms. The `--no-` form keeps every Hop-2 paper (much larger, off-topic corpus). |
| `--keywords K [K ...]` | `"Signal Temporal Logic" "Metric Temporal Logic" "STL specification" "STL formulas"` | Search phrases for the keyword search. Quote each phrase. Ignored with `--mode citations`. |

### Step 2: Download Papers Locally (`.tex` & `.pdf`)

Downloads raw LaTeX source files (`data/raw/latex/{paper_id}/`) whenever available on arXiv, or falls back to Open Access PDFs (`data/raw/pdfs/{paper_id}.pdf`):

```bash
# Download every paper that has not been tried yet
python scripts/02_download_papers.py --with-recovery

# Show the download status of the whole corpus
python scripts/02_download_papers.py --stats

# Go back over papers whose recovery lookups were cut short by rate limiting
python scripts/02_download_papers.py --retry-rate-limited --with-recovery

# Go back over papers that failed on a network problem or a server error
python scripts/02_download_papers.py --retry-transient --with-recovery

```

Each run first compares `data/corpus.json` with the files on disk and corrects the recorded status. Without any flag, only papers that were never tried (`pending`) are downloaded.

| Flag | What it does |
|---|---|
| `--with-recovery` | For a paper without a working arXiv source, also asks Semantic Scholar (by DOI), the arXiv title search and HAL (by title) for an arXiv version or an open PDF. Slower: the lookups are paced to respect each service's rate limit. |
| `--retry-unavailable` | Also retries **every** paper marked `unavailable`, whatever the reason. |
| `--retry-rate-limited` | Also retries the `unavailable` papers whose recovery lookup was abandoned (rate limit, cooldown, or no answer). Only useful together with `--with-recovery`. |
| `--retry-transient` | Also retries the `unavailable` papers whose failure reason is a connection error, a timeout, HTTP 429 or HTTP 500/502/503/504. |
| `--limit N` | Processes only the first `N` papers of the queue (for testing). |
| `--stats` | Prints the status counts and failure reasons of the whole corpus, then exits. Nothing is downloaded. |
| `--relabel` | Rewrites the stored failure reasons in the current wording, prints the same report as `--stats`, then exits. Nothing is downloaded. |

`--retry-rate-limited` and `--retry-transient` can be combined; both are redundant with `--retry-unavailable`, which already includes those papers. `--stats` and `--relabel` take precedence over all the download flags.

#### Failure reasons

A paper that could not be downloaded gets `status: "unavailable"` and one of these `failure_reason` values in `data/corpus.json`. Reasons from PDF links are prefixed with `PDF Mirrors: ` and describe the last link tried.

| Failure reason | Meaning |
|---|---|
| `No Link Found (not open access)` | No arXiv source and no PDF link is known, and the paper is not open access. Nothing was attempted. |
| `No Link Found (open access, but no URL listed)` | Same, for a paper that OpenAlex marks as open access. |
| `No Link Found (lookup rate-limited, worth a retry)` | No link is known, but a recovery lookup was abandoned, so one may still exist. |
| `arXiv Error: HTTP 404 (Not Found)` / `HTTP 403 (Forbidden/Blocked)` / `HTTP <code>` | arXiv refused or does not have the source bundle. |
| `arXiv Error: Connection Timeout` / `Network/System Exception` | Network problem while fetching the arXiv bundle. |
| `Archive contained no .tex files` | The arXiv bundle was unpacked but holds no LaTeX. |
| `Invalid archive format or PDF only` | arXiv only has a PDF for this paper, or the bundle could not be read. |
| `HTTP 403 (Paywall or Bot Protection)` | The host refuses automated downloads. |
| `HTTP 404 (Dead Link)` / `HTTP 410 (Removed by Host)` | The file is gone. |
| `HTTP 401 (Login Required)` | The host asks for an account. |
| `HTTP 202 (Bot Protection Challenge)`, `HTTP 405`/`406`/`418 (Bot Protection)` | The host answered with an anti-bot page instead of the file. |
| `HTTP 429 (Rate Limited)` | The host asked to slow down. |
| `HTTP <code>` (e.g. 500, 502, 503) | Any other answer from the host, usually a server-side error. |
| `HTML Landing Page (Not a %PDF file)` | The link returned a web page instead of a PDF. |
| `Connection Timeout` | The host did not answer in time. |
| `SSL Certificate Error` | The host's HTTPS certificate is invalid (for example expired). |
| `Connection Error (Domain unreachable)` | The host could not be reached at all. |

A paper can also carry `recovery_rate_limited: true` next to any of these reasons; that is what `--retry-rate-limited` looks for.

### Step 3: Audit Exact Licenses & Print Statistics

Scans local `.tex` files, PDF metadata, and arXiv OAI-PMH headers to verify exact paper licenses, flags any conflicts with OpenAlex metadata, updates `data/corpus.json`, and prints a full breakdown report:

```bash
python scripts/03_audit_and_print_licenses.py

# Print the report again without re-scanning
python scripts/03_audit_and_print_licenses.py --skip-audit

```

| Flag | What it does |
|---|---|
| `--skip-audit` | Skips the scan and prints the report from the licences already stored in `data/corpus.json`. |
| `--limit N` | Audits only the first `N` downloaded papers (for testing). The report still covers the whole corpus. |

### Step 4: Estimate STL Formula Yield

Scans all downloaded `.tex` folders and `.pdf` files, counts concrete and symbolic STL formulas per paper, saves the counts under `formula_estimates` in `data/corpus.json`, and prints the 20 most promising papers:

```bash
python scripts/04_estimate_formulas.py

```

| Flag | What it does |
|---|---|
| `--limit N` | Scans only the first `N` downloaded papers (for testing). |

---

## Data Schema (`data/corpus.json`)

`data/corpus.json` is a JSON object keyed by paper ID. The ID is the OpenAlex work ID (`W...`) or, for preprints found only through the arXiv keyword search, `arxiv_<arxiv id>`. Each entry tracks discovery provenance, local file state, license resolution and formula estimates:

```json
{
  "W1511164163": {
    "paper_id": "W1511164163",
    "openalex_id": "https://openalex.org/W1511164163",
    "arxiv_id": "1409.1234",
    "doi": "https://doi.org/10.1007/...",
    "title": "Learning and Designing Stochastic Processes from Logical Constraints",
    "year": 2015,
    "cited_by_count": 42,
    "is_oa": true,
    "alternate_ids": [],
    "discovery": {
      "methods": ["citation_hop_1", "openalex_kw:Signal Temporal Logic"],
      "hop_distance": 1,
      "parent_ids": ["W1547304883"],
      "expanded_hop_2": true
    },
    "urls": {
      "eprint_source": "https://export.arxiv.org/e-print/1409.1234",
      "pdf_mirrors": ["https://arxiv.org/pdf/1409.1234"]
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
        "arxiv_oai": ["http://creativecommons.org/licenses/by/4.0/"],
        "pdf_metadata": []
      }
    },
    "formula_estimates": {
      "concrete": 12,
      "symbolic": 3
    }
  }
}

```

| Field | Notes |
|---|---|
| `alternate_ids` | Other OpenAlex IDs that were merged into this entry as duplicates. |
| `discovery.methods` | How the paper was found: `citation_hop_1`, `citation_hop_2`, `openalex_kw:<keyword>`, `arxiv_kw:<keyword>`. A paper can have several. |
| `discovery.hop_distance` | `1` or `2` for papers from the citation crawl, `null` for papers found only by keyword. |
| `discovery.parent_ids` | The papers of the previous hop that this paper cites (the seed papers for Hop-1). |
| `discovery.expanded_hop_2` | Set on Hop-1 papers whose citing papers have already been fetched. |
| `local_files.status` | `pending` (not tried yet), `downloaded_latex`, `downloaded_pdf` or `unavailable`. |
| `local_files.failure_reason` | Only for `unavailable` papers; see the failure reasons under Step 2. |
| `local_files.recovery_rate_limited` | `true` when a recovery lookup was abandoned, so the paper is worth retrying with `--retry-rate-limited`. |
| `license_info` | Written by Step 3. `effective_source` is `tex_source`, `pdf_metadata`, `arxiv_oai`, `openalex_locations` or `none`. |
| `formula_estimates` | Written by Step 4, for downloaded papers only. |

### License Tiers

Every paper is categorized into one of four legal tiers:

1. **`permissive_cc` (`CC0`, `CC-BY`, `CC-BY-SA`):** Safe for verbatim redistribution and commercial/academic use with attribution.
2. **`restricted_cc` (`CC-BY-NC`, `CC-BY-ND`):** Permitted for non-commercial academic research; requires paraphrasing if used in derivative commercial datasets.
3. **`custom_or_arxiv` (`arXiv non-exclusive`, HAL, institutional repository):** Governed by Text & Data Mining (TDM) research exceptions; mathematical formulas are non-copyrightable facts, and natural language context should be normalized/paraphrased before redistribution.
4. **`unspecified`:** License not declared in metadata or source files.
