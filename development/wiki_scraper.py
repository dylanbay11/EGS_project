import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os
import datetime

# Target CSV path
csv_path = 'data/2026-04-21-wiki.csv'

def check_should_scrape():
    # check if file exists and if it was modified in the last 24 hours
    if os.path.exists(csv_path):
        mtime = os.path.getmtime(csv_path)
        last_modified_date = datetime.datetime.fromtimestamp(mtime)
        now = datetime.datetime.now()
        diff = now - last_modified_date
        if diff.total_seconds() < 86400: # 1 day in seconds
            print(f"Skipping scrape: {csv_path} was generated less than 1 day ago ({last_modified_date}).")
            return False
    return True

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
                title = cells[1].text.strip()

                # Clean title
                title = re.sub(r'\[\d+\]', '', title)
                title = re.sub(r'\[[a-zA-Zа-яА-ЯёЁ.]+\]', '', title)
                title = title.strip()

                # Format date
                clean_date = translate_date(date_str, year)

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

                data.append({
                    "Date": clean_date,
                    "Title": title,
                    "Year": year,
                    "Source Links": link_str
                })

    df = pd.DataFrame(data)

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    df.to_csv(csv_path, index=False)
    print(f"Successfully scraped and saved {len(df)} records to {csv_path}")

if __name__ == "__main__":
    scrape_wiki()
