import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # Stage 2 interactive explorer over the canonical giveaway dataset. A separate
    # artifact from eda.py: eda.py is a fixed narrative first-look, this is a hands-on
    # filter-and-poke tool. Two tabs — "Explore" (reactive filters → table + charts)
    # and "Triage" (the open data-quality questions from REVIEW_NEEDED.md, surfaced as
    # sortable tables so they're point-and-click instead of a markdown wall).
    #
    # marimo wiring follows development/MARIMO_NOTES.md: UI elements are defined as
    # globals in one cell and their .value is read in *downstream* cells. NA-safe masks
    # (.fillna(False)) are used throughout because Arrow-backed boolean indexing raises
    # on NA.

    import math
    from pathlib import Path

    import marimo as mo
    import pandas as pd
    import plotly.express as px

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_ROOT / "data"

    event = pd.read_parquet(DATA_DIR / "egs_giveaways.parquet")
    game = pd.read_parquet(DATA_DIR / "egs_giveaways_by_game.parquet")

    # filter domains, derived from the data so the controls can't drift from it
    YEAR_MIN = int(event["giveaway_year"].min())
    YEAR_MAX = int(event["giveaway_year"].max())
    PRICE_MAX = int(math.ceil(float(event["egs_original_price_usd"].max())))
    TYPE_OPTIONS = sorted(event["giveaway_type"].fillna("standard").unique().tolist())
    TAG_OPTIONS = sorted(
        event["egs_tags"].dropna().str.split(", ").explode().str.strip().unique().tolist()
    )
    return (
        PRICE_MAX,
        TAG_OPTIONS,
        TYPE_OPTIONS,
        YEAR_MAX,
        YEAR_MIN,
        event,
        game,
        mo,
        px,
    )


@app.cell
def _(event, game, mo):
    mo.md(
        """
        # Epic Giveaways — Interactive Explorer

        Filter the canonical `egs_giveaways` dataset and watch the table and charts react.
        - **{events}** giveaway events (event-level) · **{games}** unique titles (game-level)
        - Use the **Triage** tab for the open data-quality questions (`REVIEW_NEEDED.md`).

        > Price/tag habit: leave **"Confident EGS matches only"** on — it restricts to
        > `egs_meets_threshold == True`, the correct base for money/tag analysis.
        """.format(events=len(event), games=len(game))
    )
    return


@app.cell
def _(PRICE_MAX, TAG_OPTIONS, TYPE_OPTIONS, YEAR_MAX, YEAR_MIN, mo):
    # the filter controls — assigned to globals here, read in the derive cell below
    grain = mo.ui.dropdown(
        options=["event", "game"], value="event", label="Grain"
    )
    confident_only = mo.ui.switch(value=True, label="Confident EGS matches only")
    year_range = mo.ui.range_slider(
        start=YEAR_MIN, stop=YEAR_MAX, step=1, value=(YEAR_MIN, YEAR_MAX),
        show_value=True, label="Giveaway year (event grain)",
    )
    type_select = mo.ui.multiselect(
        options=TYPE_OPTIONS, value=[], label="Giveaway type (event grain; empty = all)"
    )
    price_range = mo.ui.range_slider(
        start=0, stop=PRICE_MAX, step=5, value=(0, PRICE_MAX),
        show_value=True, label="Retail price USD",
    )
    min_mc = mo.ui.slider(
        start=0, stop=100, step=5, value=0, show_value=True, label="Min Metacritic score"
    )
    min_hours = mo.ui.slider(
        start=0, stop=100, step=5, value=0, show_value=True, label="Min HLTB main-story hrs"
    )
    tag_select = mo.ui.multiselect(
        options=TAG_OPTIONS, value=[], label="EGS tags — match ANY (empty = all)"
    )
    return (
        confident_only,
        grain,
        min_hours,
        min_mc,
        price_range,
        tag_select,
        type_select,
        year_range,
    )


@app.cell
def _(
    confident_only,
    grain,
    min_hours,
    min_mc,
    mo,
    price_range,
    tag_select,
    type_select,
    year_range,
):
    # lay the controls out into a panel (rendered inside the Explore tab)
    filter_panel = mo.vstack(
        [
            mo.md("### Filters"),
            mo.hstack([grain, confident_only], justify="start", gap=2),
            mo.hstack([year_range, price_range], justify="start", gap=2),
            mo.hstack([min_mc, min_hours], justify="start", gap=2),
            type_select,
            tag_select,
        ]
    )
    return (filter_panel,)


