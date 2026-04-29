"""Enrich the latest raw Wikipedia scrape with English Wikipedia metadata."""

from __future__ import annotations

from pathlib import Path
import re
import time
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_WIKI_GLOB = "*-wiki.csv"
DATED_ENRICHED_GLOB = "*-wiki-enriched.csv"
ENRICHED_WIKI_PATH = DATA_DIR / "wiki-enriched.csv"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 EGS_Project/1.0"
    )
}


def get_latest_raw_wiki_file() -> Path | None:
    """Return the newest dated raw wiki scrape, if one exists."""
    files = sorted(
        file_path
        for file_path in DATA_DIR.glob(RAW_WIKI_GLOB)
        if not file_path.name.endswith("-wiki-enriched.csv")
    )
    if not files:
        return None
    return files[-1]


def clean_infobox_value(value: str) -> str:
    """Collapse infobox cell text into a cleaner single-line string."""
    cleaned_value = re.sub(r"\[.*?\]", "", value).strip()
    cleaned_value = cleaned_value.replace("\n", ", ")
    cleaned_value = re.sub(r"\s+", " ", cleaned_value)
    return cleaned_value.strip()


def fetch_wikipedia_details(title: str) -> dict[str, str | None]:
    """Fetch English Wikipedia metadata for one game title."""
    search_title = re.sub(r"\[.*?\]", "", str(title)).strip()
    if "\n" in search_title:
        search_title = search_title.split("\n", maxsplit=1)[0].strip()

    url = (
        "https://en.wikipedia.org/wiki/"
        + urllib.parse.quote(search_title.replace(" ", "_"))
    )
    row_data: dict[str, str | None] = {
        "title_wiki": title,
        "link_wiki": url,
        "developer_wiki": None,
        "publisher_wiki": None,
        "releasedate_wiki": None,
        "genre_wiki": None,
        "engine_wiki": None,
        "director_wiki": None,
        "artist_wiki": None,
        "composer_wiki": None,
        "platform_wiki": None,
        "designer_wiki": None,
        "writer_wiki": None,
        "programmer_wiki": None,
        "mode_wiki": None,
        "summary_wiki": None,
        "background_wiki": None,
    }

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    if response.status_code != 200:
        row_data["link_wiki"] = None
        return row_data

    soup = BeautifulSoup(response.content, "html.parser")
    infobox = soup.find("table", class_="infobox")
    if infobox:
        data: dict[str, str] = {}
        for row in infobox.find_all("tr"):
            header = row.find("th")
            cell = row.find("td")
            if not header or not cell:
                continue
            key = header.get_text(" ", strip=True).lower()
            data[key] = clean_infobox_value(cell.get_text("\n", strip=True))

        row_data["developer_wiki"] = data.get("developer(s)") or data.get("developer")
        row_data["publisher_wiki"] = data.get("publisher(s)") or data.get("publisher")
        row_data["releasedate_wiki"] = data.get("release")
        row_data["genre_wiki"] = data.get("genre(s)") or data.get("genre")
        row_data["engine_wiki"] = data.get("engine(s)") or data.get("engine")
        row_data["director_wiki"] = data.get("director(s)") or data.get("director")
        row_data["artist_wiki"] = data.get("artist(s)") or data.get("artist")
        row_data["composer_wiki"] = data.get("composer(s)") or data.get("composer")
        row_data["platform_wiki"] = data.get("platform(s)") or data.get("platform")
        row_data["designer_wiki"] = data.get("designer(s)") or data.get("designer")
        row_data["writer_wiki"] = data.get("writer(s)") or data.get("writer")
        row_data["programmer_wiki"] = data.get("programmer(s)") or data.get("programmer")
        row_data["mode_wiki"] = data.get("mode(s)") or data.get("mode")

    content = soup.find(id="bodyContent")
    if not content:
        return row_data

    parser_output = content.find("div", class_="mw-parser-output")
    if not parser_output:
        return row_data

    paragraphs = []
    for paragraph in parser_output.find_all("p", recursive=False):
        text = paragraph.get_text(" ", strip=True)
        if not text:
            continue
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            paragraphs.append(text)

    if paragraphs:
        row_data["summary_wiki"] = paragraphs[0]
    if len(paragraphs) > 1:
        row_data["background_wiki"] = "\n\n".join(paragraphs[1:3])

    return row_data


def cleanup_old_enriched_outputs() -> None:
    """Remove legacy dated enriched wiki files now that this is an intermediate."""
    for file_path in DATA_DIR.glob(DATED_ENRICHED_GLOB):
        try:
            file_path.unlink()
            print(f"Deleted old enriched file: {file_path}")
        except OSError as exc:
            print(f"Failed to delete old enriched file {file_path}: {exc}")


def enrich_data() -> None:
    """Build the single rolling enriched wiki dataset from the latest raw scrape."""
    input_file = get_latest_raw_wiki_file()
    if not input_file or not input_file.exists():
        print("Error: No recent wiki input file found.")
        return

    df = pd.read_csv(input_file).rename(
        columns={
            "Date": "daterange_wiki",
            "Title": "title_wiki",
            "Year": "year_wiki",
            "Source Links": "source_wiki",
            "Game Wiki Link": "ru_link_wiki",
        }
    )

    df["title_wiki"] = df["title_wiki"].astype("string").str.strip()
    unique_titles = [title for title in df["title_wiki"].dropna().unique().tolist() if title]
    print(f"Found {len(unique_titles)} unique titles in {input_file.name}. Starting enrichment...")

    enriched_rows: list[dict[str, str | None]] = []
    for index, title in enumerate(unique_titles, start=1):
        print(f"Processing {index}/{len(unique_titles)}: {title}")
        try:
            enriched_rows.append(fetch_wikipedia_details(title))
        except Exception as exc:
            print(f"Error fetching {title}: {exc}")
            enriched_rows.append(
                {
                    "title_wiki": title,
                    "link_wiki": None,
                    "developer_wiki": None,
                    "publisher_wiki": None,
                    "releasedate_wiki": None,
                    "genre_wiki": None,
                    "engine_wiki": None,
                    "director_wiki": None,
                    "artist_wiki": None,
                    "composer_wiki": None,
                    "platform_wiki": None,
                    "designer_wiki": None,
                    "writer_wiki": None,
                    "programmer_wiki": None,
                    "mode_wiki": None,
                    "summary_wiki": None,
                    "background_wiki": None,
                }
            )
        time.sleep(1)

    enriched_df = pd.DataFrame(enriched_rows)
    final_df = pd.merge(df, enriched_df, on="title_wiki", how="left")

    DATA_DIR.mkdir(exist_ok=True)
    final_df.to_csv(ENRICHED_WIKI_PATH, index=False)
    print(f"Enriched data saved to {ENRICHED_WIKI_PATH}")

    cleanup_old_enriched_outputs()


if __name__ == "__main__":
    enrich_data()
