import pandas as pd
from howlongtobeatpy import HowLongToBeat
import time
import os
import sys

def scrape_hltb_data():
    """
    Scrapes HowLongToBeat (HLTB) data for unique games in the cleaned dataset.

    Reads the merged data to extract unique titles and queries the HLTB API to
    retrieve completion times, review scores, and related metadata. Saves
    the results incrementally to avoid data loss.
    """

    # Determine the input file
    input_file = "data/merge_mc.csv"
    if not os.path.exists(input_file):
        print(f"Fallback: {input_file} not found. Using data/cleaned_merged_data.csv instead.", flush=True)
        input_file = "data/cleaned_merged_data.csv"

    output_file = "outputs/hltb_data.csv"

    print(f"Reading dataset from {input_file}", flush=True)
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}", flush=True)
        return

    unique_games = df['Title_gsheets'].dropna().unique()
    print(f"Found {len(unique_games)} unique games.", flush=True)

    # Load existing data if we're resuming
    existing_data = []
    processed_games = set()
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            existing_data = existing_df.to_dict('records')
            processed_games = set(existing_df['Original_Title'].dropna())
            print(f"Loaded {len(processed_games)} previously processed games from {output_file}", flush=True)
        except Exception as e:
            print(f"Could not load existing output file: {e}", flush=True)

    hltb = HowLongToBeat()
    new_data = []

    # For testing/demonstration, we'll process all of them
    games_to_process = [g for g in unique_games if g not in processed_games]
    print(f"Processing {len(games_to_process)} remaining games...", flush=True)



    for i, game in enumerate(games_to_process):
        print(f"[{i+1}/{len(games_to_process)}] Searching for: {game}", flush=True)

        row_data = {
            'Original_Title': game,
            'HLTB_Found': False,
            'HLTB_Game_Name': None,
            'HLTB_Main_Story': None,
            'HLTB_Main_Extra': None,
            'HLTB_Completionist': None,
            'HLTB_All_Styles': None,
            'HLTB_Review_Score': None,
            'HLTB_Platforms': None,
            'HLTB_Release_World': None,
            'HLTB_Similarity': None
        }

        try:
            results = hltb.search(game)
            if results and len(results) > 0:
                # Results are usually sorted by similarity/relevance, take the first one
                best_match = results[0]

                row_data.update({
                    'HLTB_Found': True,
                    'HLTB_Game_Name': best_match.game_name,
                    'HLTB_Main_Story': best_match.main_story,
                    'HLTB_Main_Extra': best_match.main_extra,
                    'HLTB_Completionist': best_match.completionist,
                    'HLTB_All_Styles': best_match.all_styles,
                    'HLTB_Review_Score': best_match.review_score,
                    'HLTB_Platforms': ', '.join(best_match.profile_platforms) if getattr(best_match, 'profile_platforms', None) else None,
                    'HLTB_Release_World': getattr(best_match, 'release_world', None),
                    'HLTB_Similarity': getattr(best_match, 'similarity', None)
                })
                print(f"  -> Found match: {best_match.game_name}", flush=True)
            else:
                print("  -> No match found.", flush=True)
        except Exception as e:
            print(f"  -> Error searching for {game}: {e}", flush=True)

        new_data.append(row_data)
        existing_data.append(row_data)

        # Save periodically
        if (i + 1) % 5 == 0:
            pd.DataFrame(existing_data).to_csv(output_file, index=False)
            print(f"Saved progress to {output_file}", flush=True)

        # Respect rate limits
        time.sleep(1.5)

    # Final save
    if new_data:
        pd.DataFrame(existing_data).to_csv(output_file, index=False)
        print(f"Finished. Total data saved to {output_file}", flush=True)
    else:
        print("No new data to save.", flush=True)

    # Merge the scraped data back onto the original dataset
    if os.path.exists(output_file):
        print("Merging HLTB data back onto the original dataset...", flush=True)
        try:
            # Read original dataset
            orig_df = pd.read_csv(input_file)
            # Read HLTB data
            hltb_df = pd.read_csv(output_file)

            # Perform a left join
            # We use 'Title_gsheets' from original and 'Original_Title' from HLTB
            merged_df = orig_df.merge(hltb_df, left_on='Title_gsheets', right_on='Original_Title', how='left')

            # Save the final dataset
            final_output = "data/merge_hltb.csv"
            merged_df.to_csv(final_output, index=False)
            print(f"Successfully saved merged dataset to {final_output}", flush=True)
        except Exception as e:
            print(f"Error during merging: {e}", flush=True)


if __name__ == "__main__":
    scrape_hltb_data()
