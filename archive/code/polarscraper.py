import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium")


@app.cell
def _():
    ## IMPORTS
    import marimo as mo         # run scripts as better Jupyter-style notebooks

    import json                 # API JSON response parsing
    import os                   # file existence checks
    import re                   # string parsing assistance
    import time                 # rate limiting via delays

    import polars as pl         # dataframe manipulation
    import numpy as np          # certain dataframe operations
    import epicstore_api as es  # wrapper to query Epic Games Store for game info
    return es, json, os, pl


@app.cell
def _(pl):
    ## GAME LIST SCRAPER
    def scrape_gamelist() -> pl.DataFrame:
        """
        Scrapes the list of free games and dates from the Google Sheet data source.

        Returns a polars DataFrame with nice column names.
        """

        print("Attempting to load game list from Google Sheet...")
        google_sheet_url = "https://docs.google.com/spreadsheets/d/1pD5h9JfwjewnN7DTKPu-Ad89ukaStLaY7nB5jhOAEyE/export?format=csv&gid=504781956"
        try:
            gdf = pl.read_csv(google_sheet_url)
            print("Successfully loaded data from Google Sheet.")

            gdf = gdf.slice(1).select(['#', 'GG', 'Games', 'Start', 'End']).rename(
                {
                '#': 'order',
                'GG': 'top_game',
                'Games': 'title',
                'Start': 'start_date',
                'End': 'end_date'}
                )
            
            gdf = gdf.with_columns(
                pl.col("order").cast(pl.Int64),
                pl.col("top_game").is_not_null().cast(pl.Int64),
                pl.col("title").str.strip_chars().cast(pl.String),
                pl.col("start_date").str.to_datetime(),
                pl.col("end_date").str.to_datetime()
            )

            return gdf

        except Exception as e:
            print(f"Failed to load data from Google Sheet: {e}")
            return pl.DataFrame()
    return (scrape_gamelist,)


@app.cell
def _(os, pl, scrape_gamelist):
    ## LOAD OR OBTAIN GAME LIST
    def gamelist_path():
        """
        Return path of gamelist.parquet if already exists, otherwise return None.
        """
        paths = ["gamelist.parquet", "../data/gamelist.parquet"]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def load_gamelist(optional_path:str = None, force_reload:bool = False) -> pl.DataFrame:
        """
        Returns the gamelist dataframe whether from file or web scrape.
        Saves to file if it doesn't exist, for example if running script alone.
        """
        if optional_path:
            try:
                return_df = pl.read_parquet(optional_path)
                print(f"Loaded gamelist from alternate path: {optional_path}")
            except Exception as e:
                print(f"Error reading file {optional_path}: {e}")
            return return_df
        elif force_reload:
            print("Force loading gamelist from web scrape and overwrite")
            return_df = scrape_gamelist()
            try:
                return_df.write_parquet("../data/gamelist.parquet")
                print(f"After loading, saved/overwritten to default path: ../data/gamelist.parquet")
            except Exception as e:
                print(f"Failed to save gamelist to '../data/gamelist.csv': {e}")
            return return_df
        elif p := gamelist_path():
            try:
                return_df = pl.read_parquet(p)
                print(f"Loaded gamelist from default path: {p}")
            except Exception as e:
                print(f"Error reading file {p}: {e}")
            return return_df
        else:
            return_df = scrape_gamelist()
            try:
                return_df.write_parquet("../data/gamelist.parquet")
                print(f"After loading, saved to default path: ../data/gamelist.parquet")
            except Exception as e:
                print(f"Failed to save gamelist to '../data/gamelist.csv': {e}")
            return return_df

    gamelist = load_gamelist()
    return (gamelist,)


@app.cell
def _(es):
    ## API
    # verify API wrapper is working
    try:
        api = es.EpicGamesStoreAPI()
        print("EpicGamesStoreAPI initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize EpicGamesStoreAPI: {e}")
        api = None
    return (api,)


@app.cell
def _(api, gamelist, json):
    # TEMP
    g = api.fetch_store_games(count = 7, keywords = gamelist.sample(1)["title"][0])
    g
    def jprint(j):
        print(json.dumps(j, indent = 2, default = str))
    jprint(g)
    return (g,)


@app.cell
def _(g):
    type(g["data"]["Catalog"]["searchStore"]["elements"])
    # g["data"]["Catalog"]["searchStore"]["elements"]
    return


app._unparsable_cell(
    r'''
    def get_api_match(game_title = None: str, delay: float = 1.3):
        return

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
    ''',
    name="_"
)


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run() 