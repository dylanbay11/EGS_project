"""Scrape and merge HowLongToBeat data for the Epic giveaway dataset."""

from __future__ import annotations

import argparse
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd
from howlongtobeatpy import HowLongToBeat
from howlongtobeatpy.HTMLRequests import SearchModifiers

INPUT_CANDIDATES = (Path("data/merge_mc.csv"), Path("data/cleaned_merged_data.csv"))
OUTPUT_FILE = Path("outputs/hltb_data.csv")
FINAL_OUTPUT_FILE = Path("data/merge_hltb.csv")
OUTPUT_COLUMNS = [
    "Original_Title",
    "HLTB_Found",
    "HLTB_Game_Name",
    "HLTB_Main_Story",
    "HLTB_Main_Extra",
    "HLTB_Completionist",
    "HLTB_All_Styles",
    "HLTB_Review_Score",
    "HLTB_Platforms",
    "HLTB_Release_World",
    "HLTB_Similarity",
    "HLTB_Match_Score",
    "HLTB_Query_Used",
]
SAFE_SUFFIXES = (
    "anniversary edition",
    "complete edition",
    "definitive edition",
    "deluxe edition",
    "director's cut",
    "directors cut",
    "enhanced edition",
    "game of the year edition",
    "gold edition",
    "goty edition",
    "masterpiece edition",
    "remastered",
    "special edition",
    "trials of fear edition",
    "ultimate edition",
)
SERIES_NUMBER_MAP = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}
STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to"}
MATCH_THRESHOLD = 0.84
SAVE_EVERY = 10


