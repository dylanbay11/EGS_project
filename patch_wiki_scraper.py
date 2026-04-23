import re

with open("development/wiki_scraper.py", "r") as f:
    content = f.read()

search = """
# Target CSV path
csv_path = 'data/2026-04-21-wiki.csv'

def check_should_scrape():
"""

replace = """
# Target CSV path
today = datetime.date.today().isoformat()
data_dir = os.path.join(os.path.dirname(__file__), '../data')
csv_path = os.path.join(data_dir, f'{today}-wiki.csv')

def check_should_scrape():
"""

if search in content:
    content = content.replace(search, replace)
    with open("development/wiki_scraper.py", "w") as f:
        f.write(content)
    print("Patched wiki_scraper successfully")
else:
    print("Search string not found")
