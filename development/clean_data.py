import pandas as pd
import re
import os

import glob

def get_latest_file(data_dir, pattern_xlsx, pattern_csv=None):
    """Helper to find the most recently created/named file matching a pattern."""
    files = glob.glob(os.path.join(data_dir, pattern_xlsx))
    if pattern_csv:
        files.extend(glob.glob(os.path.join(data_dir, pattern_csv)))
    if not files:
        raise FileNotFoundError(f"No files found matching {pattern_xlsx} or {pattern_csv}")
    files.sort(reverse=True)
    return files[0]


def clean_gsheets():
    """
    Cleans the Google Sheets data.

    Data Key for the 'TYPE' column (extracted from original headers):
      - pack: packs, in-game content, DLC
      - dupe: dupe games, packs, in-game content, DLC
      - free: free games
      - other: other unique games (another days, different number of days, DLC's, fails)
      - pack2: other packs, in-game content, DLC
      - dupe2: other dupe games, packs, in-game content, DLC
      - mobile: mobile unique games
      - pack3: mobile packs, in-game content, DLC
      - dupe3: mobile dupe games, packs, in-game content, DLC
      - next: next gifts (future/upcoming games)
    """
    # Find the latest Google Sheets file dynamically
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    file_path = get_latest_file(data_dir, "20*-gsheets.xlsx", "20*-gsheets.csv")

    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path, engine='openpyxl', skiprows=15)
    else:
        df = pd.read_csv(file_path, skiprows=15)

    # Keep the first 7 columns and rename to standard names
    df = df.iloc[:, 0:7].copy()
    df.columns = ['FROM', 'TO', 'DAY', 'DAYS', 'TYPE', 'Title', 'NOTES']

    # Forward-fill event-related columns for days with multiple games
    cols_to_ffill = ['FROM', 'TO', 'DAY', 'DAYS', 'TYPE']
    for col in cols_to_ffill:
        df[col] = df[col].ffill()

    # If Title is NaN but NOTES is present (e.g., in a bundle like Trine Collection), use NOTES
    df['Title'] = df['Title'].fillna(df['NOTES'])

    # Clean string values, remove empties, and filter out future placeholders
    df = df[df['Title'].notna()].copy()
    df['Title'] = df['Title'].astype("string").str.strip()
    df = df[~df['Title'].isin(['', '-', 'nan'])]
    df = df[df['TYPE'] != '*']

    return df

def clean_wiki():
    """
    Loads and cleans the scraped Wikipedia dataset.

    Returns:
        pd.DataFrame: A DataFrame with exploded titles replacing bundle text.
    """
    # Load the Wikipedia CSV file dynamically
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    file_path = get_latest_file(data_dir, "20*-wiki.csv")
    df = pd.read_csv(file_path)

    # Explode rows where Title has multiple games separated by \n
    df['Title'] = df['Title'].astype("string").str.split('\n')
    df = df.explode('Title')
    df['Title'] = df['Title'].astype("string").str.strip()

    return df

def normalize_title_series(s):
    """Normalize a title Series for robust merging: lowercase, remove special characters, and strip extra spaces."""
    return s.astype("string").str.lower().str.replace(r'[^a-z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()

def main():
    """
    Main function to execute the data cleaning pipeline.

    Loads and cleans Google Sheets and Wikipedia datasets separately, normalizes
    titles to perform a left join merging Wikipedia metadata into the primary
    Google Sheets dataset, and saves the result to a CSV file.
    """
    print("Cleaning Google Sheets data...")
    gsheets_df = clean_gsheets()

    print("Cleaning Wikipedia data...")
    wiki_df = clean_wiki()

    # Create temporary normalized title columns for merging
    gsheets_df['merge_title'] = normalize_title_series(gsheets_df['Title'])
    wiki_df['merge_title'] = normalize_title_series(wiki_df['Title'])

    print("Merging datasets...")
    # LEFT JOIN: keep all from gsheets (primary source), enrich with wiki info where possible
    merged_df = pd.merge(gsheets_df, wiki_df, on='merge_title', how='left', suffixes=('_gsheets', '_wiki'))

    # Drop the temporary merge column
    merged_df = merged_df.drop('merge_title', axis=1)

    print(f"Merge complete. Result shape: {merged_df.shape}")
    print(f"Games successfully matched with Wikipedia data: {merged_df['Title_wiki'].notna().sum()}")

    # Save output to data directory
    output_path = os.path.join(os.path.dirname(__file__), '../data/cleaned_merged_data.csv')
    merged_df.to_csv(output_path, index=False)
    print(f"Saved merged dataset to: {output_path}")

if __name__ == "__main__":
    main()