@app.cell
def _(
    PRICE_MAX,
    YEAR_MAX,
    YEAR_MIN,
    confident_only,
    event,
    game,
    grain,
    min_hours,
    min_mc,
    price_range,
    tag_select,
    type_select,
    year_range,
):
    # apply every active filter to the chosen grain. Year/type only exist event-level,
    # so they're applied only at event grain. Every mask is .fillna(False) because the
    # enrichment columns are sparse and NA can't go into boolean indexing.
    filtered = event if grain.value == "event" else game

    if confident_only.value:
        filtered = filtered[filtered["egs_meets_threshold"].fillna(False)]

    if grain.value == "event":
        ylo, yhi = year_range.value
        if (ylo, yhi) != (YEAR_MIN, YEAR_MAX):
            filtered = filtered[filtered["giveaway_year"].between(ylo, yhi).fillna(False)]
        if type_select.value:
            keep = set(type_select.value)
            filtered = filtered[filtered["giveaway_type"].fillna("standard").isin(keep)]

    plo, phi = price_range.value
    if (plo, phi) != (0, PRICE_MAX):
        filtered = filtered[filtered["egs_original_price_usd"].between(plo, phi).fillna(False)]

    if min_mc.value > 0:
        filtered = filtered[(filtered["mc_criticScore"] >= min_mc.value).fillna(False)]

    if min_hours.value > 0:
        filtered = filtered[(filtered["hltb_main_story"] >= min_hours.value).fillna(False)]

    if tag_select.value:
        wanted = set(tag_select.value)
        has_tag = filtered["egs_tags"].fillna("").apply(
            lambda s: bool(wanted & {t.strip() for t in s.split(",") if t.strip()})
        )
        filtered = filtered[has_tag]

    # curated display columns: grain-specific context first, then the shared enrichment
    common_cols = [
        "title", "egs_match_title", "egs_match_score", "egs_original_price_usd",
        "egs_publisher", "egs_tags", "mc_criticScore", "hltb_main_story",
        "egs_meets_threshold",
    ]
    grain_cols = (
        ["giveaway_year", "giveaway_type", "from_date"]
        if grain.value == "event"
        else ["giveaway_count", "first_giveaway", "last_giveaway"]
    )
    display_cols = [c for c in grain_cols + common_cols if c in filtered.columns]
    return display_cols, filtered


@app.cell
def _(filtered, mo):
    # live headline: how big is this slice and what's its summed retail value
    total_value = float(filtered["egs_original_price_usd"].sum())
    priced_n = int(filtered["egs_original_price_usd"].notna().sum())
    summary_box = mo.md(
        "**{rows}** rows in selection · **{priced}** priced · "
        "summed retail value **${value:,.0f}**".format(
            rows=len(filtered), priced=priced_n, value=total_value
        )
    )
    return (summary_box,)


@app.cell
def _(display_cols, filtered, mo):
    # the filtered rows, sortable + downloadable (read-only — no selection wired)
    table_view = mo.ui.table(
        filtered[display_cols], selection=None, page_size=15, show_download=True
    )
    return (table_view,)


@app.cell
def _(filtered, mo, px):
    # price distribution of the current slice
    priced = filtered[filtered["egs_original_price_usd"].notna()]
    if priced.empty:
        price_fig = mo.md("_No priced rows in this selection._")
    else:
        price_fig = px.histogram(
            priced, x="egs_original_price_usd", nbins=40,
            title="Retail price (USD) — n={}".format(len(priced)),
        )
    return (price_fig,)


@app.cell
def _(filtered, mo, px):
    # giveaways-per-year cadence (event grain only — game grain has no giveaway_year)
    if "giveaway_year" not in filtered.columns:
        year_fig = mo.md("_Per-year cadence is event-grain only._")
    elif filtered.empty:
        year_fig = mo.md("_No rows in this selection._")
    else:
        per_year = filtered.groupby("giveaway_year", as_index=False).agg(
            events=("title", "size")
        )
        year_fig = px.bar(
            per_year, x="giveaway_year", y="events", text="events",
            title="Giveaways per year (filtered)",
        )
    return (year_fig,)


@app.cell
def _(filtered, mo, px):
    # most common EGS tags in the current slice (same explode-and-count recipe as eda.py)
    tag_counts = (
        filtered["egs_tags"].dropna().str.split(", ").explode().str.strip()
        .value_counts().head(20).reset_index()
    )
    tag_counts.columns = ["tag", "count"]
    if tag_counts.empty:
        tag_fig = mo.md("_No tags in this selection._")
    else:
        tag_fig = px.bar(
            tag_counts, x="count", y="tag", orientation="h", height=600,
            title="Top EGS tags (filtered)",
        )
    return (tag_fig,)


@app.cell
def _(filter_panel, mo, price_fig, summary_box, table_view, tag_fig, year_fig):
    # assemble the Explore tab
    explore_view = mo.vstack(
        [filter_panel, summary_box, table_view, price_fig, year_fig, tag_fig]
    )
    return (explore_view,)