def parse_args() -> argparse.Namespace:
    """Parse the small CLI we use for refreshes and polite rate limiting."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore any cached scrape and rebuild outputs/hltb_data.csv from scratch",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="seconds to wait between title searches; default keeps the scrape polite",
    )
    return parser.parse_args()


def find_input_file() -> Path:
    """Return the preferred merged input dataset, falling back when needed."""

    for candidate in INPUT_CANDIDATES:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in INPUT_CANDIDATES)
    raise FileNotFoundError(f"Could not find any input dataset. Looked for: {searched}")


def collapse_spaces(text: str) -> str:
    """Trim a title and collapse internal whitespace down to single spaces."""

    return " ".join(text.split())


def normalize_title(text: str) -> str:
    """Normalize a title into a comparison-friendly lowercase ASCII string."""

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.casefold().replace("&", " and ")
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return collapse_spaces(ascii_text)


def strip_safe_suffixes(title: str) -> str:
    """Drop edition-style suffixes when they likely point to the same base game."""

    cleaned_title = collapse_spaces(title)
    changed = True
    while changed:
        changed = False
        for suffix in SAFE_SUFFIXES:
            pattern = re.compile(rf"(?i)(?:\s*[:\-]\s*|\s+){re.escape(suffix)}$")
            if pattern.search(cleaned_title):
                cleaned_title = pattern.sub("", cleaned_title).strip(" :-")
                cleaned_title = collapse_spaces(cleaned_title)
                changed = True
                break

    return cleaned_title


def extract_series_numbers(normalized_title: str) -> set[str]:
    """Extract simple sequel markers so we can avoid sequel mismatches."""

    numbers: set[str] = set()
    for token in normalized_title.split():
        if token.isdigit():
            numbers.add(token)
            continue

        mapped = SERIES_NUMBER_MAP.get(token)
        if mapped is not None:
            numbers.add(mapped)

    return numbers


def canonical_content_tokens(normalized_title: str) -> set[str]:
    """Return meaningful title tokens with simple number normalization applied."""

    tokens: set[str] = set()
    for token in normalized_title.split():
        mapped = SERIES_NUMBER_MAP.get(token, token)
        if mapped not in STOPWORDS:
            tokens.add(mapped)

    return tokens


def is_subsequence(query_tokens: list[str], candidate_tokens: list[str]) -> bool:
    """Return True when query tokens appear in the candidate in the same order."""

    if not query_tokens:
        return False

    query_index = 0
    for candidate_token in candidate_tokens:
        if candidate_token == query_tokens[query_index]:
            query_index += 1
            if query_index == len(query_tokens):
                return True

    return False


def has_sequel_mismatch(query_title: str, candidate_title: str) -> bool:
    """Reject candidates that only differ because they look like another numbered entry."""

    query_numbers = extract_series_numbers(query_title)
    candidate_numbers = extract_series_numbers(candidate_title)

    if not query_numbers and candidate_numbers:
        return True

    if query_numbers and candidate_numbers and query_numbers != candidate_numbers:
        return True

    if query_numbers and not candidate_numbers:
        return True

    return False


def score_candidate(
    original_title: str,
    candidate_title: str,
    package_similarity: float | None,
) -> float:
    """Score an HLTB candidate using title normalization and a few safety checks."""

    full_normalized = normalize_title(original_title)
    root_normalized = normalize_title(strip_safe_suffixes(original_title))
    candidate_normalized = normalize_title(candidate_title)
    title_prefix = normalize_title(original_title.split(":", maxsplit=1)[0])

    if not candidate_normalized:
        return 0.0

    if has_sequel_mismatch(root_normalized or full_normalized, candidate_normalized):
        return 0.0

    if candidate_normalized == full_normalized:
        return 1.0

    if root_normalized and candidate_normalized == root_normalized:
        return 0.99

    score = 0.0
    score = max(score, SequenceMatcher(None, full_normalized, candidate_normalized).ratio())
    if root_normalized and root_normalized != full_normalized:
        score = max(score, SequenceMatcher(None, root_normalized, candidate_normalized).ratio() + 0.02)

    if package_similarity is not None:
        score = max(score, min(float(package_similarity), 0.9))
        if title_prefix and title_prefix == candidate_normalized and float(package_similarity) >= 0.95:
            score = max(score, 0.96)

    root_tokens = root_normalized.split()
    candidate_tokens = candidate_normalized.split()
    root_token_set = set(root_tokens)
    candidate_token_set = set(candidate_tokens)

    if root_tokens and root_token_set.issubset(candidate_token_set):
        score = max(score, 0.9)
        if is_subsequence(root_tokens, candidate_tokens):
            score = max(score, 0.94)

    if root_normalized and candidate_normalized.startswith(root_normalized):
        score = max(score, 0.95)

    query_content = canonical_content_tokens(root_normalized or full_normalized)
    candidate_content = canonical_content_tokens(candidate_normalized)
    if query_content - candidate_content and candidate_content - query_content:
        score = min(score, 0.82)

    return min(score, 1.0)


def build_search_queries(title: str) -> list[str]:
    """Generate a short, ordered list of search queries for one title."""

    cleaned_title = collapse_spaces(title)
    stripped_title = strip_safe_suffixes(cleaned_title)

    queries: list[str] = []
    for query in (cleaned_title, stripped_title):
        if query and query not in queries:
            queries.append(query)

    return queries


def load_unique_titles(input_file: Path) -> list[str]:
    """Load the source dataset and return unique non-empty Google Sheets titles."""

    df = pd.read_csv(input_file)
    if "Title_gsheets" not in df.columns:
        raise KeyError("Expected a 'Title_gsheets' column in the input dataset.")

    return (
        pd.Series(df["Title_gsheets"])
        .dropna()
        .astype(str)
        .map(collapse_spaces)
        .drop_duplicates()
        .tolist()
    )


def blank_row(original_title: str) -> dict[str, Any]:
    """Create the default empty output row for one title."""

    return {
        "Original_Title": original_title,
        "HLTB_Found": False,
        "HLTB_Game_Name": None,
        "HLTB_Main_Story": None,
        "HLTB_Main_Extra": None,
        "HLTB_Completionist": None,
        "HLTB_All_Styles": None,
        "HLTB_Review_Score": None,
        "HLTB_Platforms": None,
        "HLTB_Release_World": None,
        "HLTB_Similarity": None,
        "HLTB_Match_Score": None,
        "HLTB_Query_Used": None,
    }


def load_existing_rows(output_file: Path, refresh: bool) -> tuple[list[dict[str, Any]], set[str]]:
    """Load cached rows so interrupted scrapes can resume cleanly."""

    if refresh or not output_file.exists():
        return [], set()

    existing_df = pd.read_csv(output_file)
    if existing_df.empty:
        return [], set()

    for column in OUTPUT_COLUMNS:
        if column not in existing_df.columns:
            existing_df[column] = None

    existing_df = (
        existing_df[OUTPUT_COLUMNS]
        .drop_duplicates(subset=["Original_Title"], keep="last")
        .sort_values("Original_Title", kind="stable")
        .reset_index(drop=True)
    )

    processed_titles = set(existing_df["Original_Title"].dropna().astype(str))
    return existing_df.to_dict("records"), processed_titles


def save_rows(rows: list[dict[str, Any]], output_file: Path) -> None:
    """Persist the incremental scrape output with a consistent column order."""

    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(output_file, index=False)


def search_with_retries(hltb: HowLongToBeat, query: str, retries: int = 3) -> list[Any]:
    """Search HLTB with light retry logic for transient web hiccups."""

    for attempt in range(1, retries + 1):
        try:
            results = hltb.search(
                query,
                search_modifiers=SearchModifiers.HIDE_DLC,
                similarity_case_sensitive=False,
            )
            return results or []
        except Exception as exc:  # noqa: BLE001 - this wrapper can raise a mix of request errors
            if attempt == retries:
                print(f"  -> Search failed for {query!r}: {exc}", flush=True)
                return []

            wait_seconds = attempt * 2
            print(
                f"  -> Search error for {query!r} on attempt {attempt}/{retries}: {exc}. "
                f"Retrying in {wait_seconds}s.",
                flush=True,
            )
            time.sleep(wait_seconds)

    return []


def pick_best_match(hltb: HowLongToBeat, title: str) -> tuple[Any | None, float | None, str | None]:
    """Choose the safest HLTB result for one title, or return no match."""

    best_match: Any | None = None
    best_score = 0.0
    best_query: str | None = None
    seen_candidates: set[tuple[str | None, int | None]] = set()

    for query in build_search_queries(title):
        for candidate in search_with_retries(hltb, query):
            candidate_key = (
                getattr(candidate, "game_name", None),
                getattr(candidate, "release_world", None),
            )
            if candidate_key in seen_candidates:
                continue

            seen_candidates.add(candidate_key)
            score = score_candidate(
                original_title=title,
                candidate_title=getattr(candidate, "game_name", ""),
                package_similarity=getattr(candidate, "similarity", None),
            )
            if score > best_score:
                best_match = candidate
                best_score = score
                best_query = query

    if best_match is None or best_score < MATCH_THRESHOLD:
        return None, None, None

    return best_match, round(best_score, 4), best_query


def match_to_row(original_title: str, match: Any | None, match_score: float | None, query_used: str | None) -> dict[str, Any]:
    """Turn one HLTB match object into the flattened row we store on disk."""

    row = blank_row(original_title)
    if match is None:
        return row

    row.update(
        {
            "HLTB_Found": True,
            "HLTB_Game_Name": getattr(match, "game_name", None),
            "HLTB_Main_Story": getattr(match, "main_story", None),
            "HLTB_Main_Extra": getattr(match, "main_extra", None),
            "HLTB_Completionist": getattr(match, "completionist", None),
            "HLTB_All_Styles": getattr(match, "all_styles", None),
            "HLTB_Review_Score": getattr(match, "review_score", None),
            "HLTB_Platforms": ", ".join(getattr(match, "profile_platforms", []) or []),
            "HLTB_Release_World": getattr(match, "release_world", None),
            "HLTB_Similarity": getattr(match, "similarity", None),
            "HLTB_Match_Score": match_score,
            "HLTB_Query_Used": query_used,
        }
    )
    return row


def merge_hltb_data(input_file: Path, output_file: Path, final_output_file: Path) -> None:
    """Join the HLTB scrape back onto the original merged dataset."""

    original_df = pd.read_csv(input_file)
    hltb_df = pd.read_csv(output_file)

    if hltb_df["Original_Title"].duplicated().any():
        duplicates = hltb_df.loc[hltb_df["Original_Title"].duplicated(), "Original_Title"].unique()
        duplicate_preview = ", ".join(sorted(map(str, duplicates[:10])))
        raise ValueError(f"HLTB output contains duplicate titles: {duplicate_preview}")

    merged_df = original_df.merge(
        hltb_df,
        left_on="Title_gsheets",
        right_on="Original_Title",
        how="left",
        validate="m:1",
    )
    merged_df.to_csv(final_output_file, index=False)


def scrape_hltb_data(refresh: bool = False, delay_seconds: float = 1.0) -> None:
    """Scrape HLTB for each unique game title, then regenerate the merged dataset."""

    input_file = find_input_file()
    print(f"Reading titles from {input_file}", flush=True)
    unique_titles = load_unique_titles(input_file)
    print(f"Found {len(unique_titles)} unique titles to consider.", flush=True)

    existing_rows, processed_titles = load_existing_rows(OUTPUT_FILE, refresh=refresh)
    print(f"Loaded {len(processed_titles)} cached titles from {OUTPUT_FILE}.", flush=True)

    titles_to_process = [title for title in unique_titles if title not in processed_titles]
    print(f"Processing {len(titles_to_process)} remaining titles.", flush=True)

    hltb = HowLongToBeat()

    for index, title in enumerate(titles_to_process, start=1):
        print(f"[{index}/{len(titles_to_process)}] Searching for: {title}", flush=True)
        match, match_score, query_used = pick_best_match(hltb, title)
        row = match_to_row(title, match, match_score, query_used)
        existing_rows.append(row)

        if row["HLTB_Found"]:
            print(
                f"  -> Matched {row['HLTB_Game_Name']} "
                f"(score={row['HLTB_Match_Score']}, query={row['HLTB_Query_Used']!r})",
                flush=True,
            )
        else:
            print("  -> No confident match found.", flush=True)

        if index % SAVE_EVERY == 0 or index == len(titles_to_process):
            save_rows(existing_rows, OUTPUT_FILE)
            print(f"Saved progress to {OUTPUT_FILE}", flush=True)

        if delay_seconds > 0 and index != len(titles_to_process):
            time.sleep(delay_seconds)

    if not titles_to_process and not OUTPUT_FILE.exists():
        save_rows(existing_rows, OUTPUT_FILE)

    merge_hltb_data(input_file, OUTPUT_FILE, FINAL_OUTPUT_FILE)
    print(f"Successfully regenerated {FINAL_OUTPUT_FILE}", flush=True)


def main() -> None:
    """Run the CLI entrypoint for the HLTB scrape workflow."""

    args = parse_args()
    scrape_hltb_data(refresh=args.refresh, delay_seconds=args.delay)


if __name__ == "__main__":
    main()
