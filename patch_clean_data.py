import re

with open("development/clean_data.py", "r") as f:
    content = f.read()

search = """
def clean_gsheets():
    \"\"\"
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
    \"\"\"
    # Load the Google Sheets CSV file, skipping the initial header rows
    file_path = os.path.join(os.path.dirname(__file__), '../data/2026-04-21-gsheets.csv')
    df = pd.read_csv(file_path, skiprows=15)
"""

replace = """
import glob

def get_latest_file(data_dir, pattern_xlsx, pattern_csv=None):
    \"\"\"Helper to find the most recently created/named file matching a pattern.\"\"\"
    files = glob.glob(os.path.join(data_dir, pattern_xlsx))
    if pattern_csv:
        files.extend(glob.glob(os.path.join(data_dir, pattern_csv)))
    if not files:
        raise FileNotFoundError(f"No files found matching {pattern_xlsx} or {pattern_csv}")
    files.sort(reverse=True)
    return files[0]


def clean_gsheets():
    \"\"\"
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
    \"\"\"
    # Find the latest Google Sheets file dynamically
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    file_path = get_latest_file(data_dir, "20*-gsheets.xlsx", "20*-gsheets.csv")

    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path, engine='openpyxl', skiprows=15)
    else:
        df = pd.read_csv(file_path, skiprows=15)
"""

if search in content:
    content = content.replace(search, replace)
    print("Patched clean_gsheets successfully")
else:
    print("Search string 1 not found")

search2 = """
def clean_wiki():
    \"\"\"
    Loads and cleans the scraped Wikipedia dataset.

    Returns:
        pd.DataFrame: A DataFrame with exploded titles replacing bundle text.
    \"\"\"
    # Load the Wikipedia CSV file
    file_path = os.path.join(os.path.dirname(__file__), '../data/2026-04-21-wiki.csv')
    df = pd.read_csv(file_path)
"""

replace2 = """
def clean_wiki():
    \"\"\"
    Loads and cleans the scraped Wikipedia dataset.

    Returns:
        pd.DataFrame: A DataFrame with exploded titles replacing bundle text.
    \"\"\"
    # Load the Wikipedia CSV file dynamically
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    file_path = get_latest_file(data_dir, "20*-wiki.csv")
    df = pd.read_csv(file_path)
"""

if search2 in content:
    content = content.replace(search2, replace2)
    print("Patched clean_wiki successfully")
else:
    print("Search string 2 not found")

with open("development/clean_data.py", "w") as f:
    f.write(content)
