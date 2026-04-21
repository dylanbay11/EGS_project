# Epic Games Store API Feasibility & Replacement Report

## High-Level Overview of the `epicstore_api` Wrapper
The `epicstore_api` library is an unofficial Python wrapper for the Epic Games Store (EGS) Web API. Under the hood, it performs the following primary tasks:
- **Authentication Bypass & Anti-Bot Evasion:** EGS has anti-bot protections (like Cloudflare) on its main GraphQL endpoint (`https://store.epicgames.com/graphql`). The library tries to bypass these using `cloudscraper`, which emulates a real browser's TLS fingerprints and handles Cloudflare challenges.
- **GraphQL Queries:** It abstracts away complex, hardcoded GraphQL queries (e.g. `STORE_QUERY`, `CATALOG_QUERY`, `OFFERS_QUERY`) used to fetch detailed catalog data, search results, pricing, and tags.
- **Content API Queries:** It provides wrappers for the simpler static content endpoints, like `https://store-content.ak.epicgames.com/api/...` which don't require the same level of anti-bot bypass.
- **Error Handling:** It automatically parses responses and swallows random unhelpful errors, like the `1004` error code that Epic's API occasionally spits out despite succeeding.

## Feasibility of Bypassing the Wrapper API
It is **highly feasible** to do your project without this wrapper, provided you use the right endpoints. The main `https://store.epicgames.com/graphql` endpoint requires `cloudscraper` (or a similar anti-bot library) because a simple `requests.post()` will yield a `403 Forbidden` error. 

However, your specific goal of mapping scraped games to the catalog and retrieving details (price, genre, tags) can largely be accomplished using Epic's static, non-Cloudflare-protected backend endpoints:

### Alternative Endpoints (No Cloudscraper Required)
1. **Free Games List:**
   - Endpoint: `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US`
   - You can get all the free games, along with their `title`, `productSlug`, `price`, and basic `tags` directly here using the standard `requests` library. No anti-bot bypass is needed.
2. **Product Page Info:**
   - Endpoint: `https://store-content.ak.epicgames.com/api/en-US/content/products/<productSlug>`
   - Once you have the `productSlug` from the free games list, you can query this endpoint to get deep details about the game, such as description, developer attributions, and page layout elements. 

## Tips for Improvements & Better Approaches

### 1. Tag Extraction
In your `scrape_sheet.py`, you were manually trying to guess the structure of `tags` from the `get_product()` response. 
- The easiest way to get genre and standard catalog tags is actually through the `freeGamesPromotions` static endpoint or the search GraphQL queries. The tags usually look like `[{'id': '1216'}, {'id': '1370'}]` in those payloads, which map to internal Epic category IDs.
- For product-specific content attributes, instead of manually parsing the frontend layouts via `get_product`, rely on the `customAttributes` dictionary returned by `freeGamesPromotions` or the `searchStore` GraphQL query. Keys like `developerName` and `publisherName` are consistently placed there.

### 2. Fuzzy Matching Game Names
Epic's exact search behavior can be finicky. Sometimes "Tiny Tina's Wonderlands" in your dataset is "Tiny Tina's Assault on Dragon Keep" in the API.
- Use a dedicated string matching library like `rapidfuzz` or `thefuzz`. 
- **Workflow:** 
  1. Fetch the entire catalog or the current free games list in one go.
  2. Extract the titles into a list.
  3. When querying a title from your dataset, run `process.extractOne(target_title, epic_titles, scorer=fuzz.token_set_ratio)`.
  4. Use a threshold (e.g., >85%). If it matches, use the associated `productSlug` to grab the rest of the data. This completely avoids making rate-limited individual search queries for every single row.

### 3. Rate Limiting and Bulk Queries
- In `scrape_sheet.py`, you are doing a `time.sleep(1.5)` between each search. Since you just want a dataset analysis of a predefined list, try fetching the full catalog list (or large chunks of it) directly via the GraphQL `searchStore` query with a high `count` (e.g. 1000) using `cloudscraper` once, save it to a JSON file, and do all your lookups locally. This is significantly faster and less prone to random disconnects or rate-limiting bans.