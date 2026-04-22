# Potential Information Available via Epic Games Store API

After exploring the `epicstore_api` library and running some test queries against the Epic Games Store (EGS) endpoints, I've compiled a list of valuable data points that can be extracted for each game. These data points can significantly enhance our dataset and provide rich avenues for analysis and visualization in the Streamlit app.

## 1. Core Metadata
The `searchStore` and product specific endpoints return a wealth of basic metadata.

* **Title (`title`)**: The official name of the game.
* **Descriptions (`description`)**: A short summary of the game, useful for textual analysis or displaying tooltips in the UI.
* **Developer and Publisher**: Information on who made and published the game. This can be found in the `seller` field (e.g., `{"name": "Maddy Makes Games"}`) or the `meta` object inside the product page data.
    * **Visualization Idea**: Bar charts of the most generous developers/publishers (giving away the most games or the highest total retail value).
* **Release Dates (`effectiveDate`, `releaseDate`)**: The date the game was released on EGS.
    * **Visualization Idea**: Plotting the age of games when they are given away (e.g., "Does Epic give away older games or newer games?").

## 2. Pricing and Valuation
One of the most interesting aspects of the EGS giveaways is the monetary value. The API provides detailed pricing data within the `price` object for a specific country (e.g., US).

* **Original Price (`originalPrice`)**: The base retail price of the game in cents (e.g., 1999 for $19.99).
* **Discount Price (`discountPrice`)**: The current price, which could be 0 during a giveaway.
* **Visualization Idea**:
    * A line chart showing the cumulative dollar amount given away over time.
    * A histogram of game prices given away (e.g., how many $60 AAA games vs. $15 indie games).
    * Average game price by year of giveaway.

## 3. Categories and Tags
Epic categorizes games extensively, which is fantastic for grouping data.

* **Tags (`tags`)**: Each game returns a list of tag IDs (e.g., `[{"id": "1216"}, {"id": "1188"}]`). The API also allows fetching the catalog tags (`fetch_catalog_tags`), which maps these IDs to human-readable names like "Single Player", "Windows", "Action", "Indie", etc.
* **Categories (`categories`)**: The structural path of the item, like `games/edition/base` or `applications`. Useful for filtering out DLCs or non-game applications if they sneak in.
* **Visualization Idea**:
    * A pie chart or bar chart showing the most common genres (Action, Platformer, RPG) given away.
    * A correlation chart between genres and retail price or rating.
    * Filtering the main dataset by tag in the Streamlit app.

## 4. Media and Imagery
The API provides links to various promotional images.

* **Key Images (`keyImages`)**: A list of image URLs with specific types (e.g., `OfferImageWide`, `OfferImageTall`, `Thumbnail`).
* **Visualization Idea**:
    * Displaying the actual cover art (`OfferImageTall`) or landscape banner (`OfferImageWide`) in the Streamlit app next to the game title to make the UI pop.

## 5. Platform and System Requirements
By querying the specific product slug (e.g., `celeste`), we can retrieve deeper page data.

* **Platforms**: Supported OS (Windows, Mac).
* **System Requirements**: Detailed hardware requirements can sometimes be parsed from the page data if we dig into the `data` -> `requirements` field.
* **Visualization Idea**:
    * Charting PC-only vs PC/Mac compatible giveaways.

## 6. OpenCritic Ratings
The Epic Games API integrates with OpenCritic. Using a GraphQL query (`productReviewsQuery`), we can fetch review metrics for certain games using their SKU or Slug.

* **OpenCritic Score**: The aggregate score from critics.
* **Percent Recommended**: The percentage of critics recommending the game.
* **Review Count**: How many reviews it has.
* **Top Reviews**: Snippets from notable outlets.
* **Visualization Idea**:
    * Scatter plot of Price vs. OpenCritic Score.
    * Identifying the "highest-rated" free games of all time.
    * A timeline showing the average quality (score) of giveaways over the years.

## Summary of Implementation
To get this data efficiently:
1. We can use the `epicstore_api`'s `fetch_store_games(keywords="Game Title", count=1, with_price=True)` or map our existing list of free games using a fuzzy matcher to avoid querying too many times.
2. For tags, we can hit `api.fetch_catalog_tags()` once, build a dictionary, and map the IDs returned by the search query.
3. For deep details (like OpenCritic or specific meta info), we use `api.get_product(productSlug)` once we obtain the correct `productSlug` from the search step.
