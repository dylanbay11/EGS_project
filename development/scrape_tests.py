import requests
from bs4 import BeautifulSoup
import csv
from io import StringIO
import sys

def scrape_wikipedia():
    print("--- Wikipedia (ru) ---")
    url = "https://ru.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA_%D0%B8%D0%B3%D1%80,_%D1%80%D0%BE%D0%B7%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85_%D0%B2_Epic_Games_Store"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table', class_='wikitable')
        print(f"Found {len(tables)} tables")

        entries = []
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]: # skip header
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    date = cells[0].text.strip()
                    title = cells[1].text.strip()
                    # Clean up footnote references like [1]
                    import re
                    title = re.sub(r'\[\d+\]', '', title)
                    if title:
                         entries.append({"date": date, "title": title})
                if len(entries) >= 3:
                     break
            if len(entries) >= 3:
                 break
        for e in entries:
             print(f"Date: {e['date']}, Title: {e['title']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def scrape_gamerant():
    print("\n--- GameRant ---")
    url = "https://gamerant.com/epic-games-store-free-games-list/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        if not table:
             print("No table found")
             return False

        rows = table.find_all('tr')
        entries = []
        current_year = None
        for row in rows:
            cells = row.find_all(['th', 'td'])
            cell_texts = [c.text.strip() for c in cells]

            if len(cell_texts) == 1 and cell_texts[0].isdigit():
                 current_year = cell_texts[0]
            elif len(cell_texts) >= 2 and current_year and cell_texts[0] != 'Game':
                 title = cell_texts[0]
                 date = f"{cell_texts[1]} {current_year}"
                 entries.append({"date": date, "title": title})

            if len(entries) >= 3:
                 break

        for e in entries:
             print(f"Date: {e['date']}, Title: {e['title']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def scrape_pcgamer():
    print("\n--- PC Gamer ---")
    url = "https://www.pcgamer.com/epic-games-store-free-games-list/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        lists = soup.find_all('ul')

        entries = []
        for ul in lists:
            text = ul.text
            if "Epic free games list" in text or "Jan 1" in text or "Dec 31" in text:
                 items = ul.find_all('li')
                 for item in items:
                     # format is usually Date: Title
                     parts = item.text.strip().split(':', 1)
                     if len(parts) == 2:
                          entries.append({"date": parts[0].strip(), "title": parts[1].strip()})
                     if len(entries) >= 3:
                          break
            if len(entries) >= 3:
                 break

        for e in entries:
             print(f"Date: {e['date']}, Title: {e['title']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def scrape_google_sheets():
    print("\n--- Google Sheets (CSV Export) ---")
    url = "https://docs.google.com/spreadsheets/d/1fpp0u5VHig4KG47Fu0I2EaB7vNCuU4xYBFWRlUKydjk/export?format=csv&gid=216261844"
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)

        # Skip header rows
        for _ in range(3):
            next(reader)

        entries = []
        for row in reader:
            if len(row) >= 25:
                 title = row[0]
                 start_date = row[23]
                 end_date = row[24]
                 date = f"{start_date} - {end_date}"
                 entries.append({"date": date, "title": title})
            if len(entries) >= 3:
                 break

        for e in entries:
             print(f"Date: {e['date']}, Title: {e['title']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    w = scrape_wikipedia()
    g = scrape_gamerant()
    p = scrape_pcgamer()
    s = scrape_google_sheets()

    if w and g and p and s:
        print("\nAll sources scraped successfully!")
        sys.exit(0)
    else:
        print("\nSome sources failed.")
        sys.exit(1)
