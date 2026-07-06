"""Build the single canonical Epic giveaway dataset from all enrichment sources.

This is the authoritative join step. The previous pipeline had each enricher
(Metacritic, HLTB) write its own merged file with its own schema, which drifted
out of sync. Instead, the scrapers now only maintain their per-title caches and
this script owns the one canonical merge.

Grain: the base is *event-level* - one row per giveaway occurrence, preserving
repeats (Bloons TD 6 was given away 12 times) and the giveaway TYPE. The
enrichments are *game-level* (one record per unique title) and fan out onto the
events by a normalized title key.

Inputs:
- data/cleaned_merged_data.csv        gsheets + wiki, event-level base
- outputs/metacritic_cache.json       title -> metacritic fields
- outputs/hltb_data.csv               Original_Title + HLTB_* fields
- data/egs-enriched.csv               title + egs_* fields (from egs_api_enrich.py)

Outputs:
- data/egs_giveaways.parquet (+ .csv mirror)          event-level canonical table
- data/egs_giveaways_by_game.parquet (+ .csv mirror)  game-level derived table

Run:
    uv run python development/build_dataset.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

BASE_FILE = DATA_DIR / "cleaned_merged_data.csv"
MC_CACHE_FILE = OUTPUT_DIR / "metacritic_cache.json"
HLTB_FILE = OUTPUT_DIR / "hltb_data.csv"
EGS_FILE = DATA_DIR / "egs-enriched.csv"

EVENT_OUT = DATA_DIR / "egs_giveaways"
GAME_OUT = DATA_DIR / "egs_giveaways_by_game"

# rename the gsheets-origin core columns to clean snake_case
CORE_RENAME = {
    "FROM": "from_date",
    "TO": "to_date",
    "DAY": "day_of_week",
    "DAYS": "duration_days",
    "TYPE": "giveaway_type",
    "Title": "title",
    "NOTES": "notes",
    "COLOR_CATEGORY": "color_category",
}

# the sources spell a few repeat giveaways with different casing, which splits one
# game into two "unique" titles; fold them onto the official spelling
CANONICAL_TITLES = {
    "Ark: Survival Evolved": "ARK: Survival Evolved",
    "Remnant: From The Ashes": "Remnant: From the Ashes",
    "SIFU": "Sifu",
}

# --- standalone-game classification (REVIEW_NEEDED item C) ---
# Words that mark a giveaway as add-on/in-game content rather than a playable game.
ADDON_TITLE_PATTERN = re.compile(
    r"(?i)\b(?:dlc|packs?|bundle|unlock|starter|welcome|cosmetic|costume|skins?|wheels"
    r"|decal|outfits?|gift|kits?|set|stuff|package|offer|giveaway|promo|bonus)\b"
)

# add-on content whose title dodges the pattern (expansions, DLC missions, unlocks)
ADDON_TITLES = {
    "Alien: Isolation - Last Survivor",
    "Borderlands 2 - Commander Lilith & the Fight for Sanctuary",
    "Crime Boss: Rockay City - Cagnali's Order",
    "Crime Boss: Rockay City - Dragon's Gold Cup",
    "Dark and Darker - Legendary Status",
    "Destiny 2: Beyond Light",
    "Destiny 2: Shadowkeep",
    "Destiny 2: The Witch Queen",
    "Dragon Age: The Veilguard - Rook’s Weapons Appearance",
    "The Cycle: Frontier - Fortuna Survivor",
    "Tom Clancy’s Ghost Recon Wildlands - Fallen Ghosts",
    "Train Sim World 2 - LGV Méditerranée: Marseille - Avignon",
    "Train Sim World® 5: Sherman Hill: Cheyenne - Laramie",
    "Train Sim World® 6: Spirit of Steam: Liverpool Lime Street - Crewe",
    "World of Warships x Azur Lane — Quest for AL Avrora",
    "World of Warships — Anniversary Party Favor",
}

# pattern hits that ARE playable games (bundles of full games count as games)
STANDALONE_TITLES = {
    '3 out of 10, EP 1: "Welcome To Shovelworks"',
    "Costume Quest",
    "Costume Quest 2",
    "HOT WHEELS UNLEASHED™",
    "Jackbox Party Pack 4",
    "Q.U.B.E. ULTIMATE BUNDLE",
    "The Jackbox Party Pack",
    "Wheels of Aurelia",
}


def join_key(series: pd.Series) -> pd.Series:
    """Normalize a title series into a stable join key (strip + collapse spaces)."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


def load_base() -> pd.DataFrame:
    """Load the cleaned event-level base and apply core column renames + dates.

    Also applies the snapshot-level corrections from the July 2026 review: title
    casing folds, retiring the transient 'next' marker, and the standalone-game
    flag.
    """
    df = pd.read_csv(BASE_FILE).rename(columns=CORE_RENAME)
    df["title"] = df["title"].replace(CANONICAL_TITLES)
    df["from_date"] = pd.to_datetime(df["from_date"], errors="coerce")
    df["to_date"] = pd.to_datetime(df["to_date"], errors="coerce")
    df["giveaway_year"] = df["from_date"].dt.year

    # 'next' marked the upcoming giveaway at scrape time; those windows have since
    # completed, so relabel them as ordinary events (provenance goes to notes)
    upcoming = df["giveaway_type"].eq("next")
    marker = "was listed as upcoming ('next') at scrape time"
    df.loc[upcoming & df["notes"].notna(), "notes"] = df["notes"] + "; " + marker
    df.loc[upcoming & df["notes"].isna(), "notes"] = marker
    df.loc[upcoming, "giveaway_type"] = None

    # 'dupe', 'dupe2', 'dupe3' all mark a repeat giveaway of a prior title
    df["is_repeat"] = df["giveaway_type"].astype("string").str.startswith("dupe").fillna(False)
    df["is_standalone_game"] = classify_standalone(df)
    return df


