# EGS Project Progress & State

## Current State
- **Primary source collection is working**: `development/data_collection.py` handles the community Google Sheet and saves dated raw source files in `data/` using the `YYYY-MM-DD-gsheets.xlsx` pattern.
- **Wikipedia raw scraping is working**: `development/wiki_scraper.py` follows the same rolling-cache idea, writes dated raw wiki files like `YYYY-MM-DD-wiki.csv`, and has safer bundle/header cleanup so collection names are less likely to become fake game rows.
- **Wikipedia enrichment is now a true intermediate step**: `development/enrich_wiki_data.py` reads the newest raw wiki scrape and writes a single rolling intermediate file at `data/wiki-enriched.csv` instead of accumulating dated enriched copies.
- **Core merge step uses the enriched wiki data**: `development/clean_data.py` reads the newest Google Sheets source plus `data/wiki-enriched.csv`, applies the shared collection/bundle cleanup logic, and writes `data/cleaned_merged_data.csv`.
- **Collection handling is now aligned across the main flow**: the raw Google Sheets loader and cleaner rewrite collection rows so the actual game lands in the title field and the collection name is preserved in notes as `Part of collection: ...`, while the wiki path defensively drops stale bundle-header rows.
- **Downstream enrichment exists but is not the final canonical flow yet**: `development/metacritic_scraper.py` currently extends `data/cleaned_merged_data.csv` into `data/merge_mc.csv`, but the broader "single fully-featured dataset" stage is still in progress.
- **HLTB enrichment exists as a downstream pass**: `development/hltb_scraper.py` now rebuilds `outputs/hltb_data.csv` and `data/merge_hltb.csv` with a conservative matcher that currently links 550 of 686 unique titles to HLTB data.
- **Single canonical dataset now exists**: `development/build_dataset.py` is the authoritative join. It reads the cleaned event-level base plus the per-title caches (`outputs/metacritic_cache.json`, `outputs/hltb_data.csv`, `data/egs-enriched.csv`) and writes one tidy table at `data/egs_giveaways.parquet` (event-level, ~914 rows) plus a derived `data/egs_giveaways_by_game.parquet` (game-level, 686 titles). Columns are documented in root `DATA_DICTIONARY.md`. This replaces the previous parallel, schema-divergent `merge_*.csv` files as the analysis surface.
- **Scraper schema drift fixed**: `metacritic_scraper.py` and `hltb_scraper.py` previously required a `Title_gsheets` column and would crash on the current cleaned schema (which uses `Title`). Both now adapt to either column, so their caches stay in sync with the current pipeline.
- **EGS API enrichment is productionized**: `development/egs_api_enrich.py` promotes the workbench/`direct_egs_scraper` logic into a resumable, cached, rate-limit-polite pass that adds store-side price, tags/categories, seller/publisher/developer, dates, and descriptions to `data/egs-enriched.csv` (cache: `outputs/egs_api_cache.json`).
- **Validation + EDA exist**: `development/validate_dataset.py` runs lightweight integrity/sanity checks on the canonical dataset (errors fail, warnings tolerated). `development/eda.py` is a marimo EDA notebook that doubles as a data-quality feedback pass (ends with a Data Issues list).
- **REVIEW_NEEDED items resolved (July 2026)**: all A–E data-quality questions are decided and applied. `egs_api_enrich.py` gained a `MANUAL_OVERRIDES` map (~24 titles: pinned listings for wrong fuzzy matches incl. a token-subset audit of "confident" matches, forced no-match for delisted products, nulled bogus $0 prices) and now nulls all substantive fields for below-threshold matches in the output. `build_dataset.py` folds case-variant duplicate titles (686→683 games), retires the transient `next` marker, and derives `is_standalone_game` (606 games / 77 add-on titles). `REVIEW_NEEDED.md` is now the resolution log (incl. a short "still worth human eyes" list: wiki footnote artifacts, unaudited Metacritic matcher).
- **Stage 2 interactive explorer started**: `development/explorer.py` is a marimo app (separate artifact from `eda.py`) with an **Explore** tab (reactive grain/year/type/price/score/tag filters + a "confident EGS matches only" switch wired to `egs_meets_threshold`, driving a live table and price/year/tag charts) and a **Triage** tab that turns the `REVIEW_NEEDED.md` A–E data-quality questions into sortable tables (read-only — surfaces, never edits). `development/MARIMO_NOTES.md` is a conventions note pinned to the installed **marimo 0.23.2** (the version-picky `start`/`stop` slider args, the define-vs-read-across-cells rule, NA-safe masking). Export/smoke-test: `uv run marimo export html development/explorer.py -o outputs/explorer.html`.

## Main Data Flow
This is the main pipeline right now, ignoring exploratory notebooks, spot-check helpers, and older trial scripts. A visual version with diagnostic annotations (join keys, match thresholds, where each cleaning rule lives) is in root `DIAGRAM.md` — keep it in sync when pipeline structure changes.

1. **Google Sheets base import**
   `development/data_collection.py`
   Produces `data/YYYY-MM-DD-gsheets.xlsx`
   This is the primary source of giveaway events, labels, notes, and color/category context.

