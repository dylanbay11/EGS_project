# EGS Project Progress & State

## Current State
- **Primary source collection is working**: `development/data_collection.py` handles the community Google Sheet and saves dated raw source files in `data/` using the `YYYY-MM-DD-gsheets.xlsx` pattern.
- **Wikipedia raw scraping is working**: `development/wiki_scraper.py` now follows the same rolling-cache idea, writes dated raw wiki files like `YYYY-MM-DD-wiki.csv`, and has safer bundle/header cleanup so collection names are less likely to become fake game rows.
- **Wikipedia enrichment is now a true intermediate step**: `development/enrich_wiki_data.py` reads the newest raw wiki scrape and writes a single rolling intermediate file at `data/wiki-enriched.csv` instead of accumulating dated enriched copies.
- **Core merge step uses the enriched wiki data**: `development/clean_data.py` reads the newest Google Sheets source plus `data/wiki-enriched.csv`, applies the shared collection/bundle cleanup logic, and writes `data/cleaned_merged_data.csv`.
- **Downstream enrichment exists but is not the final canonical flow yet**: `development/metacritic_scraper.py` currently extends `data/cleaned_merged_data.csv` into `data/merge_mc.csv`, but the broader "single fully-featured dataset" stage is still in progress.

## Main Data Flow
This is the main pipeline right now, ignoring exploratory notebooks, spot-check helpers, and older trial scripts.

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

5. **Downstream enrichment layer**
   `development/metacritic_scraper.py`
   Reads `data/cleaned_merged_data.csv`
   Produces `data/merge_mc.csv`
   This is one of the current follow-on enrichments on the path toward the eventual fully-featured analysis dataset.

## Current Notes
- `development/spotcheck.py` should be kept in sync with the main pipeline assumptions, especially the rolling `data/wiki-enriched.csv` intermediate and the collection/bundle cleanup rules.
- `development/scrape_sheet.py` is still a development notebook-style script rather than part of the main production flow, but its duplicate import and stale output path should not drift from the main conventions.
- The merge step is still a normalized-title left join. That is good enough for current progress, but repeated giveaways across different years still deserve a more precise pass later if we want a cleaner event-level match.

## Near & Medium-Term Roadmap
- [ ] **Visibility Options**: Create a marimo document that allows easier inspection and spot-checking of outputs, to enable better feedback for AI agents.
- [ ] **Test Suite**: Develop a small-scale, useful set of reusable validation checks without turning the repo into a full pytest project.
- [ ] **Wikipedia Spot Check**: Hand-check the enriched Wikipedia fields and a sample of tricky bundle rows.
- [ ] **Google Sheets Spot Check**: Ensure that all relevant info was imported including labels and metadata.
- [ ] **Verify Source Merges**: Tighten merge logic for repeated giveaway titles so event-level matches are cleaner.
- [ ] **Feature Engineering**: Perform minor feature engineering, manipulation, or reshaping for stubborn columns.
- [ ] **Missing Data Assessment**: Complete a holistic missing-data pass across the merged dataset.
- [ ] **Fetch API Data Directly**: Bypass the problematic wrapper API and hit open static endpoints (`freeGamesPromotions` and `content/products/<productSlug>`) for tags, prices, developer, publisher, and related details.

## Long-Term Roadmap
- [ ] **Extract Wrapper Data**: If necessary, extract additional "extra" information via the wrapper API to enable more analysis.
- [ ] **Interactive Streamlit App**: Build an interactive app for exploring giveaway timing, prices, tags, and other features.
- [ ] **Content Creation**: Write a blog post, Reddit post, and/or LinkedIn post detailing the findings and process.
- [ ] **Portfolio Integration**: Create a presentation or portfolio-ready artifact for the project.
