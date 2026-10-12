# NL-to-STL Dataset Builder

A modular, resumable pipeline that discovers academic papers on Signal Temporal Logic (STL), downloads their LaTeX sources or PDFs, audits their licences, and estimates how many STL formulas each one contains. It prepares the corpus for building a dataset of **(Natural Language Requirement, Signal Temporal Logic Formula)** pairs from Cyber-Physical Systems (CPS) and formal verification literature.

**Current state:** steps 1 to 4 (discovery, download, licence audit, formula estimation) are implemented. The extraction of the (requirement, formula) pairs themselves is not implemented yet.

---

## Key Features

* **Multi-Source & Multi-Hop Paper Discovery:**
  * **1-Hop & 2-Hop Citation Graph Crawling:** Discovers papers citing the foundational STL literature (Maler & Nickovic 2004, Donzé & Maler 2010, Fainekos & Pappas 2009, Breach 2010) via OpenAlex, with batching and local relevance filtering to save API credits. Each paper records which papers of the previous hop it cites (`parent_ids`).
  * **Direct Keyword Harvesting:** Queries both the arXiv API and OpenAlex by keyword (`"Signal Temporal Logic"`, `"Metric Temporal Logic"`, `"STL specification"`, `"STL formulas"`). OpenAlex results are kept only if their title or abstract matches the STL relevance terms.
  * **Automatic Deduplication:** Deduplicates works across OpenAlex IDs, arXiv IDs, DOIs, and normalized titles inside a single source of truth (`data/corpus.json`).
  * **Enrichment:** Asks Semantic Scholar, the arXiv title search and HAL for the arXiv IDs and open PDF links that OpenAlex does not list. Each answer is recorded per paper, so no service is asked twice about the same paper, and a lookup that got no answer (rate limit, network problem) is repeated on the next run.
* **Resumable Harvester:**
  * **Tier 1 (LaTeX Sources):** Prioritizes source bundles from `export.arxiv.org` to preserve exact mathematical macros ($\square_{[a,b]}$, $\lozenge_{[a,b]}$, $\mathcal{U}_{[a,b]}$) without OCR corruption. Keeps the `.tex`, `.sty`, `.cls` and `.def` files with their folder structure, so author macros defined outside the main file are not lost.
  * **Tier 2 (Open-Access PDFs):** Falls back to Open Access PDF mirrors (HAL, Inria, Dagstuhl, institutional repositories) and verifies the `%PDF` magic bytes.
  * **Descriptive Failure Reasons & Stats:** Every paper that could not be downloaded stores why, and `--stats` prints the breakdown for the whole corpus.
* **Strict Multi-Source License Auditing:**
  * Resolves the exact license for every downloaded paper by inspecting `.tex` headers, PDF metadata, arXiv OAI-PMH records, and OpenAlex locations.
  * Tracks license provenance and flags conflicts between publisher metadata and preprint source files.
