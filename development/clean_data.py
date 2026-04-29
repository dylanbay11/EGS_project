"""Clean the current source datasets and merge them into one analysis table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ENRICHED_WIKI_PATH = DATA_DIR / "wiki-enriched.csv"


def get_latest_file(
    data_dir: Path,
    primary_pattern: str,
    secondary_pattern: str | None = None,
) -> Path:
    """Return the newest dated file matching the supplied pattern or patterns."""
    files = list(data_dir.glob(primary_pattern))
    if secondary_pattern:
        files.extend(data_dir.glob(secondary_pattern))
    files = sorted(files)
    if not files:
        raise FileNotFoundError(
            f"No files found matching {primary_pattern!r} or {secondary_pattern!r}."
        )
    return files[-1]


def get_current_wiki_enriched_path() -> Path:
    """Return the current enriched wiki dataset path used by the merge step."""
    if ENRICHED_WIKI_PATH.exists():
        return ENRICHED_WIKI_PATH

    legacy_files = sorted(DATA_DIR.glob("*-wiki-enriched.csv"))
    if legacy_files:
        return legacy_files[-1]

    raise FileNotFoundError(
        f"Missing enriched wiki data at {ENRICHED_WIKI_PATH} and no legacy "
        "dated enriched wiki file was found. Run development/enrich_wiki_data.py first."
    )


def rewrite_collection_rows(
    df: pd.DataFrame,
    title_col: str,
    notes_col: str,
) -> pd.DataFrame:
    """Replace collection headers with the actual per-game titles from notes."""
    if title_col not in df.columns or notes_col not in df.columns:
        return df

    title_values = df[title_col].astype("string").str.strip()
    notes_values = df[notes_col].astype("string").str.strip()
    has_title = title_values.notna() & title_values.ne("")
    has_notes = notes_values.notna() & notes_values.ne("")

    collection_names = title_values.where(has_title).ffill()
    is_continuation = ~has_title & has_notes
    next_is_continuation = is_continuation.shift(-1).fillna(False)
    is_start = has_title & has_notes & next_is_continuation
    in_collection = is_start | is_continuation

    new_titles = title_values.copy()
    new_notes = notes_values.copy()

    new_titles.loc[in_collection] = notes_values.loc[in_collection]
    new_notes.loc[in_collection] = "Part of collection: " + collection_names.loc[in_collection]

    isolated_missing_title = ~in_collection & ~has_title & has_notes
    new_titles.loc[isolated_missing_title] = notes_values.loc[isolated_missing_title]

    df[title_col] = new_titles
    df[notes_col] = new_notes
    return df


def drop_wiki_bundle_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Drop stale wiki bundle headers when component game rows already exist."""
    required_cols = {"title_wiki", "daterange_wiki", "source_wiki"}
    if df.empty or not required_cols.issubset(df.columns):
        return df

    df = df.copy()
    df["title_wiki"] = df["title_wiki"].astype("string").str.strip()
    df["is_bundle_header"] = df["title_wiki"].str.contains(
        r"\b(?:collection|trilogy)\b",
        case=False,
        regex=True,
        na=False,
    )

    group_cols = ["daterange_wiki", "source_wiki"]
    group_sizes = df.groupby(group_cols, dropna=False)["title_wiki"].transform("size")
    header_counts = df.groupby(group_cols, dropna=False)["is_bundle_header"].transform("sum")
    keep_mask = ~(df["is_bundle_header"] & (group_sizes > 1) & (header_counts > 0))

    return df.loc[keep_mask].drop(columns="is_bundle_header").reset_index(drop=True)


def clean_gsheets() -> pd.DataFrame:
    """Load and clean the latest Google Sheets export."""
    file_path = get_latest_file(DATA_DIR, "20*-gsheets.xlsx", "20*-gsheets.csv")

    if file_path.suffix == ".xlsx":
        df = pd.read_excel(file_path, engine="openpyxl", skiprows=15)

        import openpyxl

        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet = workbook.active

        colors = []
        for row_idx in range(17, 17 + len(df)):
            cell = sheet.cell(row=row_idx, column=6)
            rgb = cell.fill.start_color.rgb if cell.fill and cell.fill.start_color else None
            colors.append(rgb if rgb and isinstance(rgb, str) else "unknown")
    else:
        df = pd.read_csv(file_path, skiprows=15)
        colors = ["unknown"] * len(df)

    df = df.iloc[:, 0:7].copy()
    df.columns = ["FROM", "TO", "DAY", "DAYS", "TYPE", "Title", "NOTES"]
    df["COLOR_CATEGORY"] = colors

    first_next_idx = df.index[df["TYPE"] == "next"].tolist()
    if first_next_idx:
        df = df.loc[first_next_idx[0] :].copy()

    if len(df) > 0 and df.iloc[-1]["FROM"] == "FROM":
        df = df.iloc[:-1].copy()

    df = rewrite_collection_rows(df, "Title", "NOTES")

    for column in ["FROM", "TO", "DAY", "DAYS"]:
        df[column] = df[column].ffill()

    df = df[df["Title"].notna()].copy()
    df["Title"] = df["Title"].astype("string").str.strip()
    df = df[~df["Title"].isin(["", "-", "nan"])]
    df = df[df["TYPE"] != "*"]

    return df.reset_index(drop=True)


def clean_wiki() -> pd.DataFrame:
    """Load the rolling enriched wiki dataset used by the merge step."""
    file_path = get_current_wiki_enriched_path()
    df = pd.read_csv(file_path)
    if "title_wiki" not in df.columns:
        raise ValueError(
            f"{file_path} does not contain 'title_wiki'. "
            "Rebuild the enriched wiki dataset."
        )

    df["title_wiki"] = df["title_wiki"].astype("string").str.strip()
    return drop_wiki_bundle_headers(df)


def normalize_title_series(series: pd.Series) -> pd.Series:
    """Normalize titles for more robust cross-source matching."""
    return (
        series.astype("string")
        .str.lower()
        .str.replace(r"[^a-z0-9\s]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def main() -> None:
    """Run the core clean-and-merge step for the project pipeline."""
    print("Cleaning Google Sheets data...")
    gsheets_df = clean_gsheets()

    print("Loading enriched Wikipedia data...")
    wiki_df = clean_wiki()

    gsheets_df["merge_title"] = normalize_title_series(gsheets_df["Title"])
    wiki_df["merge_title"] = normalize_title_series(wiki_df["title_wiki"])

    print("Merging datasets...")
    merged_df = pd.merge(
        gsheets_df,
        wiki_df,
        on="merge_title",
        how="left",
        suffixes=("_gsheets", "_wiki"),
    ).drop(columns="merge_title")

    print(f"Merge complete. Result shape: {merged_df.shape}")
    print(f"Games successfully matched with Wikipedia data: {merged_df['title_wiki'].notna().sum()}")

    output_path = DATA_DIR / "cleaned_merged_data.csv"
    merged_df.to_csv(output_path, index=False)
    print(f"Saved merged dataset to: {output_path}")


if __name__ == "__main__":
    main()
