import marimo

__generated_with = "0.23.2"
app = marimo.App()


@app.cell
def _():
    """Marimo cell that imports required libraries for the notebook."""
    import pandas as pd  # ty:ignore[unresolved-import]
    import numpy as np  # ty:ignore[unresolved-import]
    import os

    return os, pd


@app.cell
def _(os, pd):
    """Marimo cell that handles data loading of raw and intermediate datasets."""
    # --- 1. DATA LOADING ---
    # Load datasets (using raw source files and intermediate/merged ones)
    data_dir = os.path.join(os.path.dirname(__file__), '../data')

    import glob
    def get_latest_file(directory, pattern_main, pattern_alt=None):
        files = glob.glob(os.path.join(directory, pattern_main))
        if pattern_alt:
            files.extend(glob.glob(os.path.join(directory, pattern_alt)))
        files.sort(reverse=True)
        return files[0] if files else None

    # Source 1: Google Sheets (skipping first 15 rows based on project memory, and row 16 which is totals in actual parsing)
    print("Loading GSheets data...")
    latest_gsheets = get_latest_file(data_dir, '20*-gsheets.xlsx', '20*-gsheets.csv')
    if latest_gsheets.endswith('.xlsx'):
        gsheets_csv = pd.read_excel(latest_gsheets, engine='openpyxl', skiprows=15)
    else:
        gsheets_csv = pd.read_csv(latest_gsheets, skiprows=15)

    # Source 2: Wikipedia data
    print("Loading Wiki data...")
    latest_wiki = get_latest_file(data_dir, '20*-wiki.csv')
    wiki_csv = pd.read_csv(latest_wiki)
    latest_wiki_enriched = get_latest_file(data_dir, '20*-wiki-enriched.csv')
    wiki_enriched_csv = pd.read_csv(latest_wiki_enriched)

    # Intermediate/Merged data
    print("Loading Merged data...")
    merged_csv = pd.read_csv(os.path.join(data_dir, 'cleaned_merged_data.csv'))

    # API details
    print("Loading API details data...")
    api_details_csv = pd.read_csv(os.path.join(data_dir, 'epic_free_games_with_api_details.csv'))

    datasets = {
        'GSheets': gsheets_csv,
        'Wiki': wiki_csv,
        'Wiki Enriched': wiki_enriched_csv,
        'Merged': merged_csv,
        'API Details': api_details_csv
    }
    return datasets, gsheets_csv, wiki_csv


@app.cell
def _(datasets):
    """Marimo cell for executing basic Exploratory Data Analysis (EDA) and overviews."""
    # --- 2. BASIC EDA & OVERVIEW ---
    print("\n--- Basic Dataset Overview ---")
    for _name, _df in datasets.items():
        print(f"\n[{_name}]")
        print(f"Shape: {_df.shape}")
        print("\nInfo:")
        _df.info()
        print("\nSample (first 3 rows):")
        print(_df.head(3))
    return


@app.cell
def _(col, datasets):
    """Marimo cell executing missing data analysis and handling non-standard missing values."""
    # --- 3. MISSING DATA ANALYSIS ---
    print("\n--- Missing Data Analysis ---")
    for _name, _df in datasets.items():
        print(f"\n[{_name}] Missing values per column:")
        print(_df.isna().sum())

        # Hunting for non-standard missing values (empty strings, "nan", "null")
        # This works for object (string) columns
        print(f"\n[{_name}] Non-standard missing values (in string columns):")
        _obj_cols = _df.select_dtypes(include=['object', 'string']).columns
        for _col in _obj_cols:
            empty_str_count = (_df[_col] == "").sum()
            str_nan_count = (_df[_col].astype(str).str.lower() == "nan").sum()
            str_null_count = (_df[_col].astype(str).str.lower() == "null").sum()
            none_str_count = (_df[_col].astype(str).str.lower() == "none").sum()
            if any([empty_str_count, str_nan_count, str_null_count, none_str_count]):
                 print(f"  {col}: empty_str={empty_str_count}, 'nan'={str_nan_count}, 'null'={str_null_count}, 'none'={none_str_count}")

    return


@app.cell
def _(datasets):
    """Marimo cell to detect completely duplicated rows and duplicate title keys."""
    # --- 4. DUPLICATE DETECTION ---
    print("\n--- Duplicate Detection ---")
    for _name, _df in datasets.items():
        dup_rows = _df.duplicated().sum()
        print(f"\n[{_name}] Fully duplicated rows: {dup_rows}")
        if dup_rows > 0:
            print("Sample of duplicated rows:")
            print(_df[_df.duplicated(keep=False)].sort_values(by=_df.columns.tolist()[:2]).head())

    # Specific duplicate checks by Title (if exists)
    for _name, _df in datasets.items():
        # Attempt to find the Title column (case-sensitive or insensitive)
        title_col = None
        if 'Title' in _df.columns:
            title_col = 'Title'
        elif 'Title_gsheets' in _df.columns:
            title_col = 'Title_gsheets'

        if title_col:
            title_dupes = _df.duplicated(subset=[title_col]).sum()
            print(f"[{_name}] Duplicated titles in '{title_col}': {title_dupes}")
            if title_dupes > 0:
                print(f"Sample of duplicated titles in {_name}:")
                # print(df[df.duplicated(subset=[title_col], keep=False)].sort_values(by=title_col)[title_col].head(10))

    return


