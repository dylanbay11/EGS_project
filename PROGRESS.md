# EGS Project Progress & State

## Current State of Development
- **Automated Data Collection**: The primary source is a Community Google Sheet. We have automated data collection and parsing from this sheet via `data_collection.py`, which includes logic to handle categorical background colors and column cleaning.
- **Data Enrichment**: We have a working Wikipedia scraper (`wiki_scraper.py`) that extracts giveaway lists from the Russian Wikipedia page for further data enrichment.
- **Data Cleaning and Merging**: We have a script (`clean_data.py`) to clean the Google Sheets data, handle formatting quirks (e.g., exploded bundle titles from Wiki), and merge the datasets.
- **Collection Handling**: The raw Google Sheets loader and cleaner now both rewrite collection rows so the actual game lands in the title field and the collection name is preserved in notes as `Part of collection: ...`. The wiki path also has a defensive bundle-header cleanup so stale or slightly shifted markup does not keep the collection title as a fake extra game row.
- **API Access Discovery**: We discovered that the unofficial wrapper-API (`epicstore_api`) is failing due to structure/authentication changes. However, we found it is highly feasible to bypass it and use open static endpoints instead, as documented in `EpicGamesStoreAPIReport.md`.

## Near & Medium-Term Roadmap
There may be minor overlap between some of these.
- [ ] **Visibility Options**: Create a marimo document that allows easier inspection and spot-checking of outputs, to enable better feedback for AI agents
- [ ] **Test Suite**: Develop small-scale, not overkill, useful set of re-usable tests (manual, no extra packages) for validation.
- [ ] **Finish Data Cleaning**: Finalize cleaning rules and procedures across datasets, both content and columns.
- [ ] **Wikipedia Spot Check**: Polish up final touches on game list data enrichment. The Wikipedia scrape needs hand verification and spot-checking by the user.
- [x] **Google Sheets Spot Check**: Ensure that all relevant info was imported including labels and 'meta'data. (Updated collection logic)
- [ ] **Verify Source Merges**: Ensure that the two gamelist sources merge and match correctly.
- [ ] **Feature Engineering**: Perform minor feature engineering, manipulation, or reshaping for certain stubborn columns.
- [ ] **Missing Data Assessment**: Complete a holistic missing data pass/assessment.
- [ ] **Fetch API Data Directly**: Bypass the problematic wrapper-API and hit open static endpoints (`freeGamesPromotions` and `content/products/<productSlug>`) for data (like tags, prices, developer, and publisher details) as detailed in the API report.

## Long-Term Roadmap
- [ ] **Extract Wrapper Data**: If necessary, extract additional "extra" information via the wrapper-API to enable more analysis.
- [ ] **Interactive Streamlit App**: Develop an interactive Streamlit application to allow users to play with visualizations (e.g., price over time, average price by game tag, total dollar amount per week, as noted in the brainstorm document).
- [ ] **Content Creation**: Write a blog post, Reddit post, and/or LinkedIn post detailing the findings and process.
- [ ] **Portfolio Integration**: Create a portfolio presentation suitable for a portfolio website.
