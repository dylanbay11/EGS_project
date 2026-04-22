# Epic Games Store Free Games - Data Sources Report

This report evaluates several potential sources for tracking the free games given away on the Epic Games Store over the years. The primary goals are to ensure the source is reliable, has ongoing updates, contains at least the game title and the date it was free, and ideally offers richer data to replace potentially defunct sources as of April 2026.

## Evaluated Sources

### 1. Russian Wikipedia
**URL:** [Список игр, розданных в Epic Games Store](https://ru.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA_%D0%B8%D0%B3%D1%80,_%D1%80%D0%BE%D0%B7%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85_%D0%B2_Epic_Games_Store)
*   **Viability & Promise:** Very high. It's Wikipedia, so it's regularly updated by the community and unlikely to disappear.
*   **Data Richness:** High. In addition to dates and titles, many games have direct Wikipedia links, which could be followed to scrape genres, developers, and release dates. It also contains footnotes.
*   **Formatting Quirks:** Data is split into multiple `wikitable` elements, generally one per year. The dates are in Russian (e.g., "14—27 декабря 2018"). Titles occasionally have footnote markers (e.g., "[1]") that need to be stripped via regex.

### 2. GameRant
**URL:** [Every Free Game Released On The Epic Games Store](https://gamerant.com/epic-games-store-free-games-list/)
*   **Viability & Promise:** Good. GameRant maintains this as a living article.
*   **Data Richness:** Low. It contains only the game title and the time period it was free.
*   **Formatting Quirks:** The data is presented in a single, massive HTML `<table>`. The years are injected as single-cell rows separating the entries for that year. The date column just says "April 2–16", requiring you to inherit the year from the most recent year-header row.

### 3. PC Gamer
**URL:** [What's free on the Epic Games Store right now?](https://www.pcgamer.com/epic-games-store-free-games-list/)
*   **Viability & Promise:** Good. Similar to GameRant, this is an evergreen article updated weekly.
*   **Data Richness:** Low. Contains the date and the game title.
*   **Formatting Quirks:** The historical data is formatted as unstructured HTML bulleted lists (`<ul>` containing `<li>` elements) divided by year. The text inside the bullets usually follows a "Date: Title" format (e.g., "Dec 31: Sifu"), but can be slightly inconsistent.

### 4. Community Google Sheets (The Winner for Automation)
**URL:** [EGS Free Games List](https://docs.google.com/spreadsheets/d/1fpp0u5VHig4KG47Fu0I2EaB7vNCuU4xYBFWRlUKydjk/edit#gid=216261844)
*   **Viability & Promise:** Excellent. The community does the heavy lifting of maintaining this sheet.
*   **Data Richness:** Extremely High. This sheet contains everything: Title, Date Free From, Date Free To, Metacritic Score, User Score, Publisher, Developer, Genres, HowLongToBeat times, and Download Sizes.
*   **Automation Trick:** You don't need to manually download it! By changing the `/edit#gid=...` part of the URL to `/export?format=csv&gid=...`, you can download the sheet directly as a CSV file in Python via the `requests` library.
    *   *Example Export URL:* `https://docs.google.com/spreadsheets/d/1fpp0u5VHig4KG47Fu0I2EaB7vNCuU4xYBFWRlUKydjk/export?format=csv&gid=216261844`
*   **Formatting Quirks:** The first three rows are header/metadata rows that need to be skipped before reaching the actual data.

## Conclusion & Recommendation

I recommend using the **Community Google Sheet** via the CSV export URL trick. It provides by far the richest dataset, fulfilling all the original goals of the Streamlit app (analyzing tags, publishers, etc.) without needing to rely on the currently broken `epicstore_api` wrapper.

If a fallback is needed, the **Russian Wikipedia** page is the most structured HTML source, and its links could be used to crawl for metadata.

A proof-of-concept scraping script `development/scrape_tests.py` has been created to demonstrate successful extraction of titles and dates from all four of these sources.