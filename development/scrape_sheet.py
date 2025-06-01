import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import pandas as pd
    import numpy as np
    import re
    import time
    import json
    from epicstore_api import EpicGamesStoreAPI, EGSException
    # import requests                # web fallback
    # from bs4 import BeautifulSoup  # used for web fallback

    # verify API wrapper is working
    try:
        api = EpicGamesStoreAPI()
        print("EpicGamesStoreAPI initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize EpicGamesStoreAPI: {e}")
        api = None

    def scrape_gamelist():
        """
        Scrapes the list of free games and dates from the Google Sheet data source.

        Returns a pandas DataFrame with nice column names.
        """

        print("Attempting to load game list from Google Sheet...")
        google_sheet_url = "https://docs.google.com/spreadsheets/d/1pD5h9JfwjewnN7DTKPu-Ad89ukaStLaY7nB5jhOAEyE/export?format=csv&gid=504781956"
        try:
            gdf = pd.read_csv(google_sheet_url)
            print("Successfully loaded data from Google Sheet.")

            gdf = gdf.drop(index=0)[['#', 'GG', 'Games', 'Start', 'End']].rename(
                columns={
                '#': 'order',
                'GG': 'good_game',
                'Games': 'title',
                'Start': 'start_date',
                'End': 'end_date'}
                ).reset_index()
            gdf["order"] = pd.to_numeric(gdf["order"]).astype("Int64")
            gdf["good_game"] = gdf["good_game"].notna().astype("Int64")
            gdf["title"] = gdf["title"].str.strip()
            gdf["start_date"] = pd.to_datetime(gdf["start_date"])
            gdf["end_date"] = pd.to_datetime(gdf["end_date"])

            return gdf

        except Exception as e:
            print(f"Failed to load data from Google Sheet: {e}")
            return pd.DataFrame(), None

        #TODO: add a manual loading fallback from data folder after first successful scrape
    return EGSException, api, pd, scrape_gamelist, time


@app.cell
def _(EGSException, api, time):

    def get_game_details(game_title: str, delay: float = 1.5):
        """
        Fetches details from Epic Games Store API by title,
        then attempts to get more product details including tags.
    
        Returns a dictionary of extracted game details, None if nothing found.
        """
        print(f"...Sleeping for {delay} seconds for rate limit purposes (initial search)")
        time.sleep(delay)
        print(f"Fetching initial details for: {game_title}...")
        
        extracted_data = {
            "searched_title": game_title,
            "api_found_title": None,
            "api_id": None,
            "api_namespace": None,
            "api_description": None,
            "api_product_slug": None,
            "api_categories": None,
            "api_original_price": None,
            "api_key_image_wide": None,
            "api_tags": None, # This will be our focus
            "api_raw_search_result": None, # For debugging initial search
            "api_raw_product_page": None # For debugging product page call
        }

        try:
            search_results = api.fetch_store_games(keywords=str(game_title).strip(), count=5)
            extracted_data["api_raw_search_result"] = search_results # Store for debugging

            if search_results and search_results.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements'):
                elements = search_results['data']['Catalog']['searchStore']['elements']
                
                best_match_from_search = None
                for element in elements:
                    if str(element.get('title', '')).strip().lower() == str(game_title).strip().lower():
                        best_match_from_search = element
                        print(f"  Exact match found in search: {element.get('title')}")
                        break
                
                if not best_match_from_search and elements:
                    best_match_from_search = elements[0]
                    print(f"  No exact match in search. Using first result: {best_match_from_search.get('title')}")

                if best_match_from_search:
                    extracted_data["api_found_title"] = best_match_from_search.get('title')
                    extracted_data["api_id"] = best_match_from_search.get('id')
                    extracted_data["api_namespace"] = best_match_from_search.get('namespace')
                    extracted_data["api_product_slug"] = best_match_from_search.get('productSlug') # often None here
                    
                    # If productSlug is None from search, try to use the one from title for get_product
                    slug_for_product_page = best_match_from_search.get('productSlug') or \
                                            str(best_match_from_search.get('title','')).lower().replace(' ', '-') # basic slugify

                    if not slug_for_product_page: # If title was empty or slug is still none
                         print(f"  Could not determine a slug for {game_title}. Skipping product page fetch.")
                         return extracted_data # Return what we have so far

                    print(f"  Fetching product page details for slug: {slug_for_product_page}...")
                    print(f"...Sleeping for {delay} seconds for rate limit purposes (product page)")
                    time.sleep(delay) # Additional delay before the second API call
                    
                    try:
                        # According to epicstore-api docs, get_product uses 'slug'
                        product_page_data = api.get_product(slug=slug_for_product_page)
                        extracted_data["api_raw_product_page"] = product_page_data # Store for debugging
                        
                        if product_page_data:
                            print(f"  Successfully fetched product page for {slug_for_product_page}")
                            # Now extract details from product_page_data
                            # This structure might differ from the search result element
                            extracted_data["api_description"] = product_page_data.get('description')
                            
                            # Price from product page
                            price_info = product_page_data.get('price', {}).get('totalPrice', {})
                            extracted_data["api_original_price"] = price_info.get('originalPrice')

                            # Key Images from product page
                            key_images = product_page_data.get('keyImages', [])
                            for img in key_images:
                                if img.get('type') == 'DieselStoreFrontWide': # Or common wide image types
                                    extracted_data["api_key_image_wide"] = img.get('url')
                                    break
                            
                            # Categories from product page
                            categories_list = product_page_data.get('categories', [])
                            extracted_data["api_categories"] = [cat.get('path') for cat in categories_list if cat.get('path')]

                            # TAGS from product page - this is a guess at structure, inspect api_raw_product_page
                            # The epicstore-api docs mention that tags might be under a 'tags' key
                            # or sometimes within customAttributes or elsewhere.
                            # For Limbo, search_result had 'tags': [], let's see product_page_data
                            tags_data = product_page_data.get('tags') 
                            if tags_data: # If it's a list of dicts with 'id' or 'name'
                                if all(isinstance(tag, dict) and 'name' in tag for tag in tags_data):
                                     extracted_data["api_tags"] = [tag['name'] for tag in tags_data if tag.get('name')]
                                elif all(isinstance(tag, dict) and 'id' in tag for tag in tags_data): # If tags are just IDs
                                     extracted_data["api_tags"] = [tag['id'] for tag in tags_data if tag.get('id')]
                                else: # if it's some other structure
                                     extracted_data["api_tags"] = tags_data # store as is for now
                            else: # Check customAttributes if not found directly
                                custom_attributes = product_page_data.get('customAttributes', [])
                                for attr in custom_attributes:
                                    if 'tag' in attr.get('key','').lower(): # look for keys containing 'tag'
                                        extracted_data["api_tags"] = attr.get('value') # take the first one found
                                        break
                            if not extracted_data["api_tags"]: # if still no tags
                                 print(f"  Tags not found directly in product_page_data for {slug_for_product_page}. Check api_raw_product_page.")


                        else:
                            print(f"  Failed to fetch product page for {slug_for_product_page} (get_product returned None/empty).")
                    except EGSException as e_prod:
                        print(f"  API Error fetching product page for '{slug_for_product_page}': {e_prod}")
                    except Exception as e_gen_prod:
                        print(f"  Unexpected error fetching product page for '{slug_for_product_page}': {e_gen_prod}")
                else: # No best_match_from_search
                    print(f"  No search results elements found for '{game_title}'.")
            else: # No search results structure
                print(f"  No valid search results structure for '{game_title}'.")
            
            return extracted_data

        except EGSException as e_search:
            print(f"  API Error during initial search for '{game_title}': {e_search}")
            return extracted_data # Return partially filled data with error noted
        except Exception as e_gen_search:
            print(f"  Unexpected error during initial search for '{game_title}': {e_gen_search}")
            return extracted_data # Return partially filled data

    return (get_game_details,)


