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
        print(f"Columns found: {gdf.columns.tolist()}")
        print("First 5 rows of the loaded data:")
        print(gdf.head())

        #TODO: make nice column names and enforce proper data types
        
        return gdf
        
    except Exception as e:
        print(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame(), None

    #TODO: add a manual loading fallback from data folder after first successful scrape

def get_game_details(game_title: str, delay: float = 1.5):
    """
    Fetches details from Epic Games Store API by title
    
    Returns closest match title's JSON, None if nothing found

    #TODO: return in a more structured format AND indicate if the match was exact or inferred
    """
    
    time.sleep(delay)
    print(f"Fetching details for: {game_title}...")
    try:
        # NOTE: The API wrapper's get_product might require a namespace/offer_id, which we don't have yet.
        search_results = api.fetch_store_games(keywords=str(game_title).strip(), count = 5)
        
        # if we get a response AND it matches the JSON format we expect, look at possible matches
        if search_results and search_results.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements'):
            elements = search_results['data']['Catalog']['searchStore']['elements']
            
            best_match = None
            for element in elements:
                if str(element.get('title', '')).strip().lower() == str(game_title).strip().lower():
                    best_match = element
                    print(f"  Exact match found: {element.get('title')}")
                    break

            #TODO: add more extensive matching logic and waittime, following "archive/code/reviewget.py"
            # for now, just use the first result if no exact match
            
            if not best_match and elements:
                best_match = elements[0]
                print(f"  No exact match. Using first result: {best_match.get('title')}")
            
            if best_match:
                return best_match
            else:
                print(f"  No search results found for '{game_title}'.")
                return None
        else:
            print(f"  No search results structure for '{game_title}'.")
            return None
    except EGSException as e:
        print(f"  API Error fetching details for '{game_title}': {e}")
        return None
    except Exception as e:
        print(f"  Unexpected error fetching details for '{game_title}': {e}")
        return None

def main():
    games_df = scrape_gamelist()
    
    if games_df.empty:
        print("Could not load game data from sheet. Exiting.")
        return

    all_game_details = []
    # TESTING: only look at first 5 games
    games_to_process = games_df.head(5) 
    # games_to_process = games_df

    for index, row in games_to_process.iterrows():
        game_title = row[game_title_col_name]
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
            
        print("--- Waiting before next API call ---")
        time.sleep(2) # RATE LIMITING: Wait for 2 seconds between API calls

    # Convert the list of dictionaries to a DataFrame
    processed_games_df = pd.DataFrame(all_game_details)
    
    print("\nProcessed Games DataFrame:")
    print(processed_games_df.head())
    
    # Save the processed data
    output_path = "../data/epic_games_data_with_api_details.csv" # Save to top-level data folder
    try:
        processed_games_df.to_csv(output_path, index=False)
        print(f"Successfully saved processed data to {output_path}")
    except Exception as e:
        print(f"Failed to save data: {e}")

# ensure imports do not auto-run main()
if __name__ == "__main__":
    main() 