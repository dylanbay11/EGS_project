# EGS Project Progress & State

## Current State of Development
- **Automated Data Collection**: The primary source is a Community Google Sheet. We have automated data collection and parsing from this sheet via `data_collection.py`, which includes logic to handle categorical background colors and column cleaning.
- **Data Enrichment**: We have a working Wikipedia scraper (`wiki_scraper.py`) that extracts giveaway lists from the Russian Wikipedia page for further data enrichment.
- **Data Cleaning and Merging**: We have a script (`clean_data.py`) to clean the Google Sheets data, handle formatting quirks (e.g., exploded bundle titles from Wiki), and merge the datasets.
- **API Access Discovery**: We discovered that the unofficial wrapper-API (`epicstore_api`) is failing due to structure/authentication changes. However, we found it is highly feasible to bypass it and use open static endpoints instead, as documented in `EpicGamesStoreAPIReport.md`.


## Data Flow Pipeline
The project's main data flow consists of the following steps:
1. **Scraping Base Data**:
   - `data_collection.py` (or `scrape_sheet.py` in development): Scrapes and parses the primary EGS Community Google Sheet, producing the base `YYYY-MM-DD-gsheets.csv` or `.xlsx` dataset.
   - `wiki_scraper.py`: Scrapes the Russian Wikipedia giveaway list, handling explosions of game bundles into individual rows, producing the base `YYYY-MM-DD-wiki.csv` dataset.
2. **Data Enrichment**:
   - `enrich_wiki_data.py`: Reads the latest `*-wiki.csv`, hits the English Wikipedia API for each title to extract infobox details (developer, genre, engine, etc.) and summaries, outputting the enriched `YYYY-MM-DD-wiki-enriched.csv`.
3. **Cleaning and Merging**:
   - `clean_data.py`: Loads the most recent Google Sheets dataset and the *enriched* Wikipedia dataset. It applies final structural cleanups and merges the two datasets together using a left join on normalized titles.
4. **Final Output**: The result of the merge is stored as `cleaned_merged_data.csv`, which serves as the final dataset ready for advanced analysis and visualization.

## Near & Medium-Term Roadmap
There may be minor overlap between some of these.
- [ ] **Visibility Options**: Create a marimo document that allows easier inspection and spot-checking of outputs, to enable better feedback for AI agents
- [ ] **Test Suite**: Develop small-scale, not overkill, useful set of re-usable tests (manual, no extra packages) for validation.
- [x] **Finish Data Cleaning**: Finalize cleaning rules and procedures across datasets, both content and columns.
- [x] **Wikipedia Spot Check**: Polish up final touches on game list data enrichment. The Wikipedia scrape needs hand verification and spot-checking by the user.
- [ ] **Google Sheets Spot Check**: Ensure that all relevant info was imported including labels and 'meta'data.
- [x] **Verify Source Merges**: Ensure that the two gamelist sources merge and match correctly.
- [ ] **Feature Engineering**: Perform minor feature engineering, manipulation, or reshaping for certain stubborn columns.
- [ ] **Missing Data Assessment**: Complete a holistic missing data pass/assessment.
- [ ] **Fetch API Data Directly**: Bypass the problematic wrapper-API and hit open static endpoints (`freeGamesPromotions` and `content/products/<productSlug>`) for data (like tags, prices, developer, and publisher details) as detailed in the API report.

## Long-Term Roadmap
- [ ] **Extract Wrapper Data**: If necessary, extract additional "extra" information via the wrapper-API to enable more analysis.
- [ ] **Interactive Streamlit App**: Develop an interactive Streamlit application to allow users to play with visualizations (e.g., price over time, average price by game tag, total dollar amount per week, as noted in the brainstorm document).
- [ ] **Content Creation**: Write a blog post, Reddit post, and/or LinkedIn post detailing the findings and process.
- [ ] **Portfolio Integration**: Create a portfolio presentation suitable for a portfolio website.
