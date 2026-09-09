"""Build a bounded, source-reconciled dashboard sample without changing the pipeline.

Run with ``uv run python development/build_dashboard_sample.py``. Reads the
April source sheet and canonical cache, writes a sample parquet under data/,
and records selection evidence under outputs/. No scraping is performed.
"""

from hashlib import sha256
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "data/2026-04-29-gsheets.xlsx"
CANONICAL = ROOT / "data/egs_giveaways.parquet"
OUTPUT = ROOT / "data/dashboard_sample.parquet"
SAMPLE_SIZE = 40
METADATA = [
    "title", "egs_match_title", "mc_title", "hltb_game_name", "title_wiki",
    "egs_original_price_usd", "egs_currency", "mc_criticScore", "mc_slug",
    "hltb_main_story", "hltb_main_extra", "hltb_completionist", "egs_tags",
    "egs_publisher", "developer_wiki", "egs_short_description", "link_wiki",
    "egs_slug", "egs_namespace", "egs_offer_id",
]


def normalize_title(value: object) -> str:
    """Ignore case/punctuation, preserving every word and sequel numeral."""
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def source_events() -> pd.DataFrame:
    """Read ordinary PC rows, retaining actual Excel row numbers for tracing.

    Restrict the prototype to 2018–2025 completed windows with no source notes.
    Bundles, mobile, content packs, announcements, and ambiguous source rows
    are excluded rather than repaired or collapsed in this sample branch.
    """
    frame = pd.read_excel(SHEET, skiprows=15).iloc[:, :7].copy()
    frame.columns = ["from_date", "to_date", "day", "days", "type", "title", "notes"]
    frame["source_sheet_row"] = range(17, 17 + len(frame))
    for column in ["from_date", "to_date"]:
        frame[column] = pd.to_datetime(frame[column].ffill(), errors="coerce")
    frame["title"] = frame["title"].str.strip()
    return frame.loc[
        frame["type"].fillna("").isin(["", "dupe", "dupe2", "dupe3"])
        & frame["notes"].isna()
        & frame["title"].notna()
        & frame["from_date"].between("2018-01-01", "2025-12-31")
        & frame["to_date"].le(pd.Timestamp("2026-04-29"))
        & frame["to_date"].ge(frame["from_date"]),
        ["title", "from_date", "to_date", "source_sheet_row"],
    ].reset_index(drop=True)


