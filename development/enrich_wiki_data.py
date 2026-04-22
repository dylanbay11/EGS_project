import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import time
import os

def enrich_data():
    """
    Enriches Wikipedia title data with additional attributes.

    Reads titles from a base CSV dataset, queries the English Wikipedia API for
    each title's dedicated page, and extracts metadata from infoboxes (developer,
    publisher, genre, etc.) along with the first few paragraphs of summary and
    background text. Saves the enriched dataset to a new CSV file.
    """
    input_file = 'data/2026-04-21-wiki.csv'
    output_file = 'data/2026-04-21-wiki-enriched.csv'

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    df = pd.read_csv(input_file)

    # Rename original columns
    df = df.rename(columns={
        'Date': 'daterange_wiki',
        'Title': 'title_wiki',
        'Year': 'year_wiki',
        'Source Links': 'source_wiki'
    })

    enriched_data = []

    # Handle potentially non-string titles (e.g. NaN)
    df['title_wiki'] = df['title_wiki'].astype(str)
    unique_titles = [t for t in df['title_wiki'].unique() if t and str(t).lower() != 'nan']
    print(f"Found {len(unique_titles)} unique titles. Starting enrichment...")

    for i, title in enumerate(unique_titles):
        print(f"Processing {i+1}/{len(unique_titles)}: {title}")

        search_title = str(title)
        search_title = re.sub(r'\[.*?\]', '', search_title).strip()

        if '\n' in search_title:
            search_title = search_title.split('\n')[0].strip()

        url = f'https://en.wikipedia.org/wiki/{urllib.parse.quote(search_title.replace(" ", "_"))}'

        row_data = {
            'title_wiki': title,
            'link_wiki': url,
            'developer_wiki': None,
            'publisher_wiki': None,
            'releasedate_wiki': None,
            'genre_wiki': None,
            'engine_wiki': None,
            'director_wiki': None,
            'artist_wiki': None,
            'composer_wiki': None,
            'platform_wiki': None,
            'designer_wiki': None,
            'writer_wiki': None,
            'programmer_wiki': None,
            'mode_wiki': None,
            'summary_wiki': None,
            'background_wiki': None
        }

        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 EGS_Project/1.0'})
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'html.parser')

                infobox = soup.find('table', class_='infobox')
                if infobox:
                    data = {}
                    for tr in infobox.find_all('tr'):
                        th = tr.find('th')
                        td = tr.find('td')
                        if th and td:
                            key = th.text.strip().lower()
                            val = re.sub(r'\[.*?\]', '', td.text.strip())
                            data[key] = val.replace('\n', ', ')

                    row_data['developer_wiki'] = data.get('developer(s)') or data.get('developer')
                    row_data['publisher_wiki'] = data.get('publisher(s)') or data.get('publisher')
                    row_data['releasedate_wiki'] = data.get('release')
                    row_data['genre_wiki'] = data.get('genre(s)') or data.get('genre')

                    row_data['engine_wiki'] = data.get('engine(s)') or data.get('engine')
                    row_data['director_wiki'] = data.get('director(s)') or data.get('director')
                    row_data['artist_wiki'] = data.get('artist(s)') or data.get('artist')
                    row_data['composer_wiki'] = data.get('composer(s)') or data.get('composer')
                    row_data['platform_wiki'] = data.get('platform(s)') or data.get('platform')
                    row_data['designer_wiki'] = data.get('designer(s)') or data.get('designer')
                    row_data['writer_wiki'] = data.get('writer(s)') or data.get('writer')
                    row_data['programmer_wiki'] = data.get('programmer(s)') or data.get('programmer')
                    row_data['mode_wiki'] = data.get('mode(s)') or data.get('mode')

                content = soup.find(id='bodyContent')
                if content:
                    # Find mw-parser-output
                    parser_output = content.find('div', class_='mw-parser-output')
                    if parser_output:
                        # Extract paragraphs that are direct children to avoid infobox/table paragraphs
                        ps = parser_output.find_all('p', recursive=False)
                        valid_ps = []
                        for p in ps:
                            text = p.text.strip()
                            if text:
                                text = re.sub(r'\[.*?\]', '', text)
                                valid_ps.append(text)

                        if len(valid_ps) > 0:
                            row_data['summary_wiki'] = valid_ps[0]
                        if len(valid_ps) > 1:
                            background = valid_ps[1]
                            if len(valid_ps) > 2:
                                background += "\n\n" + valid_ps[2]
                            row_data['background_wiki'] = background

            else:
                row_data['link_wiki'] = None # Only keep link if successful
        except Exception as e:
            print(f"Error fetching {title}: {e}")
            row_data['link_wiki'] = None

        enriched_data.append(row_data)
        time.sleep(1)

    enriched_df = pd.DataFrame(enriched_data)

    final_df = pd.merge(df, enriched_df, on='title_wiki', how='left')
    final_df.to_csv(output_file, index=False)
    print(f"Enriched data saved to {output_file}")

if __name__ == '__main__':
    enrich_data()
