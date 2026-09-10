# EGS Project Progress & State

## September 2026 egdata landscape review

- [x] **Competitor/API assessment**: reviewed `egdata.app`, its live public API, OpenAPI
  contract, giveaway browser, and relevant offer endpoints. The collection layer overlaps
  heavily: egdata already exposes offer-linked giveaway history, store identity/metadata,
  prices, HLTB, external ratings, IGDB, and headline giveaway statistics. The project should
  differentiate through repaired/reconciled source grain, explicit definitions, cross-source
  auditability, longitudinal giveaway analysis, and its visitor-facing research narrative.
  Detailed findings: `outputs/egdata_comparison.md`.
- [ ] **Reconcile against egdata after the source-grain repair**: compare distinct offer/windows
  through a shared cutoff, use stable offer IDs where available, and audit missing/extra records
  without treating either source as automatic ground truth.
- [ ] **Evaluate contemporaneous giveaway value**: test whether egdata price history can support
  price-at-giveaway measures, with coverage diagnostics and clear reuse/attribution terms.

## September 2026 dashboard design branch

- [x] **Second dashboard prototype on `codex/clean-sample-dashboard`**:
  `development/dashboard/app.py` is a separate marimo + Plotly portfolio explorer
  with sidebar filters, reactive game-level summaries, score/playtime discovery,
  genre counts, a selectable game file, and giveaway history. Preserves the
  existing explorers and production pipeline. Design/launch notes:
  `outputs/dashboard_design.md`.
- [x] **Bounded source-reconciled fixture**: `development/build_dashboard_sample.py`
  selects 40 games / 42 windows from 122 eligible games in the saved snapshot.
  Writes `data/dashboard_sample.parquet` and a deployable JSON asset under
  `development/dashboard/public/`. Evidence: `outputs/dashboard_sample_report.md`
  and `outputs/dashboard_sample_audit.csv`. This is an enriched design sample,
  not a representative program-wide dataset or certification that the pipeline is fixed.
- [x] **Portable export**: `development/export_dashboard.py` builds
  `outputs/dashboard_site/` and `outputs/dashboard_site.zip` for ordinary static
  hosting, bundling custom CSS and sample data. Local Python retains pandas 3;
  browser metadata targets bundled Pyodide 0.27.7's pandas 2.2.3. No project dependency downgrade.
- [x] **Programmatic checks passed**: `outputs/dashboard_checks.py` checks source
  identity/grain and runs default, empty, single-game, and history notebook states.
  Captured output is in `outputs/dashboard_checks.txt`.
- [x] **Dashboard browser acceptance**: native search/history and actual WASM
  startup, game selection, and empty filtering tested in the in-app browser.
  Added an initial WASM loading message and meaningful empty genre-chart state.
- [ ] **Staging**: obtain the user's website/staging destination before private deployment. Swap
  in the repaired full dataset only after accepting the analytical definitions.

## September 2026 independent review

