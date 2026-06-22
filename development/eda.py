import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # Stage 1 EDA over the canonical giveaway dataset. Two jobs at once:
    # (1) first look at the findings, and (2) catch data weirdness that should
    # loop back into the build/clean step. The DATA ISSUES cell at the bottom is
    # the feedback list.

    from pathlib import Path

    import marimo as mo
    import pandas as pd
    import plotly.express as px

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_ROOT / "data"

    event = pd.read_parquet(DATA_DIR / "egs_giveaways.parquet")
    game = pd.read_parquet(DATA_DIR / "egs_giveaways_by_game.parquet")
    return event, game, mo, px


@app.cell
def _(event, game, mo):
    mo.md(
        """
        # Epic Giveaways — Exploratory Analysis

        Built on the canonical `egs_giveaways` dataset.
        - **{events}** giveaway events (event-level grain)
        - **{games}** unique titles (game-level grain)

        This notebook is also a data-quality pass; see **Data Issues** at the end.
        """.format(events=len(event), games=len(game))
    )
    return


@app.cell
def _(event, mo, px):
    # how complete is each column? a quick missingness read across the dataset
    fill = (
        (event.notna().mean() * 100)
        .round(1)
        .sort_values()
        .reset_index()
    )
    fill.columns = ["column", "pct_filled"]

    missing_fig = px.bar(
        fill,
        x="pct_filled",
        y="column",
        orientation="h",
        title="Column fill rate (%)",
        height=900,
    )
    mo.vstack([mo.md("## Missingness overview"), missing_fig])
    return


@app.cell
def _(event, mo, px):
    # giveaway cadence: how many games went free each year
    per_year = (
        event.groupby("giveaway_year", as_index=False)
        .agg(events=("title", "size"))
    )
    year_fig = px.bar(
        per_year,
        x="giveaway_year",
        y="events",
        title="Giveaway events per year",
        text="events",
    )
    mo.vstack([mo.md("## Cadence — giveaways per year"), year_fig])
    return


@app.cell
def _(event, mo, px):
    # what kinds of giveaways are these? standard vs repeats vs bundles vs mobile
    type_counts = (
        event["giveaway_type"]
        .fillna("standard")
        .value_counts()
        .reset_index()
    )
    type_counts.columns = ["giveaway_type", "count"]
    type_fig = px.bar(
        type_counts,
        x="giveaway_type",
        y="count",
        title="Giveaway type distribution",
        text="count",
    )
    mo.vstack([mo.md("## Giveaway types"), type_fig])
    return


@app.cell
def _(event, mo, px):
    # the headline money angle: distribution of retail value given away
    priced = event[event["egs_original_price_usd"].notna()]
    price_fig = px.histogram(
        priced,
        x="egs_original_price_usd",
        nbins=40,
        title="Retail price of giveaways (USD, EGS) — n={}".format(len(priced)),
    )
    mo.vstack([mo.md("## Price distribution"), price_fig])
    return


@app.cell
def _(event, mo, px):
    # cumulative retail dollars given away over time (event-level, priced rows)
    timeline = (
        event[event["egs_original_price_usd"].notna()]
        .sort_values("from_date")
        .assign(cumulative_usd=lambda d: d["egs_original_price_usd"].cumsum())
    )
    cumulative_fig = px.line(
        timeline,
        x="from_date",
        y="cumulative_usd",
        title="Cumulative retail value given away (USD)",
    )
    mo.vstack([mo.md("## Cumulative dollars over time"), cumulative_fig])
    return


@app.cell
def _(game, mo, px):
    # which games has Epic re-gifted the most?
    repeats = (
        game[game["giveaway_count"] > 1]
        .sort_values("giveaway_count")
        .tail(20)
    )
    repeat_fig = px.bar(
        repeats,
        x="giveaway_count",
        y="title",
        orientation="h",
        title="Most-repeated giveaways (top 20)",
        height=600,
    )
    mo.vstack([mo.md("## Most-repeated games"), repeat_fig])
    return


@app.cell
def _(event, mo, px):
    # what genres/tags dominate? split the comma-joined EGS tags and count
    tag_series = (
        event["egs_tags"]
        .dropna()
        .str.split(", ")
        .explode()
        .str.strip()
    )
    top_tags = tag_series.value_counts().head(25).reset_index()
    top_tags.columns = ["tag", "count"]
    tag_fig = px.bar(
        top_tags,
        x="count",
        y="tag",
        orientation="h",
        title="Most common EGS tags (top 25)",
        height=700,
    )
    mo.vstack([mo.md("## Tags / genres"), tag_fig])
    return


