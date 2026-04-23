import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os
import datetime
import glob

def get_today_csv_path():
    """Returns the path for today's Wikipedia scrape CSV."""
    today = datetime.date.today().isoformat()
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    return os.path.join(data_dir, f'{today}-wiki.csv')

def check_should_scrape():
    """
    Checks if a new scrape of Wikipedia data is required.

    Returns:
        bool: True if the scrape should proceed (today's file doesn't exist,
              or FORCE_SCRAPE is set), False otherwise.
    """
    csv_path = get_today_csv_path()
    if os.path.exists(csv_path) and not os.environ.get("FORCE_SCRAPE"):
        print(f"Skipping scrape: Today's scrape {csv_path} already exists.")
        return False
    return True

def cleanup_old_scrapes():
    """
    Keeps today's scrape and the most recent previous scrape, and deletes older ones.
    """
    files = glob.glob('data/*-wiki.csv')
    # Filter out enriched ones just in case
    files = [f for f in files if not f.endswith('-wiki-enriched.csv')]

    if not files:
        return

    files.sort(reverse=True)
    # Keep the first two files (today and yesterday/most recent)
    files_to_keep = files[:2]
    files_to_delete = files[2:]

    for f in files_to_delete:
        try:
            os.remove(f)
            print(f"Deleted old scrape: {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")

months = {
    'января': 'January', 'февраля': 'February', 'марта': 'March',
    'апреля': 'April', 'мая': 'May', 'июня': 'June',
    'июля': 'July', 'августа': 'August', 'сентября': 'September',
    'октября': 'October', 'ноября': 'November', 'декабря': 'December',
    'январь': 'January', 'февраль': 'February', 'март': 'March',
    'апрель': 'April', 'май': 'May', 'июнь': 'June',
    'июль': 'July', 'август': 'August', 'сентябрь': 'September',
    'октябрь': 'October', 'ноябрь': 'November', 'декабрь': 'December'
}

def translate_date(date_str, year):
    """
    Translates and normalizes Russian month names and formats into English date strings.

    Args:
        date_str (str): The raw date string scraped from Russian Wikipedia.
        year (int): The inferred release year to append if missing.

    Returns:
        str: A cleaned and translated date string in English.
    """
    # e.g., "14—27 декабря" or "14—27 декабря 2018"
    # replace ndash or emdash with hyphen
    date_str = date_str.replace('—', '-').replace('–', '-')
    for ru, en in months.items():
        date_str = date_str.replace(ru, en)

    # Check if year is already in string
    if not any(str(y) in date_str for y in range(2018, 2030)):
        date_str = f"{date_str} {year}"

    return date_str

def scrape_wiki():
    """
    Scrapes the list of Epic Games Store free giveaways from the Russian Wikipedia page.

    Fetches the HTML content, parses data tables to extract dates, game titles,
    and source links, resolving footnote references. Saves the extracted data
    as a CSV to the data directory.
    """
    if not check_should_scrape():
        return

    print("Starting scrape...")
    url = "https://ru.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA_%D0%B8%D0%B3%D1%80,_%D1%80%D0%BE%D0%B7%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85_%D0%B2_Epic_Games_Store"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Respecting rate limit (though it's just one page, we'll add a tiny delay to be safe)
    time.sleep(1)

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    tables = soup.find_all('table', class_='wikitable')
    print(f"Found {len(tables)} tables.")

    data = []

    for table in tables:
        # Determine year
        year = None
        prev = table.find_previous(['h2', 'h3'])
        if prev:
            year_match = re.search(r'(20\d{2})', prev.text)
            if year_match:
                year = int(year_match.group(1))

        if not year:
             print("Warning: Could not determine year for a table. Using 2018 as fallback.")
             year = 2018

        rows = table.find_all('tr')
        for row in rows[1:]: # skip header
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 3:
                date_str = cells[0].text.strip()

                # Format date
                clean_date = translate_date(date_str, year)

                # Setup title cell for better text extraction
                title_cell = cells[1]

                # Extract game wiki link (use first link as default for bundle)
                game_wiki_link = ""
                a_tag = title_cell.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith('//'):
                        game_wiki_link = 'https:' + href
                    elif href.startswith('/'):
                        game_wiki_link = 'https://ru.wikipedia.org' + href
                    else:
                        game_wiki_link = href

                # Extract links
                links = []
                for a in cells[2].find_all('a', href=True):
                    href = a['href']
                    if href.startswith('#cite_note'):
                        cite_id = href[1:]
                        cite_element = soup.find(id=cite_id)
                        if cite_element:
                            external_link = cite_element.find('a', class_='external text', href=True)
                            if external_link:
                                links.append(external_link['href'])
                    else:
                        links.append(href)
                link_str = ", ".join(links)

                # Check for definition lists which are used for bundles
                has_dl = title_cell.find('dl')
                if has_dl:
                    dt = has_dl.find('dt')
                    if dt:
                        dt.decompose() # Remove the overarching collection name

                # Remove sup elements
                for sup in title_cell.find_all('sup'):
                    sup.decompose()

                # Insert newlines before block elements to ensure proper splitting
                for elem in title_cell.find_all(['dd', 'dt', 'li', 'br']):
                    elem.insert_before('\n')

                raw_title_text = title_cell.get_text(separator=' ').strip()

                # Collapse whitespace
                raw_title_clean = re.sub(r'[ \t]+', ' ', raw_title_text)
                raw_title_clean = re.sub(r' ?\n ?', '\n', raw_title_clean)
                raw_title_clean = re.sub(r'\n+', '\n', raw_title_clean)

                # Split bundle into multiple rows
                split_titles = [t.strip() for t in raw_title_clean.split('\n') if t.strip()]

                for title in split_titles:
                    # Clean title
                    title = re.sub(r'^data-sort-value=.*?\|\s*', '', title)
                    title = title.replace('«', '').replace('»', '')
                    title = title.replace('’', "'").replace('‘', "'")
                    title = title.replace('—', '-').replace('–', '-')
                    title = title.replace('\xa0', ' ')

                    if title != '[REDACTED]':
                        title = re.sub(r'\[[а-яА-Яa-zA-Z.]+\]', '', title)

                    title = title.strip()

                    if title == 'Чёрная книга':
                        title = 'Black Book'

                    if title:
                        data.append({
                            "Date": clean_date,
                            "Title": title,
                            "Year": year,
                            "Game Wiki Link": game_wiki_link,
                            "Source Links": link_str
                        })

    df = pd.DataFrame(data)

    # Cast to PyArrow strings for Pandas 3.0 string backend compliance
    df = df.astype({
        "Date": "string",
        "Title": "string",
        "Game Wiki Link": "string",
        "Source Links": "string"
    })

    # Validation
    if len(df) < 100:
        print(f"Validation failed: Scrape only returned {len(df)} rows (expected >= 100). Discarding data.")
        return

    na_count = df['Title'].isna().sum()
    if na_count > len(df) * 0.1: # Allow up to 10% NAs
        print(f"Validation failed: Too many NAs in Title column ({na_count}). Discarding data.")
        return

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    csv_path = get_today_csv_path()
    df.to_csv(csv_path, index=False)
    print(f"Successfully scraped and saved {len(df)} records to {csv_path}")

    cleanup_old_scrapes()

if __name__ == "__main__":
    scrape_wiki()