Read [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for the current orientation, branch map,
evidence, and revised personal-QA agenda. It qualifies the older status claims below;
the review did not apply pipeline repairs or certify the July resolution log.

- [x] **Repository orientation review**: reviewed the non-Jules branch tips and documentation, reproduced the downstream canonical build, and smoke-tested the newer notebooks. Evidence: `outputs/repository_review_checks.py` and `outputs/repository_review_checks.txt`.
- [ ] **Repair source grain before trusting counts**: 806 cleaned Sheets rows become 914 after the title-only wiki join; Bloons TD 6 expands 4→12. Preserve PC/mobile distinctions rather than blindly deduplicating title/date rows.
- [ ] **Repair and audit product identity**: saved EGS and Metacritic matches include wrong BioShock games; Cat Quest 2/II remain separate titles. Threshold acceptance does not establish correctness.
- [ ] **Agree on analytical definitions**: primary population, event versus game/offer counts, edition equivalence, price meaning, and snapshot versus ongoing refresh. Use the decision table in `PROJECT_REVIEW.md` rather than repeating the old A–E checklist.
- [ ] **Strengthen canonical QA and refresh behavior**: add source-grain and identity checks, reconcile missing-score semantics, handle future `next` rows correctly, and make cache/slice behavior safe for routine use.
- [ ] **Reassess public claims after repair**: 683 titles and $12,114.01 are reproducible provisional calculations. The app executes but its analytical claims and visitor experience still require acceptance.

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
- **Publisher-judgment API proof of concept explored**: the disposable
  `development/try_deepseek_publisher_judgments.py` tests real EGS/Wikipedia
  disagreements with `deepseek-flash`. DeepSeek's documented native Responses
  API web-search tool did not execute reliably in live probes, so the working
  cheap path separates search from judgment: Tavily basic search (recommended;
  free monthly allowance) or a brittle no-key DuckDuckGo HTML fallback, followed
  by a non-thinking JSON classification. The experiment validates cited search
  result IDs and stores raw audit records in
  `outputs/deepseek_publisher_poc.jsonl`; pipeline integration remains TBD.
- **REVIEW_NEEDED items resolved (July 2026)**: all A–E data-quality questions are decided and applied. `egs_api_enrich.py` gained a `MANUAL_OVERRIDES` map (~24 titles: pinned listings for wrong fuzzy matches incl. a token-subset audit of "confident" matches, forced no-match for delisted products, nulled bogus $0 prices) and now nulls all substantive fields for below-threshold matches in the output. `build_dataset.py` folds case-variant duplicate titles (686→683 games), retires the transient `next` marker, and derives `is_standalone_game` (606 games / 77 add-on titles). `REVIEW_NEEDED.md` is now the resolution log (incl. a short "still worth human eyes" list: wiki footnote artifacts, unaudited Metacritic matcher).
- **Stage 2 interactive explorer started**: `development/explorer.py` is a marimo app (separate artifact from `eda.py`) with an **Explore** tab (reactive grain/year/type/price/score/tag filters + a "confident EGS matches only" switch wired to `egs_meets_threshold`, driving a live table and price/year/tag charts) and a **Triage** tab that turns the `REVIEW_NEEDED.md` A–E data-quality questions into sortable tables (read-only — surfaces, never edits). `development/MARIMO_NOTES.md` is a conventions note pinned to the installed **marimo 0.23.2** (the version-picky `start`/`stop` slider args, the define-vs-read-across-cells rule, NA-safe masking). Export/smoke-test: `uv run marimo export html development/explorer.py -o outputs/explorer.html`.
- **Public portfolio explorer built (July 2026)**: `development/portfolio_explorer.py` is the *user-facing* marimo app — a new artifact, not a rework of `explorer.py` — written for a stranger arriving from a reddit/linkedin link: narrative header, KPI hero row (914 giveaways · 683 titles · $12,114 confident library value · 8,663 HLTB hours · median Metacritic 77), one filter row (years / full-games-only / tags / title search) scoping five curated plotly charts (yearly cadence, cumulative library value, price distribution, top store tags, score-vs-price scatter) plus a downloadable game-level table and sources/caveats accordions. **WASM-first**: data loads via `mo.notebook_location()/public/egs_app_data.csv` (a slim 212 KB extract cut by `development/build_app_data.py` — rerun it after any canonical rebuild), so `uv run marimo export html-wasm development/portfolio_explorer.py -o outputs/portfolio_wasm --mode run --no-show-code` produces a fully client-side static site (gitignored build artifact; serve any static host, e.g. GitHub Pages). Charts follow a validated light/dark-aware palette; the app extract converts the Metacritic "no score stored as 0" wart (72 titles) to NA for display — canonical dataset untouched, flagged in `REVIEW_NEEDED.md`.

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
- [~] **Interactive App (marimo)**: the user-facing app now exists as `development/portfolio_explorer.py` (see Current State) — narrative + KPI row + five curated charts + filterable/downloadable table, deployable as a client-side WASM static site. `development/explorer.py` remains the internal developer workbench (filters + data-quality triage tabs). Next: user feedback pass on copy/chart choices, then pick a host (GitHub Pages is the zero-infra option) and wire a publish step.
- [ ] **Content Creation**: Write a blog post, Reddit post, and/or LinkedIn post detailing the findings and process.
- [ ] **Portfolio Integration**: Create a presentation or portfolio-ready artifact for the project.
