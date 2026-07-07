"""Build the slim data extract that ships with the public portfolio explorer.

The portfolio explorer (development/portfolio_explorer.py) is designed to be
exported as a client-side WASM app (`marimo export html-wasm`), where every
byte of data is downloaded by the visitor's browser. So instead of the full
canonical parquet (50+ enrichment columns, long descriptions), we cut an
event-level CSV with only the columns the app actually renders.

Why CSV and not parquet: reading parquet in Pyodide needs pyarrow, which is a
heavyweight/flaky dependency in the browser; pandas.read_csv is bulletproof
there, and at ~914 rows the size difference is irrelevant.

Output: development/public/egs_app_data.csv
        (the `public/` folder next to the notebook is what marimo copies into
        a WASM export, and what `mo.notebook_location()` resolves against)

Run:    uv run python development/build_app_data.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "data" / "egs_giveaways.parquet"
OUT_DIR = PROJECT_ROOT / "development" / "public"
OUT_PATH = OUT_DIR / "egs_app_data.csv"

# everything the app shows or filters on, nothing else
APP_COLUMNS = [
    "title",
    "from_date",
    "giveaway_year",
    "is_repeat",
    "is_standalone_game",
    "egs_meets_threshold",
    "egs_original_price_usd",
    "egs_publisher",
    "egs_tags",
    "mc_criticScore",
    "hltb_main_story",
]

# booleans with NA don't round-trip through CSV cleanly (they come back as
# object dtype); the app treats NA as False anyway, so bake that in here
BOOL_COLUMNS = ["is_repeat", "is_standalone_game", "egs_meets_threshold"]


def build_app_extract() -> pd.DataFrame:
    """Cut the app-facing extract from the canonical event-level dataset.

    Returns the slimmed DataFrame (event grain, one row per giveaway
    occurrence) and writes it to OUT_PATH as CSV. The game-level grain is
    cheap to recompute in the app itself, so only events ship.
    """
    events = pd.read_parquet(SOURCE, columns=APP_COLUMNS)

    # dates as plain YYYY-MM-DD; the timestamps carry no time-of-day info
    events["from_date"] = events["from_date"].dt.date
    for col in BOOL_COLUMNS:
        events[col] = events[col].fillna(False).astype(bool)

    # the Metacritic scraper stores "no critic score yet" as 0, which is not a
    # real rating (72 titles as of the 2026-04 snapshot) — presenting those as
    # zeros would poison the app's median and scatter, so they become NA here.
    # The canonical dataset is left as-is pending triage (see REVIEW_NEEDED.md).
    events.loc[events["mc_criticScore"] == 0, "mc_criticScore"] = pd.NA

    OUT_DIR.mkdir(exist_ok=True)
    events.to_csv(OUT_PATH, index=False)
    return events


if __name__ == "__main__":
    df = build_app_extract()
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"wrote {OUT_PATH.relative_to(PROJECT_ROOT)}: "
          f"{len(df)} rows x {len(df.columns)} cols, {size_kb:.0f} KB")