def build_sample() -> pd.DataFrame:
    """Select up to 40 eligible games across first-giveaway years and save evidence.

    Reject entire titles with duplicate windows, shared product IDs, or
    conflicting displayed metadata. Reconcile every included event to an
    unambiguous source row. Selection uses a stable title hash within each
    first-giveaway year, round-robin across years, without ranking by score.
    Raises ValueError if the caches cannot provide the requested sample.
    """
    events = pd.read_parquet(CANONICAL)
    source = source_events()
    keys = ["title", "from_date", "to_date"]
    games = events.drop_duplicates("title").reset_index(drop=True)
    eligible = (
        games["is_standalone_game"].eq(True)
        & games["egs_meets_threshold"].eq(True)
        & games["hltb_found"].eq(True)
        & games["mc_criticScore"].between(1, 100)
        & games["hltb_main_story"].between(0.01, 500)
        & games["egs_original_price_usd"].gt(0)
        & games["egs_currency"].eq("USD")
        & games[METADATA].drop(columns=[
            "hltb_main_extra", "hltb_completionist", "egs_slug"
        ]).notna().all(axis=1)
    )
    for column in ["egs_match_title", "mc_title", "hltb_game_name", "title_wiki"]:
        eligible &= games["title"].map(normalize_title).eq(
            games[column].map(normalize_title)
        )
    eligible &= ~games["title"].str.contains(
        r"edition|collection|remaster|\bbundle\b", case=False, regex=True
    )
    for frame in [events, source]:
        ambiguous = frame.loc[frame.duplicated(keys, keep=False), "title"]
        eligible &= ~games["title"].isin(ambiguous)
    shared_offers = games.loc[
        games.duplicated(["egs_namespace", "egs_offer_id"], keep=False), "title"
    ]
    eligible &= ~games["title"].isin(shared_offers)
    metadata_versions = (
        events[METADATA].drop_duplicates().groupby("title").size()
        .reset_index(name="versions")
    )
    eligible &= ~games["title"].isin(
        metadata_versions.loc[metadata_versions["versions"].gt(1), "title"]
    )

    candidate_events = events.loc[
        events["title"].isin(games.loc[eligible, "title"])
        & events["from_date"].between("2018-01-01", "2025-12-31")
    ]
    reconciliation = candidate_events[keys].merge(
        source.loc[source["title"].isin(candidate_events["title"])],
        on=keys, how="outer", validate="1:1", indicator=True
    )
    unmatched = reconciliation.loc[reconciliation["_merge"].ne("both"), "title"]
    matched = reconciliation.loc[
        reconciliation["_merge"].eq("both")
        & ~reconciliation["title"].isin(unmatched)
    ].drop(columns="_merge").reset_index(drop=True)
    candidates = matched.groupby("title", as_index=False).agg(first=("from_date", "min"))
    candidates["year"] = candidates["first"].dt.year
    candidates["selection_order"] = candidates["title"].map(
        lambda title: sha256(("egs-dashboard-v2:" + title).encode()).hexdigest()
    )
    candidates = candidates.sort_values(["year", "selection_order"]).reset_index(drop=True)
    candidates["within_year"] = candidates.groupby("year").cumcount()
    selected = candidates.sort_values(["within_year", "year"]).head(SAMPLE_SIZE)
    if len(selected) != SAMPLE_SIZE:
        raise ValueError(f"Only {len(selected)} eligible games; expected {SAMPLE_SIZE}.")

    sample = matched.loc[matched["title"].isin(selected["title"])].merge(
        games[METADATA], on="title", how="left", validate="m:1"
    ).sort_values(["from_date", "title"]).reset_index(drop=True)
    sample["source_sheet_row"] = sample["source_sheet_row"].astype(int)
    sample["giveaway_year"] = sample["from_date"].dt.year
    sample["sample_occurrence"] = sample.groupby("title").cumcount() + 1
    sample.to_parquet(OUTPUT, index=False)
    public = ROOT / "development/dashboard/public"
    public.mkdir(parents=True, exist_ok=True)
    # JSON is a deployment asset; the analysis artifact stays parquet in data/.
    sample.to_json(public / "sample.json", orient="records", date_format="iso", indent=2)

    evidence = sample[[
        "title", "from_date", "to_date", "source_sheet_row", "egs_match_title",
        "mc_title", "hltb_game_name", "title_wiki", "egs_namespace", "egs_offer_id",
    ]]
    evidence.to_csv(ROOT / "outputs/dashboard_sample_audit.csv", index=False)
    hashes = {path.name: sha256(path.read_bytes()).hexdigest() for path in [SHEET, CANONICAL]}
    report = f"""# Dashboard sample evidence

Built from local caches; no live source verification or pipeline repair implied.

- Output: `data/dashboard_sample.parquet` — {len(sample)} title/window records,
  {sample.title.nunique()} distinct games, {sample.giveaway_year.min()}–{sample.giveaway_year.max()}.
- Eligible pool after source reconciliation: {len(candidates)} games.
- All included titles agree across EGS, MC, HLTB, and Wikipedia after case and
  punctuation normalization. No words, edition suffixes, or sequel numerals removed.
- Reject entire titles affected by duplicated canonical/source windows, shared
  EGS IDs, conflicting displayed metadata, edition/collection naming, or unmatched
  ordinary source events. Source rows have no notes and only standard/repeat types.
- Positive USD cached list prices, MC critic scores, HLTB main-story hours, store
  tags, publisher, description, and Wikipedia developer/link required.
- Round-robin selection across first-giveaway years, deterministic SHA-256 title
  ordering within year. This is a deliberately enriched design fixture, **not a
  representative sample** for estimating the whole giveaway program.
- History is the 2018–2025 source-backed history for included games only.
  No program-wide cadence, trend, monetary savings, or Epic expenditure claims.
- Price observation dates are unavailable; prices are cached USD list prices,
  not current prices or giveaway-day values. MC platform-specific score selection
  is not recorded. HLTB hours are estimates, not personal completion guarantees.
- `outputs/dashboard_sample_audit.csv` preserves the source Excel row for each
  event and all matched titles/product IDs. This is inspectable evidence of cache
  agreement, not independent certification of the upstream websites.

## Input fingerprints

"""
    for name, digest in hashes.items():
        report += f"- `{name}`: `{digest}`\n"
    (ROOT / "outputs/dashboard_sample_report.md").write_text(report)
    print(f"Selected {sample.title.nunique()} games / {len(sample)} windows from {len(candidates)} eligible games.")
    return sample


if __name__ == "__main__":
    build_sample()
