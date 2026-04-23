with open("development/spotcheck.py", "r") as f:
    content = f.read()

search = """
    # Assuming clean_data.py logic: clean titles first
    def normalize_title(s):
        \"\"\"Normalizes titles to allow robust matching across data sources.\"\"\"
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

        gsheets_titles = set(gsheets_raw['Title'].apply(normalize_title).unique())
    else:
        gsheets_titles = set()

    if 'Title' in wiki_csv.columns:
        # Explode wiki titles just like in clean_data
        wiki_raw = wiki_csv.copy()
        wiki_raw['Title'] = wiki_raw['Title'].str.split('\\n')
        wiki_raw = wiki_raw.explode('Title')
        wiki_titles = set(wiki_raw['Title'].apply(normalize_title).unique())
    else:
        wiki_titles = set()
"""

replace = """
    # Assuming clean_data.py logic: clean titles first
    def normalize_title_series(s):
        \"\"\"Normalizes titles to allow robust matching across data sources.\"\"\"
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
        wiki_raw['Title'] = wiki_raw['Title'].str.split('\\n')
        wiki_raw = wiki_raw.explode('Title')
        wiki_titles = set(normalize_title_series(wiki_raw['Title']).unique())
    else:
        wiki_titles = set()
"""

if search in content:
    content = content.replace(search, replace)
    with open("development/spotcheck.py", "w") as f:
        f.write(content)
    print("Patched spotcheck series successfully")
else:
    print("Search string not found")
