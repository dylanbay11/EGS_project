with open("development/spotcheck.py", "r") as f:
    content = f.read()

search = """
    # Source 1: Google Sheets (skipping first 15 rows based on project memory, and row 16 which is totals in actual parsing)
    print("Loading GSheets data...")
    gsheets_csv = pd.read_csv(os.path.join(data_dir, '2026-04-21-gsheets.csv'), skiprows=15)
    # GSheets from Excel file as well to see background colours and formatting
    # (Requires openpyxl)
    # gsheets_xlsx = pd.read_excel(os.path.join(data_dir, '2026-04-21-gsheets.xlsx'), skiprows=15)

    # Source 2: Wikipedia data
    print("Loading Wiki data...")
    wiki_csv = pd.read_csv(os.path.join(data_dir, '2026-04-21-wiki.csv'))
    wiki_enriched_csv = pd.read_csv(os.path.join(data_dir, '2026-04-21-wiki-enriched.csv'))
"""

replace = """
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
"""

if search in content:
    content = content.replace(search, replace)
    with open("development/spotcheck.py", "w") as f:
        f.write(content)
    print("Patched spotcheck successfully")
else:
    print("Search string not found")
