"""Scrape the Russian Wikipedia giveaway list into a rolling raw dataset."""

from __future__ import annotations

from pathlib import Path
import datetime
import os
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRAPE_URL = (
    "https://ru.wikipedia.org/wiki/"
    "%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA_%D0%B8%D0%B3%D1%80,"
    "_%D1%80%D0%BE%D0%B7%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85_"
    "%D0%B2_Epic_Games_Store"
)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

MONTHS = {
    "января": "January",
    "февраля": "February",
    "марта": "March",
    "апреля": "April",
    "мая": "May",
    "июня": "June",
    "июля": "July",
    "августа": "August",
    "сентября": "September",
    "октября": "October",
    "ноября": "November",
    "декабря": "December",
    "январь": "January",
    "февраль": "February",
    "март": "March",
    "апрель": "April",
    "май": "May",
    "июнь": "June",
    "июль": "July",
    "август": "August",
    "сентябрь": "September",
    "октябрь": "October",
    "ноябрь": "November",
    "декабрь": "December",
}


def get_today_csv_path() -> Path:
    """Return the output path for today's raw wiki scrape."""
    return DATA_DIR / f"{datetime.date.today().isoformat()}-wiki.csv"


def check_should_scrape() -> bool:
    """Return whether a new raw scrape should be created today."""
    csv_path = get_today_csv_path()
    if csv_path.exists() and not os.environ.get("FORCE_SCRAPE"):
        print(f"Skipping scrape: today's scrape {csv_path} already exists.")
        return False
    return True


def cleanup_old_scrapes() -> None:
    """Keep today's scrape plus one earlier raw wiki scrape and delete older ones."""
    files = sorted(
        file_path
        for file_path in DATA_DIR.glob("*-wiki.csv")
        if not file_path.name.endswith("-wiki-enriched.csv")
    )
    if not files:
        return

    for file_path in files[:-2]:
        try:
            file_path.unlink()
            print(f"Deleted old scrape: {file_path}")
        except OSError as exc:
            print(f"Failed to delete {file_path}: {exc}")


def translate_date(date_str: str, year: int) -> str:
    """Translate Russian month names into the English date strings used downstream."""
    translated = date_str.replace("—", "-").replace("–", "-")
    for russian_name, english_name in MONTHS.items():
        translated = translated.replace(russian_name, english_name)

    if not any(str(possible_year) in translated for possible_year in range(2018, 2030)):
        translated = f"{translated} {year}"

    return translated


def drop_bundle_header_title(titles: list[str]) -> list[str]:
    """Drop a leading bundle header when the component games are listed below it."""
    if len(titles) < 2:
        return titles

    first_title = titles[0]
    if re.search(r"\b(?:collection|trilogy)\b", first_title, flags=re.IGNORECASE):
        return titles[1:]
    return titles


def clean_title(raw_title: str) -> str:
    """Normalize the scraped wiki title text for downstream matching."""
    title = re.sub(r"^data-sort-value=.*?\|\s*", "", raw_title)
    title = title.replace("«", "").replace("»", "")
    title = title.replace("’", "'").replace("‘", "'")
    title = title.replace("—", "-").replace("–", "-")
    title = title.replace("\xa0", " ")

    if title != "[REDACTED]":
        title = re.sub(r"\[[а-яА-Яa-zA-Z.]+\]", "", title)

    title = title.strip()
    if title == "Чёрная книга":
        return "Black Book"
    return title


def scrape_wiki() -> None:
    """Scrape the Russian Wikipedia EGS giveaway page into today's raw wiki CSV."""
    if not check_should_scrape():
        return

    print("Starting scrape...")
    time.sleep(1)

    response = requests.get(SCRAPE_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    tables = soup.find_all("table", class_="wikitable")
    print(f"Found {len(tables)} tables.")

    data: list[dict[str, str | int]] = []
    for table in tables:
        year = None
        previous_header = table.find_previous(["h2", "h3"])
        if previous_header:
            year_match = re.search(r"(20\d{2})", previous_header.get_text(" ", strip=True))
            if year_match:
                year = int(year_match.group(1))

        if not year:
            print("Warning: Could not determine year for a table. Using 2018 as fallback.")
            year = 2018

        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) < 3:
                continue

            clean_date = translate_date(cells[0].get_text(" ", strip=True), year)
            title_cell = cells[1]

            game_wiki_link = ""
            title_link = title_cell.find("a", href=True)
            if title_link:
                href = title_link["href"]
                if href.startswith("//"):
                    game_wiki_link = "https:" + href
                elif href.startswith("/"):
                    game_wiki_link = "https://ru.wikipedia.org" + href
                else:
                    game_wiki_link = href

            links = []
            for link_tag in cells[2].find_all("a", href=True):
                href = link_tag["href"]
                if href.startswith("#cite_note"):
                    cite_id = href[1:]
                    cite_element = soup.find(id=cite_id)
                    if cite_element:
                        external_link = cite_element.find(
                            "a",
                            class_="external text",
                            href=True,
                        )
                        if external_link:
                            links.append(external_link["href"])
                else:
                    links.append(href)
            link_str = ", ".join(links)

            definition_list = title_cell.find("dl")
            if definition_list:
                bundle_title = definition_list.find("dt")
                if bundle_title:
                    bundle_title.decompose()

            for sup in title_cell.find_all("sup"):
                sup.decompose()

            for block_element in title_cell.find_all(["dd", "dt", "li", "br"]):
                block_element.insert_before("\n")

            raw_title_text = title_cell.get_text(separator=" ").strip()
            raw_title_text = re.sub(r"[ \t]+", " ", raw_title_text)
            raw_title_text = re.sub(r" ?\n ?", "\n", raw_title_text)
            raw_title_text = re.sub(r"\n+", "\n", raw_title_text)

            split_titles = [title.strip() for title in raw_title_text.split("\n") if title.strip()]
            split_titles = drop_bundle_header_title(split_titles)

            for raw_title in split_titles:
                title = clean_title(raw_title)
                if not title:
                    continue

                data.append(
                    {
                        "Date": clean_date,
                        "Title": title,
                        "Year": year,
                        "Game Wiki Link": game_wiki_link,
                        "Source Links": link_str,
                    }
                )

    df = pd.DataFrame(data)
    df = df.astype(
        {
            "Date": "string",
            "Title": "string",
            "Game Wiki Link": "string",
            "Source Links": "string",
        }
    )

    if len(df) < 100:
        print(
            f"Validation failed: Scrape only returned {len(df)} rows "
            "(expected at least 100). Discarding data."
        )
        return

    na_count = df["Title"].isna().sum()
    if na_count > len(df) * 0.1:
        print(
            f"Validation failed: Too many NAs in Title column "
            f"({na_count} of {len(df)}). Discarding data."
        )
        return

    DATA_DIR.mkdir(exist_ok=True)
    csv_path = get_today_csv_path()
    df.to_csv(csv_path, index=False)
    print(f"Successfully scraped and saved {len(df)} records to {csv_path}")

    cleanup_old_scrapes()


if __name__ == "__main__":
    scrape_wiki()