def classify_standalone(df: pd.DataFrame) -> pd.Series:
    """Flag each event as a standalone playable game vs add-on/in-game content.

    A row counts as add-on content when its notes say so ("In-game content...",
    "Requires base game..."), its giveaway_type is one of the pack markers, or its
    title carries an add-on word / sits on the curated exception lists. Everything
    else - including bundles of full games - is a standalone game.
    """
    notes = df["notes"].astype("string").str.lower()
    addon_notes = notes.str.contains("in-game content|requires base game", na=False)
    addon_type = df["giveaway_type"].isin(["pack", "pack2", "pack3"])
    addon_title = (
        df["title"].astype("string").str.contains(ADDON_TITLE_PATTERN, na=False)
        | df["title"].isin(ADDON_TITLES)
    )
    is_addon = (addon_notes | addon_type | addon_title) & ~df["title"].isin(STANDALONE_TITLES)
    return ~is_addon


def load_metacritic() -> pd.DataFrame:
    """Load the metacritic cache into a per-title frame, deduped on the join key."""
    if not MC_CACHE_FILE.exists():
        print("warning: no metacritic cache, skipping mc fields")
        return pd.DataFrame(columns=["_join_key"])

    with open(MC_CACHE_FILE, "r", encoding="utf-8") as handle:
        cache = json.load(handle)

    rows = [{"title": title, **fields} for title, fields in cache.items()]
    df = pd.DataFrame(rows)
    df["_join_key"] = join_key(df["title"])
    return df.drop(columns="title").drop_duplicates("_join_key", keep="first")


def load_hltb() -> pd.DataFrame:
    """Load the HLTB per-title scrape, lowercase its columns, dedupe on join key."""
    if not HLTB_FILE.exists():
        print("warning: no HLTB data, skipping hltb fields")
        return pd.DataFrame(columns=["_join_key"])

    df = pd.read_csv(HLTB_FILE)
    df["_join_key"] = join_key(df["Original_Title"])
    df = df.drop(columns="Original_Title").rename(columns=lambda c: c.lower())
    return df.drop_duplicates("_join_key", keep="first")


def load_egs() -> pd.DataFrame:
    """Load the EGS enrichment, deduped on join key (may be partial mid-run)."""
    if not EGS_FILE.exists():
        print("warning: no EGS enrichment yet, skipping egs fields")
        return pd.DataFrame(columns=["_join_key"])

    df = pd.read_csv(EGS_FILE)
    df["_join_key"] = join_key(df["title"])
    return df.drop(columns="title").drop_duplicates("_join_key", keep="first")


def attach(base: pd.DataFrame, enrichment: pd.DataFrame, source: str) -> pd.DataFrame:
    """Left-join a game-level enrichment frame onto the event-level base.

    Validates a many-events-to-one-title relationship so a silent fan-out in an
    enrichment source (duplicate keys) surfaces loudly instead of inflating rows.
    """
    if enrichment.empty or enrichment.columns.tolist() == ["_join_key"]:
        return base

    before = len(base)
    merged = base.merge(enrichment, on="_join_key", how="left", validate="m:1")
    matched = merged[enrichment.columns.drop("_join_key")[0]].notna().sum()
    print("  {}: matched {}/{} event rows".format(source, matched, before))
    return merged


def build_event_table() -> pd.DataFrame:
    """Assemble the canonical event-level table from base + all enrichments."""
    base = load_base()
    base["_join_key"] = join_key(base["title"])

    print("Joining enrichments onto {} event rows...".format(len(base)))
    table = attach(base, load_metacritic(), "metacritic")
    table = attach(table, load_hltb(), "hltb")
    table = attach(table, load_egs(), "egs")

    return table.drop(columns="_join_key")


def build_game_table(event: pd.DataFrame) -> pd.DataFrame:
    """Derive a game-level table: one row per unique title with giveaway counts.

    Enrichment fields are constant within a title (they were joined by title), so
    we take the per-title record and attach giveaway frequency and first/last
    giveaway dates.
    """
    counts = (
        event.groupby("title", as_index=False)
        .agg(
            giveaway_count=("title", "size"),
            first_giveaway=("from_date", "min"),
            last_giveaway=("from_date", "max"),
            # add-on verdicts can differ per event (notes vary); add-on wins
            is_standalone_game=("is_standalone_game", "min"),
        )
    )

    # event-specific columns we do NOT carry to the game level
    event_only = {"from_date", "to_date", "day_of_week", "duration_days",
                  "giveaway_type", "is_repeat", "giveaway_year", "notes", "color_category",
                  "is_standalone_game"}
    enrichment_cols = [c for c in event.columns if c not in event_only and c != "title"]
    per_title = event.drop_duplicates("title")[["title", *enrichment_cols]]

    return counts.merge(per_title, on="title", how="left")


def write_outputs(df: pd.DataFrame, stem: Path, label: str) -> None:
    """Write a dataframe to parquet (canonical) and csv (inspection mirror)."""
    df.to_parquet(stem.with_suffix(".parquet"), index=False)
    df.to_csv(stem.with_suffix(".csv"), index=False)
    print("Wrote {} ({} rows, {} cols) -> {}.parquet (+ .csv)".format(
        label, len(df), df.shape[1], stem.name))


def main() -> None:
    """Build and write the canonical event-level and game-level datasets."""
    event = build_event_table()
    write_outputs(event, EVENT_OUT, "event-level")

    game = build_game_table(event)
    write_outputs(game, GAME_OUT, "game-level")

    print("\nUnique titles: {} | Total giveaway events: {}".format(len(game), len(event)))


if __name__ == "__main__":
    main()