@app.cell
def _(get_game_details, pd, scrape_gamelist):
    games_df = scrape_gamelist()

    if games_df.empty:
        print("Could not load game data from sheet. Exiting.")
        exit()

    all_game_details = []
    # TESTING: only look at first 5 games
    games_to_process = games_df.head(10) 
    # games_to_process = games_df

    for index, row in games_to_process.iterrows():
        game_title = row['title']
        if pd.isna(game_title) or str(game_title).strip() == "":
            print(f"Skipping row {index} due to empty game title.")
            continue

        details = get_game_details(game_title)

        if details:
            # Combine original row data with fetched details
            # This is a basic merge; more sophisticated merging might be needed
            combined_info = row.to_dict()
            combined_info['api_details'] = details # Store the whole API response for now
            # We'll refine what to extract from 'details' later (tags, price, etc.)
            # Example: combined_info['api_title'] = details.get('title')
            #          combined_info['api_description'] = details.get('description')
            #          combined_info['api_tags'] = details.get('tags') # Structure of tags needs checking
            all_game_details.append(combined_info)
        else:
            # Still add original info even if API fetch fails, marking it
            combined_info = row.to_dict()
            combined_info['api_details'] = None
            all_game_details.append(combined_info)

    # Convert the list of dictionaries to a DataFrame
    processed_games_df = pd.DataFrame(all_game_details)

    print("\nProcessed Games DataFrame:")
    print(processed_games_df.head())

    # Save the processed data
    output_path = "../data/May2025.csv" # Save to top-level data folder
    try:
        processed_games_df.to_csv(output_path, index=False)
        print(f"Successfully saved processed data to {output_path}")
    except Exception as e:
        print(f"Failed to save data: {e}")
    return (processed_games_df,)


@app.cell
def _():
    return


@app.cell
def _(processed_games_df):
    processed_games_df["api_details"]
    return


@app.cell
def _():
    import altair as alt
    return


@app.cell
def _():
    #TODO: re-implement later after dev stage 
    #  (to allow notebook visibility into saved objects and keep in-scope)
    # def main():
    # # ensure imports do not auto-run main()
    # if __name__ == "__main__":
    #     main() 
    return


if __name__ == "__main__":
    app.run()
