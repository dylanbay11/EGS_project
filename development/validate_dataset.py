"""Lightweight validation for the canonical Epic giveaway dataset.

Not a pytest suite (overkill for this project per AGENTS.md) - just a set of
realistic checks that catch the kinds of breakage this pipeline actually hits:
schema/grain drift, fan-out from a bad join, impossible prices/dates/scores, and
an enrichment source silently going all-null.

Errors fail the run (exit 1); warnings are printed but tolerated.

Run:
    uv run python development/validate_dataset.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EVENT_FILE = DATA_DIR / "egs_giveaways.parquet"
GAME_FILE = DATA_DIR / "egs_giveaways_by_game.parquet"

# results accumulate here as (level, message); level is "error" or "warn"
_findings: list[tuple[str, str]] = []


def check(condition: bool, message: str, level: str = "error") -> None:
    """Record a finding when a condition fails; no-op when it passes."""
    if not condition:
        _findings.append((level, message))


def in_range(series: pd.Series, low: float, high: float) -> bool:
    """Return True when every non-null value sits within [low, high]."""
    values = series.dropna()
    if values.empty:
        return True
    return bool((values >= low).all() and (values <= high).all())


def validate_grain(event: pd.DataFrame, game: pd.DataFrame) -> None:
    """Check the event/game grain relationship and key uniqueness."""
    check(not event.empty, "event table is empty")
    check(not game.empty, "game table is empty")
    check(event["title"].notna().all(), "event table has null titles")
    check(not game["title"].duplicated().any(), "game table has duplicate titles (grain broken)")
    check(
        game["title"].nunique() == event["title"].nunique(),
        "game-level title count != distinct event titles",
    )
    check(
        len(event) >= len(game),
        "fewer event rows than unique titles (impossible for event grain)",
    )


def validate_sources_present(event: pd.DataFrame) -> None:
    """Each enrichment source should contribute at least some non-null data."""
    expectations = {
        "title_wiki": "Wikipedia",
        "mc_title": "Metacritic",
        "hltb_game_name": "HowLongToBeat",
        "egs_match_title": "EGS API",
    }
    for column, source in expectations.items():
        present = column in event.columns and event[column].notna().any()
        # EGS may legitimately be mid-run; warn rather than error there
        level = "warn" if source == "EGS API" else "error"
        check(present, "{} enrichment is entirely missing ({})".format(source, column), level=level)


def validate_prices(event: pd.DataFrame) -> None:
    """Prices must be non-negative and within a sane retail range."""
    if "egs_original_price_usd" not in event.columns:
        return
    prices = event["egs_original_price_usd"].dropna()
    check((prices >= 0).all() if not prices.empty else True, "negative EGS prices present")
    check(in_range(prices, 0, 1000), "EGS prices outside the plausible 0-1000 USD range", level="warn")


def validate_dates(event: pd.DataFrame) -> None:
    """Giveaway windows and years should be ordered and in-era."""
    bad_window = (event["to_date"] < event["from_date"]).sum()
    check(bad_window == 0, "{} rows have to_date before from_date".format(bad_window))

    next_year = datetime.now().year + 1
    check(
        in_range(event["giveaway_year"], 2018, next_year),
        "giveaway_year outside 2018-{}".format(next_year),
    )
    check(in_range(event["duration_days"], 0, 400), "duration_days outside 0-400", level="warn")


def validate_scores(event: pd.DataFrame) -> None:
    """Match and review scores must sit on their documented scales."""
    if "mc_criticScore" in event.columns:
        check(in_range(event["mc_criticScore"], 0, 100), "mc_criticScore outside 0-100")
    if "egs_match_score" in event.columns:
        check(in_range(event["egs_match_score"], 0, 100), "egs_match_score outside 0-100")
    if "hltb_match_score" in event.columns:
        check(in_range(event["hltb_match_score"], 0, 1), "hltb_match_score outside 0-1")


def main() -> None:
    """Load the canonical datasets and run every validation check."""
    if not EVENT_FILE.exists() or not GAME_FILE.exists():
        print("Missing canonical dataset(s). Run development/build_dataset.py first.")
        sys.exit(1)

    event = pd.read_parquet(EVENT_FILE)
    game = pd.read_parquet(GAME_FILE)

    validate_grain(event, game)
    validate_sources_present(event)
    validate_prices(event)
    validate_dates(event)
    validate_scores(event)

    errors = [msg for level, msg in _findings if level == "error"]
    warnings = [msg for level, msg in _findings if level == "warn"]

    print("Validated {} events / {} games.".format(len(event), len(game)))
    for msg in warnings:
        print("  WARN:  {}".format(msg))
    for msg in errors:
        print("  ERROR: {}".format(msg))

    if errors:
        print("\nFAILED with {} error(s).".format(len(errors)))
        sys.exit(1)
    print("\nAll checks passed{}.".format(
        " ({} warning(s))".format(len(warnings)) if warnings else ""))


if __name__ == "__main__":
    main()
