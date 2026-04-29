import json
import re
import urllib.request
import urllib.parse
import time
import random
import pandas as pd
import os

def resolve(data, obj, max_depth=10, current_depth=0):
    """
    Recursively resolve references within the Metacritic Next.js JSON payload.

    Args:
        data (list): The root JSON object list containing the referable data.
        obj: The current object or index being resolved.
        max_depth (int): Limit recursion depth to prevent infinite loops.
        current_depth (int): Tracker for current recursion level.

    Returns:
        The recursively resolved object (dict, list, bool, int, string, etc.).
    """
    if current_depth > max_depth: return obj

    if isinstance(obj, bool):
        return obj
    elif isinstance(obj, int):
        if obj >= 0 and obj < len(data):
            return resolve(data, data[obj], max_depth, current_depth + 1)
        return obj
    elif isinstance(obj, list):
        return [resolve(data, x, max_depth, current_depth + 1) for x in obj]
    elif isinstance(obj, dict):
        return {k: resolve(data, v, max_depth, current_depth + 1) for k, v in obj.items()}
    return obj

def search_metacritic(game_name):
    """
    Search Metacritic for a game title and extract data from the Next.js payload.

    Args:
        game_name (str): The name of the game to query.

    Returns:
        list[dict] | None: A list of matched game dictionaries including title,
                           slug, releaseDate, criticScore, rating, and platforms.
    """
    query = urllib.parse.quote(game_name)
    url = f"https://www.metacritic.com/search/{query}/"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        match = re.search(r'type="application/json".*?>(\[.*?\])</script>', html)
        if not match:
            return None

        data = json.loads(match.group(1))

        results = []
        for i, item in enumerate(data):
            if isinstance(item, dict) and 'title' in item and 'slug' in item and 'type' in item:
                cs = None
                if 'criticScoreSummary' in item and isinstance(item['criticScoreSummary'], int):
                    cs_dict = data[item['criticScoreSummary']]
                    if isinstance(cs_dict, dict) and 'score' in cs_dict:
                        score_idx = cs_dict['score']
                        if isinstance(score_idx, int) and score_idx < len(data):
                            score_val = data[score_idx]
                            if isinstance(score_val, int):
                                cs = score_val

                resolved_item = resolve(data, item)

                if resolved_item.get('type') == 'game-title':
                    resolved_item['criticScore'] = cs
                    results.append(resolved_item)

        return results
    except Exception as e:
        print(f"Error searching for {game_name}: {e}", flush=True)
        return None

def scrape_and_merge():
    """
    Scrape Metacritic for unique games and merge results into the main dataset.

    Loads data/cleaned_merged_data.csv, extracts unique game titles,
    queries Metacritic with caching to prevent data loss upon interruption,
    and saves the combined enriched dataframe to data/merge_mc.csv.
    """
    input_file = 'data/cleaned_merged_data.csv'
    output_file = 'data/merge_mc.csv'
    cache_file = 'outputs/metacritic_cache.json'

    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found.", flush=True)
        return

    df = pd.read_csv(input_file)
    games = df['Title_gsheets'].dropna().unique().tolist()

    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)

    new_results = 0
    total_games = len(games)

    for i, game in enumerate(games):
        # Avoid redundant spaces
        game_clean = str(game).strip()
        if not game_clean:
            continue

        if game_clean in cache:
            continue

        print(f"[{i+1}/{total_games}] Searching for: {game_clean}", flush=True)
        data = search_metacritic(game_clean)

        if data and len(data) > 0:
            exact_matches = [d for d in data if str(d.get('title')).lower() == game_clean.lower()]
            best_match = exact_matches[0] if exact_matches else data[0]

            platforms = []
            for p in best_match.get('platforms', []):
                if isinstance(p, dict) and 'name' in p:
                    platforms.append(p['name'])
                elif isinstance(p, str):
                    platforms.append(p)

            cache[game_clean] = {
                'mc_title': best_match.get('title'),
                'mc_slug': best_match.get('slug'),
                'mc_releaseDate': best_match.get('releaseDate'),
                'mc_criticScore': best_match.get('criticScore'),
                'mc_rating': best_match.get('rating'),
                'mc_platforms': ", ".join(platforms) if platforms else None
            }
        else:
            cache[game_clean] = {
                'mc_title': None,
                'mc_slug': None,
                'mc_releaseDate': None,
                'mc_criticScore': None,
                'mc_rating': None,
                'mc_platforms': None
            }

        new_results += 1

        # Incremental save
        if new_results % 10 == 0:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

        # Fast scrape
        time.sleep(0.1)

    # Final save of cache
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # Merge back into dataframe
    mc_data = []
    for game, meta in cache.items():
        row = {'Title_gsheets': game}
        row.update(meta)
        mc_data.append(row)

    mc_df = pd.DataFrame(mc_data)

    # Left join onto the original dataframe
    # Using Pandas 3.0 CoW, standard assignments and direct merge
    merged_df = pd.merge(df, mc_df, on='Title_gsheets', how='left')

    merged_df.to_csv(output_file, index=False)
    print(f"Successfully saved merged data to {output_file}", flush=True)

if __name__ == '__main__':
    scrape_and_merge()