2. **Wikipedia base scrape**
   `development/wiki_scraper.py`
   Produces `data/YYYY-MM-DD-wiki.csv`
   This is the secondary source for title/date/source-link coverage and giveaway-history cross-checking.

3. **Wikipedia enrichment**
   `development/enrich_wiki_data.py`
   Reads the newest `data/YYYY-MM-DD-wiki.csv`
   Produces `data/wiki-enriched.csv`
   This adds English Wikipedia metadata like developer, publisher, genre, release date, summary, and background text.

4. **Core cleaning + merge**
   `development/clean_data.py`
   Reads the newest `data/YYYY-MM-DD-gsheets.xlsx` plus `data/wiki-enriched.csv`
   Produces `data/cleaned_merged_data.csv`
   This is the current main merged dataset for downstream analysis and future enrichers.

5. **Downstream enrichment layer (per-title caches)**
   `development/metacritic_scraper.py` → `outputs/metacritic_cache.json` (+ `data/merge_mc.csv`)
   `development/hltb_scraper.py` → `outputs/hltb_data.csv` (+ `data/merge_hltb.csv`)
   `development/egs_api_enrich.py` → `data/egs-enriched.csv` (cache `outputs/egs_api_cache.json`)
   Each maintains a per-title cache; the standalone `merge_*.csv` files are now legacy/debug.

6. **Canonical build (single dataset)**
   `development/build_dataset.py`
   Reads `data/cleaned_merged_data.csv` + the three per-title caches above
   Produces `data/egs_giveaways.parquet` (event-level) and `data/egs_giveaways_by_game.parquet` (game-level)
   This is the analysis-ready surface. `development/validate_dataset.py` checks it; `development/eda.py` explores it.

## Current Notes
- `development/spotcheck.py` should stay in sync with the main pipeline assumptions, especially the rolling `data/wiki-enriched.csv` intermediate and the collection/bundle cleanup rules.
- `development/scrape_sheet.py` is still a development notebook-style script rather than part of the main production flow, but its duplicate import and stale output path should not drift from the main conventions.
- `development/egs_api_helpers.py` and `development/egs_api_workbench.py` are now the easiest place to do manual Epic API title QA, slug inspection, and quick endpoint poking before folding logic back into a production script.
- The merge step is still a normalized-title left join. That is good enough for current progress, but repeated giveaways across different years still deserve a more precise pass later if we want a cleaner event-level match.

## Near & Medium-Term Roadmap
There may be minor overlap between some of these.
- [x] **Visibility Options**: `development/eda.py` is a marimo EDA + data-quality notebook (export to html locally with `uv run marimo export html development/eda.py -o outputs/eda.html`).
- [x] **Test Suite**: `development/validate_dataset.py` provides lightweight reusable validation checks (no pytest).
- [x] **Finish Data Cleaning**: The July 2026 review resolved the outstanding cleaning decisions (EGS match corrections, low-confidence nulling, title-casing folds, `next` relabel, standalone-game flag). Remaining nits are tracked in `REVIEW_NEEDED.md`'s "still worth human eyes" list.
- [ ] **Wikipedia Spot Check**: Hand-check the enriched Wikipedia fields and a sample of tricky bundle rows.
- [ ] **Google Sheets Spot Check**: Ensure that all relevant info was imported including labels and metadata.
- [ ] **Verify Source Merges**: Tighten merge logic for repeated giveaway titles so event-level matches are cleaner.
- [ ] **HLTB Match Refinement**: Add a more dedicated title alias/matching layer for tricky collections, promos, trademark-heavy names, and subtitle/edition edge cases.
- [ ] **Feature Engineering**: Perform minor feature engineering, manipulation, or reshaping for stubborn columns.
- [ ] **Missing Data Assessment**: Complete a holistic missing-data pass across the merged dataset.
- [x] **Fetch API Data Directly**: `development/egs_api_enrich.py` pulls store-side price, tags, categories, seller/publisher/developer, dates, and descriptions per title. Uses the wrapper for the Cloudflare-protected search/offers plus the static `content/products/<slug>` endpoint for product pages; resumable and cached.

## Long-Term Roadmap
- [ ] **Extract Wrapper Data**: If necessary, extract additional "extra" information via the wrapper API to enable more analysis.
- [~] **Interactive App (marimo)**: `development/explorer.py` scaffolds the explorer (timing, price, tags, score filters + data-quality triage). Started in marimo rather than Streamlit, matching the rest of the current toolchain. Next: refine UX from real use, and fold in whatever cleaning decisions come out of `REVIEW_NEEDED.md`. Ultimately: Have a user-facing data explorer as final deliverable. So, this existing thing can be a starting point, but note that it was designed as a developer utility; long-term roadmap-wise, this is supposed to be a user-facing interactive app for curious users to answer their own small questions and visualize data in flexible ways. 
- [ ] **Content Creation**: Write a blog post, Reddit post, and/or LinkedIn post detailing the findings and process.
- [ ] **Portfolio Integration**: Create a presentation or portfolio-ready artifact for the project.