@app.cell
def _(datasets):
    """Marimo cell to check strings for problematic hidden whitespace or characters."""
    # --- 5. HIDDEN CHARACTER CHECKS ---
    print("\n--- Hidden Character Checks ---")
    # Check for leading/trailing whitespaces, newlines, tabs, non-breaking spaces
    for _name, _df in datasets.items():
        _obj_cols = _df.select_dtypes(include=['object', 'string']).columns
        found_hidden = False
        print(f"[{_name}] Checking string columns for hidden characters...")
        for _col in _obj_cols:
            # Check leading/trailing spaces
            leading_trailing = _df[_col].astype(str).str.contains(r'^\s+|\s+$', regex=True, na=False).sum()
            # Check internal newlines
            newlines = _df[_col].astype(str).str.contains(r'\n', regex=True, na=False).sum()
            # Check non-breaking spaces (\xa0)
            nbsp = _df[_col].astype(str).str.contains(r'\xa0', regex=True, na=False).sum()

            if any([leading_trailing, newlines, nbsp]):
                 print(f"  {_col}: Leading/Trailing Spaces={leading_trailing}, Newlines={newlines}, NBSP={nbsp}")
                 found_hidden = True
        if not found_hidden:
            print("  No obvious hidden characters detected.")

    return


@app.cell
def _(gsheets_csv, wiki_csv):
    """Marimo cell that compares overlap and discrepancies between GSheets and Wikipedia titles."""
    # --- 6. COMPARE & CONTRAST (GSheets vs Wiki) ---
    print("\n--- Comparison: GSheets vs Wiki Titles ---")
    # Assuming clean_data.py logic: clean titles first
    def normalize_title_series(s):
        """Normalizes titles to allow robust matching across data sources."""
        return s.astype("string").str.lower().str.replace(r'[^a-z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()

    # We need to extract the raw titles safely
    # Gsheets titles are in column 6 (index 5) or NOTES
    gsheets_raw = gsheets_csv.copy()
    # Keep first 7 cols to mimic clean_data
    if len(gsheets_raw.columns) >= 7:
        gsheets_raw = gsheets_raw.iloc[:, 0:7]
        gsheets_raw.columns = ['FROM', 'TO', 'DAY', 'DAYS', 'TYPE', 'Title', 'NOTES']
        gsheets_raw['Title'] = gsheets_raw['Title'].fillna(gsheets_raw['NOTES'])
        gsheets_raw = gsheets_raw[gsheets_raw['Title'].notna()]

        gsheets_titles = set(normalize_title_series(gsheets_raw['Title']).unique())
    else:
        gsheets_titles = set()

    if 'Title' in wiki_csv.columns:
        # Explode wiki titles just like in clean_data
        wiki_raw = wiki_csv.copy()
        wiki_raw['Title'] = wiki_raw['Title'].str.split('\n')
        wiki_raw = wiki_raw.explode('Title')
        wiki_titles = set(normalize_title_series(wiki_raw['Title']).unique())
    else:
        wiki_titles = set()

    if gsheets_titles and wiki_titles:
        in_gsheets_not_wiki = gsheets_titles - wiki_titles
        in_wiki_not_gsheets = wiki_titles - gsheets_titles
        both = gsheets_titles.intersection(wiki_titles)

        print(f"Titles ONLY in GSheets: {len(in_gsheets_not_wiki)}")
        print(f"Titles ONLY in Wiki: {len(in_wiki_not_gsheets)}")
        print(f"Titles in BOTH: {len(both)}")

        print("\nSample of titles ONLY in GSheets:")
        print(list(in_gsheets_not_wiki)[:10])

        print("\nSample of titles ONLY in Wiki:")
        print(list(in_wiki_not_gsheets)[:10])
    else:
        print("Could not compare titles (columns not found or parsing failed).")

    return


@app.cell
def _(datasets):
    """Marimo cell checking columns for data type consistency, particularly dates."""
    # --- 7. DATA TYPE CORRECTNESS ---
    print("\n--- Data Type Correctness Checks ---")
    # Look at date columns to see if they are parsed as datetime or strings
    for name, df in datasets.items():
        date_cols = [col for col in df.columns if any(x in col.lower() for x in ['date', 'from', 'to', 'time'])]
        if date_cols:
            print(f"[{name}] Date-like columns found: {date_cols}")
            for col in date_cols:
                print(f"  {col} dtype: {df[col].dtype}")
                # Try parsing a sample to see if it's a valid date
                sample = df[col].dropna().head(1)
                if not sample.empty:
                    print(f"  Sample value: {sample.iloc[0]}")

    print("\nSpotcheck script complete. In marimo, you would break these sections into individual cells and display DataFrames directly.")
    return (col,)


if __name__ == "__main__":
    app.run()
