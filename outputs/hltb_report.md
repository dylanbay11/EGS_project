# HowLongToBeat Integration Feasibility Report

## Feasibility

Integrating data from HowLongToBeat (HLTB) into the existing Epic Games Store dataset is highly feasible. The `howlongtobeatpy` Python package provides a reliable and straightforward way to search for games and extract metadata.

Our initial tests using the unique games found in `cleaned_merged_data.csv` (around 687 unique titles) showed successful matches for almost all the titles tested, with the API correctly returning completion times, review scores, and platforms.

## Potential Data Gained

By integrating HowLongToBeat, we could enrich our dataset with the following fields for each game:

- **Game Name (Matched):** The exact title as it appears on HLTB (`game_name`).
- **Main Story Time:** Average time to complete the main objectives (`main_story`).
- **Main + Extra Time:** Average time to complete main objectives plus extras (`main_extra`).
- **Completionist Time:** Average time to 100% complete the game (`completionist`).
- **All PlayStyles Time:** Average time considering all playstyles (`all_styles`).
- **Review Score:** The community review score percentage (`review_score`).
- **Platforms:** A list of platforms the game is available on (`profile_platforms`).
- **Developer/Publisher:** The primary developer/publisher metadata (`profile_dev`).
- **Release Year:** The global release year/date (`release_world`).
- **Game Type:** Useful to determine if an entry is a game, DLC, or mod (`game_type`).
- **Co-Op / MP Times:** Average times for multiplayer or co-op, if applicable (`coop_time`, `mp_time`).
- **Image URL:** A direct link to the game's box art/image on HLTB (`game_image_url`).

## Best Practices and Rate Limiting

Since we have around 687 unique titles to search, making these requests should be done carefully to avoid rate-limiting or being blocked by HowLongToBeat:

1. **Caching/Batching:** We should implement a similar caching mechanism as we do for Wikipedia or the Epic Games Store, saving a local JSON or CSV of matched HLTB data and only searching for newly added titles.
2. **Delay Between Requests:** Introducing a delay (e.g., `time.sleep(1)` or `time.sleep(2)`) between requests is crucial to avoid triggering anti-bot protections.
3. **Fuzzy Matching:** Since titles in our Google Sheets data might slightly differ from HLTB (e.g., "Broken Sword : Reforged" vs "Broken Sword: The Shadow of the Templars"), we should select the result with the highest `similarity` score that `howlongtobeatpy` provides.
4. **Handling Missing Data:** Some titles (especially upcoming or very obscure indie/mobile games) may return empty lists. These should be logged or recorded as empty to prevent infinite retries.

## Next Steps

I recommend creating a dedicated script (e.g., `development/scrape_hltb.py`) that reads the unique titles from `cleaned_merged_data.csv`, fetches the corresponding HLTB data respecting a 1-2 second delay, and outputs a new `hltb_enriched_data.csv`. This data can then be joined with the main dataset for visualization in the Streamlit app.