@app.cell
def _(game, mo):
    # TRIAGE A — $0 retail price on a game that clearly exists (has MC/HLTB). Either a
    # genuine freebie or a wrong match. (REVIEW_NEEDED.md §A)
    zero_priced = game[
        game["egs_match_title"].notna()
        & (game["egs_original_price_usd"] == 0).fillna(False)
        & (game["mc_title"].notna() | game["hltb_game_name"].notna())
    ][
        ["title", "egs_match_title", "egs_match_score", "egs_publisher",
         "egs_original_price_usd", "mc_criticScore", "hltb_game_name"]
    ]
    triage_zero = mo.vstack(
        [
            mo.md(
                "### A · $0-priced real games — {} titles\n"
                "Genuine free-to-play, or a wrong match? Confirm/correct each.".format(
                    len(zero_priced)
                )
            ),
            mo.ui.table(zero_priced, selection=None, page_size=15),
        ]
    )
    return (triage_zero,)


@app.cell
def _(game, mo):
    # TRIAGE B — low-confidence EGS matches. <80 don't get deep fields and are flagged
    # egs_meets_threshold=False, but still carry a (often $0) price. (REVIEW_NEEDED.md §B)
    low_conf = game[(game["egs_match_score"] < 90).fillna(False)][
        ["title", "egs_match_title", "egs_match_score", "egs_meets_threshold",
         "egs_original_price_usd"]
    ].sort_values("egs_match_score")
    triage_lowconf = mo.vstack(
        [
            mo.md(
                "### B · Low-confidence EGS matches (< 90) — {} titles\n"
                "`egs_meets_threshold` is the ≥ 80 cutoff; rows below it weren't treated "
                "as real matches.".format(len(low_conf))
            ),
            mo.ui.table(low_conf, selection=None, page_size=15),
        ]
    )
    return (triage_lowconf,)


@app.cell
def _(game, mo):
    # TRIAGE C — titles with no EGS match at all (mostly DLC/bundles/unlocks, expected
    # to be unmatched, but worth skimming for a wrongly-missed standalone game). (§C)
    no_match = game[game["egs_match_title"].isna()][
        ["title", "giveaway_count", "mc_title", "hltb_game_name"]
    ]
    triage_nomatch = mo.vstack(
        [
            mo.md(
                "### C · No EGS match — {} titles\n"
                "Mostly DLC / promo bundles / in-game unlocks (correctly unmatched). Skim "
                "for any standalone game that slipped through.".format(len(no_match))
            ),
            mo.ui.table(no_match, selection=None, page_size=15),
        ]
    )
    return (triage_nomatch,)


@app.cell
def _(event, mo):
    # TRIAGE D — marker rows: `next` (current/upcoming at scrape time, §D) and the odd
    # `-` giveaway_type values surfaced while building this explorer (not in REVIEW_NEEDED
    # yet — flagged here for triage, not auto-fixed).
    marker_types = ["next", "-"]
    markers = event[event["giveaway_type"].fillna("standard").isin(marker_types)][
        ["title", "from_date", "giveaway_type", "notes"]
    ].sort_values(["giveaway_type", "from_date"])
    triage_markers = mo.vstack(
        [
            mo.md(
                "### D · Marker / oddity rows — {} rows\n"
                "`next` = the upcoming giveaway at scrape time. `-` is an unexplained "
                "giveaway_type value (4 rows) worth a decision: relabel or drop.".format(
                    len(markers)
                )
            ),
            mo.ui.table(markers, selection=None, page_size=15),
        ]
    )
    return (triage_markers,)


@app.cell
def _(game, mo):
    # TRIAGE E — where EGS and Wikipedia disagree on publisher. Usually both are "right"
    # (regional label / parent vs studio), but a handful could be a join bug. (§E)
    both_pub = game[game["egs_publisher"].notna() & game["publisher_wiki"].notna()]
    pub_disagree = both_pub[
        both_pub["egs_publisher"].str.lower().str.strip()
        != both_pub["publisher_wiki"].str.lower().str.strip()
    ][["title", "egs_publisher", "publisher_wiki"]]
    triage_pub = mo.vstack(
        [
            mo.md(
                "### E · Publisher disagreements (EGS vs Wikipedia) — {} of {} comparable\n"
                "Eyeball a few to confirm it's noise (labels/regions), not a join "
                "bug.".format(len(pub_disagree), len(both_pub))
            ),
            mo.ui.table(pub_disagree, selection=None, page_size=15),
        ]
    )
    return (triage_pub,)


@app.cell
def _(
    mo,
    triage_lowconf,
    triage_markers,
    triage_nomatch,
    triage_pub,
    triage_zero,
):
    # assemble the Triage tab
    triage_view = mo.vstack(
        [
            mo.md(
                "## Data-quality triage\n"
                "Open questions from `REVIEW_NEEDED.md`, surfaced as sortable tables. "
                "These views are **read-only** — they flag, they don't edit the dataset."
            ),
            triage_zero,
            triage_lowconf,
            triage_nomatch,
            triage_markers,
            triage_pub,
        ]
    )
    return (triage_view,)


@app.cell
def _(explore_view, mo, triage_view):
    mo.ui.tabs({"Explore": explore_view, "Triage": triage_view})
    return


if __name__ == "__main__":
    app.run()
