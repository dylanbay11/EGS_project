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
    Recursively resolves references within the Metacritic Next.js JSON payload.

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
    Searches Metacritic for a game title and extracts data from the Next.js payload.

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
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')

        match = re.search(r'type="application/json".*?>(\[.*?\])</script>', html)
        if not match:
            return None

        data = json.loads(match.group(1))

        results = []
        for i, item in enumerate(data):
            if isinstance(item, dict) and 'title' in item and 'slug' in item and 'type' in item:
                # We need to manually resolve criticScore to make sure we don't accidentally fall into another part of the tree
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
        print(f"Error searching for {game_name}: {e}")
        return None

def test_scrape():
    """
    Executes a test scrape of Metacritic for the first 10 games in the dataset.

    Extracts details for each target, matches the highest scoring query result
    to the target, appends results into a dataframe, and outputs it to a CSV file.
    """
    df = pd.read_csv('data/epic_free_games_with_api_details.csv')
    games = df['title'].head(10).tolist()

    results = []
    for game in games:
        print(f"Searching for: {game}")
        data = search_metacritic(game)
        if data and len(data) > 0:
            exact_matches = [d for d in data if str(d.get('title')).lower() == game.lower()]
            best_match = exact_matches[0] if exact_matches else data[0]

            results.append({
                'search_term': game,
                'mc_title': best_match.get('title'),
                'mc_slug': best_match.get('slug'),
                'releaseDate': best_match.get('releaseDate'),
                'criticScore': best_match.get('criticScore'),
                'rating': best_match.get('rating'),
                'platforms': [p.get('name') for p in best_match.get('platforms', []) if isinstance(p, dict)]
            })
        else:
            results.append({
                'search_term': game,
                'mc_title': None
            })

        time.sleep(random.uniform(2, 4)) # Rate limiting

    res_df = pd.DataFrame(results)
    print(res_df)
    res_df.to_csv('outputs/metacritic_sample.csv', index=False)

if __name__ == '__main__':
    test_scrape()