* **Formula Yield Estimation:**
  * Counts temporal operators that carry a time bound (e.g. `\Box_{[0,5]}`, `\mathcal{G}_{[0,200]}`, `\always{0}{200}`, `\Diamond_{\le 3}`), split into **concrete** (numeric bounds, including infinity) and **symbolic** (parametric bounds), and groups them into **formulas**: one per inline math span or display row.
  * Accepts closed, open, half-open and unbounded intervals (`[0,5]`, `(0,5)`, `[0,5)`, `[5,\infty)`), `\left[ \right]`, LaTeX spacing commands and time units (`[0.2s, 0.8s]`).
  * Covers future and past-time operators: box and diamond symbols and their variants (`\boxminus`, `\diamondminus`, ...), `G`/`F`/`U` letters, and named operators (`\always`, `\eventually`, `\until`, `\once`, `\since`, `\historically`, `\LTL...`).
  * Recognises each paper's own operator macros (`\newcommand`, `\def`, `\DeclareMathOperator`, `\NewDocumentCommand`), including macros defined in terms of other macros.
  * Ignores commented-out lines, `comment` environments, `\iffalse ... \fi` blocks, and `.tex` files that the main document does not `\input` (old drafts, unused files).
  * For PDF-only papers, falls back to the text layer of the PDF, where a formula is one text line. It recognises box and diamond glyphs (`□[0,5]`, `♦(0,∞)`, the past-time `⊟[1,2]`), the letters and words (`G[0,5]`, `U[0,∞)`, `Always[0,10]`), single bounds (`♦≤10`, `F≤100(x > 1)`), symbolic bounds (`□[a,b]`, `G[0,T]`), mathematical letters (`𝑭[0,20]`) and the digits `2` and `3` that the AMS symbol font leaves in place of a box and a diamond (`2[0,10](x ≤ 1.2)`). A bare `G`, `F` or `U` needs a square bracket, `x ∼ U[0,1]` is read as a uniform distribution, and an interval after a space that looks like a citation (`at once [28, 36]`) is not counted. Operators whose glyph is lost in the text layer are missed, so PDF counts stay lower than LaTeX counts.

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
│   └── processed/                     # Derived files (gitignored, except the evaluation set)
│       ├── eval_set.json              # Hand-labelled (requirement, formula) pairs, with domain and variable meanings, for evaluating the extraction
│       └── eval_set.md                # The same set, readable, with rendered formulas
│
├── src/                               # Reusable Python modules
│   ├── storage.py                     # CorpusStore class (deduplication & atomic JSON persistence)
│   ├── discovery/
│   │   ├── openalex_client.py         # 1-hop/2-hop citation crawler & OpenAlex keyword search
│   │   ├── keyword_search.py          # Direct arXiv API keyword harvester
│   │   └── enrichment.py              # Semantic Scholar / arXiv title search / HAL lookups, rate-limit handling
│   ├── harvesting/
│   │   └── downloader.py              # LaTeX & PDF downloader, failure reasons
│   ├── licensing/
│   │   ├── resolver.py                # Deep license scanner (.tex, PDF, arXiv OAI, OpenAlex)
│   │   └── stats.py                   # License tier classification & reporting tables
│   └── analysis/
│       └── estimator.py               # Counts concrete and symbolic STL formulas (macro-aware)
│
└── scripts/                           # Executable CLI entrypoints
    ├── 01_build_corpus.py             # Step 1: Discover papers (citations & keywords) and enrich them with missing links
    ├── 02_download_papers.py          # Step 2: Download LaTeX sources and fallback PDFs; download stats
    ├── 03_audit_and_print_licenses.py # Step 3: Verify licenses & print statistical tables
    ├── 04_estimate_formulas.py        # Step 4: Estimate the STL formula yield per paper
    └── eval/
        ├── build_eval_set.py          # Checks the labels against the LaTeX sources and writes the evaluation set
        ├── labels.py                  # The hand-written labels: edit this file to change the set
        └── render.py                  # Expands each paper's macros so the formulas render in eval_set.md

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

Without a Semantic Scholar key, the enrichment lookups of step 1 are likely to be refused; `--mode enrich` reports the state of that service when it starts. The OpenAlex key is sent to OpenAlex only.

---

## Pipeline Usage

All steps read from and update **`data/corpus.json`** incrementally. You can interrupt (`Ctrl+C`) and resume any script at any time without losing progress.

Every script also accepts `-h` / `--help`, which prints its flags and exits.

Each step can print its statistics from `data/corpus.json` without redoing the work: `--stats` on any of the four scripts.

### Step 1: Build & Expand the Paper Corpus

Step 1 gathers everything that is known about the papers, without downloading them. It discovers papers via 1-hop foundational citations, 2-hop citation cycles, or keyword searches, and then asks other services for the arXiv IDs and PDF links that OpenAlex does not list:

