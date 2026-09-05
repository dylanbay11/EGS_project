"""Reproduce the September 2026 repository review without scraping or editing data.

Run from the repository root with ``uv run --frozen python
outputs/repository_review_checks.py``. Results go to stdout only. These checks
describe the saved snapshot; they do not certify external source accuracy.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pandas as pd
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "development"))

import build_dataset as builder
import clean_data as cleaner
import egs_api_enrich as egs
import validate_dataset as validator


def show(label: str, value: object) -> None:
    """Print a labeled result, rendering dataframes as readable tables."""
    print("\n" + label)
    print(value.to_string(index=False) if isinstance(value, pd.DataFrame) else value)


def main() -> None:
    """Compare source grain, stored artifacts, rebuilds, and matching safeguards."""
    event = pd.read_parquet(ROOT / "data/egs_giveaways.parquet")
    game = pd.read_parquet(ROOT / "data/egs_giveaways_by_game.parquet")
    base = pd.read_csv(builder.BASE_FILE)
    sheets = cleaner.clean_gsheets()
    wiki = cleaner.clean_wiki()
    sheets["merge_title"] = cleaner.normalize_title_series(sheets["Title"])
    wiki["merge_title"] = cleaner.normalize_title_series(wiki["title_wiki"])
    joined = sheets.merge(wiki, on="merge_title", how="left").drop(columns="merge_title")
    show("Environment", {"python": sys.version, "pandas": pd.__version__})
    show("Grain", {
        "cleaned_sheet_rows": len(sheets), "wiki_rows": len(wiki),
        "rebuilt_initial_join_rows": len(joined), "saved_base_rows": len(base),
        "canonical_events": len(event), "canonical_titles": len(game),
        "duplicate_title_start_end_rows": int(event.duplicated(["title", "from_date", "to_date"]).sum()),
        "sheet_duplicate_title_start_end_rows": int(sheets.duplicated(["Title", "FROM", "TO"]).sum()),
    })
    comparison = (
        sheets.groupby("Title").size().rename("sheet_rows").to_frame()
        .join(base.groupby("Title").size().rename("merged_rows"))
        .assign(extra_rows=pd.col("merged_rows") - pd.col("sheet_rows"))
        .sort_values("extra_rows", ascending=False).reset_index()
    )
    show("Largest initial-join expansions", comparison.head(15))
    show("Bloons TD 6 source rows", sheets.loc[sheets["Title"].eq("Bloons TD 6"), ["Title", "FROM", "TO", "TYPE"]])
    show("Bloons TD 6 wiki rows", wiki.loc[wiki["title_wiki"].eq("Bloons TD 6"), ["title_wiki", "daterange_wiki", "year_wiki"]])
    show("Snapshot", {
        "first_date": str(event.from_date.min()), "last_date": str(event.from_date.max()),
        "missing_from_dates": int(event.from_date.isna().sum()),
        "standalone_titles": int(game.is_standalone_game.sum()),
        "egs_trusted_titles": int(game.egs_meets_threshold.eq(True).sum()),
        "egs_priced_titles": int(game.egs_original_price_usd.notna().sum()),
        "mc_named_titles": int(game.mc_title.notna().sum()),
        "mc_zero_scores": int(game.mc_criticScore.eq(0).sum()),
        "mc_positive_scores": int(game.mc_criticScore.gt(0).sum()),
        "hltb_named_titles": int(game.hltb_game_name.notna().sum()),
        "hltb_zero_main_story": int(game.hltb_main_story.eq(0).sum()),
        "hltb_positive_main_story": int(game.hltb_main_story.gt(0).sum()),
        "wiki_title_matches": int(game.title_wiki.notna().sum()),
        "wiki_developer_values": int(game.developer_wiki.notna().sum()),
        "trusted_price_sum": float(game.loc[game.egs_meets_threshold.eq(True), "egs_original_price_usd"].sum()),
    })
    show("Source type counts", sheets.TYPE.value_counts(dropna=False))
    show("Sheet color counts", sheets.COLOR_CATEGORY.value_counts(dropna=False))
    duplicate_source = sheets.loc[sheets.duplicated(["Title", "FROM", "TO"], keep=False)]
    show("Same-title/window source rows (inspect platform before deduplicating)", duplicate_source[["Title", "FROM", "TO", "TYPE", "NOTES", "COLOR_CATEGORY"]].head(16))
    show("Existing human-note examples", sheets.loc[
        sheets.Title.str.contains("Hitman|Cat Quest|Eastern Exorcist|Botany Manor", case=False, na=False),
        ["Title", "FROM", "TO", "TYPE", "NOTES", "COLOR_CATEGORY"],
    ])
    rebuilt_event = builder.build_event_table()
    rebuilt_game = builder.build_game_table(rebuilt_event)
    show("Stored artifacts reproduce", {
        "initial_join_values": joined.fillna("").astype(str).equals(base.fillna("").astype(str)),
        "canonical_event": rebuilt_event.equals(event),
        "canonical_game": rebuilt_game.equals(game),
    })
    import io
    joined_roundtrip = pd.read_csv(io.StringIO(joined.to_csv(index=False)))
    show("Initial join CSV-roundtrip equals saved base", joined_roundtrip.equals(base))
    differing = [column for column in base.columns if not joined_roundtrip[column].equals(base[column])]
    show("Initial join differing columns", differing)
    title_mismatch = joined_roundtrip.title_wiki.fillna("").ne(base.title_wiki.fillna(""))
    show("Wiki title assignments changed by a raw-source rebuild", joined_roundtrip.loc[title_mismatch, ["Title", "title_wiki", "daterange_wiki"]])
    show("Those rows in the saved base", base.loc[title_mismatch, ["Title", "title_wiki", "daterange_wiki"]])
    app = pd.read_csv(ROOT / "development/public/egs_app_data.csv")
    from build_app_data import APP_COLUMNS, BOOL_COLUMNS
    expected_app = event[APP_COLUMNS].copy()
    expected_app["from_date"] = expected_app.from_date.dt.date
    for column in BOOL_COLUMNS:
        expected_app[column] = expected_app[column].fillna(False).astype(bool)
    expected_app.loc[expected_app.mc_criticScore.eq(0), "mc_criticScore"] = pd.NA
    show("App extract equals documented canonical projection", pd.read_csv(io.StringIO(expected_app.to_csv(index=False))).equals(app))
    repeated_offers = game.loc[game.egs_meets_threshold.eq(True) & game.egs_offer_id.notna()].copy()
    repeated_offers = repeated_offers.loc[repeated_offers.duplicated(["egs_namespace", "egs_offer_id"], keep=False)]
    show("Different canonical titles sharing the same trusted EGS offer", repeated_offers[["title", "egs_match_title", "egs_original_price_usd", "egs_offer_id"]])
    show("BioShock and Cat Quest cross-source identity examples", game.loc[
        game.title.str.contains("BioShock|Cat Quest", na=False),
        ["title", "egs_match_title", "egs_match_score", "mc_title", "hltb_game_name"],
    ])
    show("Annual source rows versus canonical rows", sheets.assign(year=pd.to_datetime(sheets.FROM).dt.year).groupby("year").size().rename("sheet_rows").to_frame().join(event.groupby("giveaway_year").size().rename("canonical_rows")).reset_index())
    for stem in ("egs_giveaways", "egs_giveaways_by_game"):
        parquet = pd.read_parquet(ROOT / "data" / (stem + ".parquet"))
        csv = pd.read_csv(ROOT / "data" / (stem + ".csv"))
        # Round-trip the parquet through CSV in memory to compare like encodings.
        import io
        mirror = pd.read_csv(io.StringIO(parquet.to_csv(index=False)))
        show(stem + " CSV mirror equals parquet CSV", mirror.equals(csv))
    mc = game.loc[game.mc_title.notna(), ["title", "mc_title", "mc_criticScore"]].copy()
    mc["title_ratio"] = [fuzz.ratio(egs.normalize_title(a), egs.normalize_title(b)) for a, b in zip(mc.title, mc.mc_title)]
    show("Lowest Metacritic name ratios (triage, not automatic wrong-match verdicts)", mc.sort_values("title_ratio").head(20))
    show("EGS related-product candidates marked trusted", game.loc[
        game.egs_meets_threshold.eq(True)
        & game.egs_match_title.fillna("").str.contains("edition|bundle|collection|pass", case=False),
        ["title", "egs_match_title", "egs_original_price_usd", "egs_notes"],
    ].head(25))
    candidates = [{"title": "Example Game Deluxe Edition"}, {"title": "Example Game"}]
    show("Synthetic EGS exact-vs-subset tie", egs.pick_best_match("Example Game", candidates))
    future = pd.DataFrame({"Title": ["Future Game"], "FROM": ["2099-01-01"], "TO": ["2099-01-08"], "TYPE": ["next"], "NOTES": [None]})
    original_read_csv = builder.pd.read_csv
    try:
        builder.pd.read_csv = lambda *args, **kwargs: future.copy()
        show("Synthetic future next marker after load_base", builder.load_base()[["title", "from_date", "giveaway_type", "notes"]])
    finally:
        builder.pd.read_csv = original_read_csv
    validator._findings.clear()
    validator.validate_grain(event, game)
    validator.validate_sources_present(event)
    validator.validate_prices(event)
    validator.validate_dates(event)
    validator.validate_scores(event)
    show("Existing validator findings", validator._findings)
    failures = []
    for path in sorted((ROOT / "development").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 11))
        except SyntaxError as exc:
            failures.append({"file": path.name, "line": exc.lineno, "reason": exc.msg})
    show("Python 3.11 grammar check (not a runtime compatibility test)", failures)
    cache = json.loads(egs.CACHE_FILE.read_text(encoding="utf-8"))
    show("EGS cache note counts", pd.Series([row.get("egs_notes", "") for row in cache.values()]).value_counts().head(12))


if __name__ == "__main__":
    main()