@app.cell
def _(event, mo, px):
    # quality of the giveaways: critic scores, and do MC and HLTB agree?
    score_fig = px.histogram(
        event[event["mc_criticScore"].notna()],
        x="mc_criticScore",
        nbins=30,
        title="Metacritic critic score distribution",
    )
    agree = event[event["mc_criticScore"].notna() & event["hltb_review_score"].notna()]
    agreement_fig = px.scatter(
        agree,
        x="mc_criticScore",
        y="hltb_review_score",
        hover_name="title",
        title="Metacritic vs HLTB review score (n={})".format(len(agree)),
    )
    mo.vstack([mo.md("## Quality — critic scores"), score_fig, agreement_fig])
    return


@app.cell
def _(event, mo, px):
    # how much game are you getting? main-story playtime in hours
    playtime = event[event["hltb_main_story"].notna()]
    playtime_fig = px.histogram(
        playtime,
        x="hltb_main_story",
        nbins=40,
        title="Main-story playtime (hours, HLTB) — n={}".format(len(playtime)),
    )
    mo.vstack([mo.md("## Playtime"), playtime_fig])
    return


@app.cell
def _(event, mo, px):
    # match-confidence read across the fuzzy-matched sources
    egs_scores = event[event["egs_match_score"].notna()]
    egs_score_fig = px.histogram(
        egs_scores,
        x="egs_match_score",
        nbins=20,
        title="EGS match score distribution (threshold 80) — n={}".format(len(egs_scores)),
    )
    mo.vstack([mo.md("## Match confidence (EGS)"), egs_score_fig])
    return


@app.cell
def _(event, mo):
    # low-confidence EGS matches worth a manual look (feeds the issues list)
    low_conf = event[
        event["egs_match_score"].notna() & (event["egs_match_score"] < 90)
    ][["title", "egs_match_title", "egs_match_score"]].drop_duplicates()
    mo.vstack([mo.md("### Low-confidence EGS matches (< 90)"), low_conf])
    return (low_conf,)


@app.cell
def _(event, mo):
    # cross-source agreement: where EGS and Wikipedia disagree on publisher
    both_pub = event[
        event["egs_publisher"].notna() & event["publisher_wiki"].notna()
    ].drop_duplicates("title")
    disagree = both_pub[
        both_pub["egs_publisher"].str.lower().str.strip()
        != both_pub["publisher_wiki"].str.lower().str.strip()
    ][["title", "egs_publisher", "publisher_wiki"]]
    mo.vstack(
        [
            mo.md(
                "### Publisher disagreements (EGS vs Wikipedia): "
                "{} of {} comparable".format(len(disagree), len(both_pub))
            ),
            disagree.head(30),
        ]
    )
    return


@app.cell
def _(event, game, low_conf, mo):
    # DATA ISSUES — the feedback list back into build/clean
    issues = []

    next_rows = int((event["giveaway_type"] == "next").sum())
    if next_rows:
        issues.append("{} 'next' marker rows (current/upcoming at scrape time)".format(next_rows))

    no_egs = int(game["egs_match_title"].isna().sum())
    issues.append("{} / {} titles have no EGS match (price/tags missing)".format(no_egs, len(game)))

    no_mc = int(game["mc_title"].isna().sum())
    issues.append("{} / {} titles have no Metacritic match".format(no_mc, len(game)))

    no_hltb = int(game["hltb_game_name"].isna().sum())
    issues.append("{} / {} titles have no HLTB match".format(no_hltb, len(game)))

    low = int(len(low_conf))
    issues.append("{} low-confidence EGS matches (< 90) to spot-check".format(low))

    dev_gap = int(event["egs_developer"].isna().sum() - event["egs_match_title"].isna().sum())
    issues.append("~{} matched events still missing egs_developer (opaque slug)".format(max(dev_gap, 0)))

    # a $0 retail price on a title that clearly is a real game (has MC/HLTB) is a
    # strong wrong-match / free-edition signal worth a manual pass
    zero_priced = game[
        game["egs_match_title"].notna()
        & (game["egs_original_price_usd"] == 0)
        & (game["mc_title"].notna() | game["hltb_game_name"].notna())
    ]
    issues.append(
        "{} matched real games priced $0 (likely wrong match or free-to-play — spot-check)".format(
            len(zero_priced)
        )
    )

    mo.md("## Data Issues (feedback loop)\n\n" + "\n".join("- " + i for i in issues))
    return


if __name__ == "__main__":
    app.run()