```bash
# 1A. Fetch Hop-1 papers citing the 4 foundational STL papers
python scripts/01_build_corpus.py --mode citations --hops 1

# 1B. Expand to Hop-2 (papers citing Hop-1 papers that have >= 5 citations)
python scripts/01_build_corpus.py --mode citations --hops 2 --min-hop1-citations 5

# 1C. Discover additional preprints and papers via keywords (arXiv + OpenAlex)
python scripts/01_build_corpus.py --mode keywords --keywords "Signal Temporal Logic" "Metric Temporal Logic" "STL specification"

# 1D. Enrich the corpus with missing arXiv IDs and PDF links (Semantic Scholar, arXiv title search, HAL)
python scripts/01_build_corpus.py --mode enrich

# Run all modes together
python scripts/01_build_corpus.py --mode all --hops 2

# Show the discovery statistics of the existing corpus
python scripts/01_build_corpus.py --stats

# Merge entries that turned out to be the same paper
python scripts/01_build_corpus.py --merge-duplicates

```

| Flag | Default | What it does |
|---|---|---|
| `--mode {citations,keywords,enrich,all}` | `citations` | What to run: the citation crawl, the keyword search (arXiv + OpenAlex), the enrichment (see below), or the three in that order. |
| `--hops {1,2}` | `1` | Citation depth. `1` fetches (or refreshes) the papers citing the 4 seed papers. `2` also fetches the papers citing those Hop-1 papers; Hop-1 itself is only fetched if it is not in the corpus yet. Ignored with `--mode keywords`. |
| `--min-hop1-citations N` | `5` | With `--hops 2`: only Hop-1 papers with at least `N` citations are expanded. |
| `--hop2-require-stl-text` / `--no-hop2-require-stl-text` | on | With `--hops 2`: keep a Hop-2 paper only if its title or abstract matches the STL relevance terms. The `--no-` form keeps every Hop-2 paper (much larger, off-topic corpus). |
| `--limit N` | none | With `--mode enrich`: asks each service about at most `N` papers (for testing). |
| `--stats` | off | Prints the statistics of the existing corpus (hops, discovery methods, metadata, enrichment lookups), then exits. No API is queried. |
| `--merge-duplicates` | off | Merges entries of the existing corpus that share an arXiv ID or a DOI, then exits. The published OpenAlex record is kept, the other ID is recorded under `alternate_ids`, and the duplicate download is deleted. No API is queried. |
| `--keywords K [K ...]` | `"Signal Temporal Logic" "STL specification" "STL formulas"` | Search phrases for the keyword search. Quote each phrase. Ignored with `--mode citations`. |

#### Enrichment

`--mode enrich` asks three services about the papers of the corpus. It can be interrupted and re-run: it only asks what is still unanswered.

| Service | Asked about | How | Gives |
|---|---|---|---|
| Semantic Scholar | Every paper with a DOI | 500 papers per request | arXiv ID, open PDF link |
| arXiv title search | Papers with no arXiv ID | 15 papers per request, one request every 3 seconds | arXiv ID |
| HAL | Papers with no arXiv ID that are not downloaded yet | One request per paper | Open PDF link |

Each answer is stored under the paper's `lookups` field as `found`, `not_found` or `no_answer`. `no_answer` means the service was rate-limited or unreachable, and that paper is asked again on the next run. A service that keeps rate-limiting is left alone for 15 minutes.

When a lookup gives a new arXiv ID or PDF link to a paper that step 2 had marked `unavailable`, the paper goes back to `pending`, so the next run of step 2 tries it. If the arXiv ID found already belongs to another entry, the two entries are the same work and are merged (as with `--merge-duplicates`).

### Step 2: Download Papers Locally (`.tex` & `.pdf`)

Downloads raw LaTeX source files (`data/raw/latex/{paper_id}/`) whenever available on arXiv, or falls back to Open Access PDFs (`data/raw/pdfs/{paper_id}.pdf`). It only uses the links that step 1 stored in the corpus and does not look for new ones:

```bash
# Download every paper that has not been tried yet
python scripts/02_download_papers.py

# Show the download status of the whole corpus
python scripts/02_download_papers.py --stats

# Go back over papers that failed on a network problem or a server error
python scripts/02_download_papers.py --retry-transient

# Fetch the LaTeX source of the papers held as PDF for which an arXiv ID is now known
python scripts/02_download_papers.py --upgrade-pdfs

```

Each run first compares `data/corpus.json` with the files on disk and corrects the recorded status. Without any flag, only `pending` papers are downloaded: those never tried, and those for which the enrichment of step 1 found a new link.

| Flag | What it does |
|---|---|
| `--retry-unavailable` | Also retries **every** paper marked `unavailable`, whatever the reason. |
| `--retry-transient` | Also retries the `unavailable` papers whose failure reason is a connection error, a timeout, HTTP 429 or HTTP 500/502/503/504. |
| `--upgrade-pdfs` | Only goes over the papers held as PDF that have an arXiv ID (usually found by the enrichment after the PDF was downloaded) and fetches their LaTeX source, one request every 3.5 seconds, then prints a report and exits. When the source is downloaded, the paper's PDF is deleted. A paper for which arXiv has no LaTeX source is recorded under `local_files.latex_upgrade` and not asked again; a network failure is tried again on the next run. Run steps 3 and 4 afterwards. |
| `--delay S` | Seconds to pause after each arXiv download (default 3.5), in the normal run and with `--upgrade-pdfs`. When arXiv answers HTTP 429 or 503, the same paper is tried again after 30, 60, 120 and 300 seconds and the pause between papers doubles (up to 30 seconds); it halves again after 10 papers without a refusal. If arXiv still refuses after the last wait, the run stops and reports how many papers were not tried; the paper it stopped on is left untouched, with no fallback to its PDF. A dropped connection or a timeout is tried once more after 10 seconds. |
| `--limit N` | Processes only the first `N` papers of the queue (for testing). |
| `--stats` | Prints the status counts and failure reasons of the whole corpus, then exits. Nothing is downloaded. |
| `--relabel` | Rewrites the stored failure reasons in the current wording, prints the same report as `--stats`, then exits. Nothing is downloaded. |

`--retry-transient` is redundant with `--retry-unavailable`, which already includes those papers. `--stats` and `--relabel` take precedence over all the download flags, and `--upgrade-pdfs` over the retry flags.

#### Failure reasons

A paper that could not be downloaded gets `status: "unavailable"` and one of these `failure_reason` values in `data/corpus.json`. Reasons from PDF links are prefixed with `PDF Mirrors: ` and describe the last link tried.

| Failure reason | Meaning |
|---|---|
| `No Link Found (not open access)` | No arXiv source and no PDF link is known, and the paper is not open access. Nothing was attempted. |
| `No Link Found (open access, but no URL listed)` | Same, for a paper that OpenAlex marks as open access. |
| `No Link Found (a lookup got no answer, run the enrichment again)` | No link is known, but an enrichment lookup of step 1 got no answer for this paper, so one may still exist. |
| `arXiv Error: HTTP 404 (Not Found)` / `HTTP 403 (Forbidden/Blocked)` / `HTTP <code>` | arXiv refused or does not have the source bundle. |
| `arXiv Error: Connection Timeout` | arXiv did not answer in time. |
| `arXiv Error: Network/System Exception (<error>)` | Any other problem while fetching or unpacking the arXiv bundle. The brackets name the error and the one underneath it, e.g. `(ConnectionError: NameResolutionError)` for a DNS failure or `(SSLError: SSLCertVerificationError)` for a certificate problem. |
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

The `--stats` report also counts the unavailable papers that still have an unanswered lookup, whatever their failure reason.

### Step 3: Audit Exact Licenses & Print Statistics

Scans local `.tex` files, PDF metadata, and arXiv OAI-PMH headers to verify exact paper licenses, flags any conflicts with OpenAlex metadata, updates `data/corpus.json`, and prints a full breakdown report:

```bash
python scripts/03_audit_and_print_licenses.py

# Print the report again without re-scanning
python scripts/03_audit_and_print_licenses.py --stats

```

| Flag | What it does |
|---|---|
| `--stats` | Skips the scan and prints the report from the licences already stored in `data/corpus.json`, then exits. |
| `--limit N` | Audits only the first `N` downloaded papers (for testing). The report still covers the whole corpus. |

### Step 4: Estimate STL Formula Yield

Scans all downloaded `.tex` folders and `.pdf` files, counts the temporal operators with a time bound and the formulas they form (concrete and symbolic) per paper, saves the counts under `formula_estimates` in `data/corpus.json`, and prints the 20 papers with the most concrete formulas:

```bash
python scripts/04_estimate_formulas.py

# Print the report again without re-scanning
python scripts/04_estimate_formulas.py --stats

```

| Flag | What it does |
|---|---|
| `--limit N` | Scans only the first `N` downloaded papers (for testing). |
| `--stats` | Prints the same report from the estimates already stored in `data/corpus.json`, then exits. No file is scanned. |

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
    "lookups": {
      "semantic_scholar": {"status": "found", "checked_at": "2026-10-12"}
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
      "symbolic": 3,
      "formulas_concrete": 7,
      "formulas_symbolic": 2
    }
  }
}

```

| Field | Notes |
|---|---|
| `alternate_ids` | IDs of other entries that were merged into this one as duplicates (e.g. the preprint record of a published paper). A later crawl resolves them to this entry instead of adding them again. |
| `alternate_dois` | DOIs of the merged entries, when they differ from `doi`. |
| `discovery.methods` | How the paper was found: `citation_hop_1`, `citation_hop_2`, `openalex_kw:<keyword>`, `arxiv_kw:<keyword>`. A paper can have several. |
| `discovery.hop_distance` | `1` or `2` for papers from the citation crawl, `null` for papers found only by keyword. |
| `discovery.parent_ids` | The papers of the previous hop that this paper cites (the seed papers for Hop-1). |
| `discovery.expanded_hop_2` | Set on Hop-1 papers whose citing papers have already been fetched. |
| `lookups` | Written by the enrichment of Step 1: one entry per service asked (`semantic_scholar`, `arxiv_title`, `hal`), with `status` `found`, `not_found` or `no_answer` and the date of the answer. A service with no entry was not asked, either because it was not needed (for example the arXiv title search for a paper that has an arXiv ID) or because the enrichment has not reached the paper yet. |
| `local_files.status` | `pending` (to be tried by Step 2), `downloaded_latex`, `downloaded_pdf` or `unavailable`. |
| `local_files.failure_reason` | Only for `unavailable` papers; see the failure reasons under Step 2. |
| `license_info` | Written by Step 3. `effective_source` is `tex_source`, `pdf_metadata`, `arxiv_oai`, `openalex_locations` or `none`. |
| `formula_estimates` | Written by Step 4, for downloaded papers only. `concrete` and `symbolic` count temporal operators with numeric and with parametric time bounds. `formulas_concrete` counts the formulas holding at least one concrete operator, `formulas_symbolic` the formulas whose bounded operators are all parametric. |

### License Tiers

Every paper is categorized into one of four legal tiers:

1. **`permissive_cc` (`CC0`, `CC-BY`, `CC-BY-SA`):** Safe for verbatim redistribution and commercial/academic use with attribution.
2. **`restricted_cc` (`CC-BY-NC`, `CC-BY-ND`):** Permitted for non-commercial academic research; requires paraphrasing if used in derivative commercial datasets.
3. **`custom_or_arxiv` (`arXiv non-exclusive`, HAL, institutional repository):** Governed by Text & Data Mining (TDM) research exceptions; mathematical formulas are non-copyrightable facts, and natural language context should be normalized/paraphrased before redistribution.
4. **`unspecified`:** License not declared in metadata or source files.
