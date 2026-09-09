# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marimo==0.23.2",
#   "pandas>=3.0.0; sys_platform != 'emscripten'",
#   "pandas==2.2.3; sys_platform == 'emscripten'",
#   "plotly>=6.7.0",
# ]
# ///
"""A portable marimo portfolio dashboard over a source-reconciled sample.

Run: uv run marimo run development/dashboard/app.py
Export: uv run python development/export_dashboard.py
"""

import marimo

__generated_with = "0.23.2"
app = marimo.App(
    width="full",
    app_title="The Giveaway Atlas",
    css_file="dashboard.css",
)


@app.cell
def _():
    import html
    from urllib.parse import quote

    import marimo as mo
    import pandas as pd
    import plotly.graph_objects as go

    return go, html, mo, pd, quote


@app.cell
def _(mo, pd):
    events = pd.read_json(str(mo.notebook_location() / "public/sample.json"))
    for _column in ["from_date", "to_date"]:
        events[_column] = pd.to_datetime(events[_column])
    games = events.drop_duplicates("title").sort_values("title").reset_index(drop=True)
    # Store labels mix genres with capabilities and player reactions. Keep a
    # named genre vocabulary for this view, with all original tags in details.
    genre_vocabulary = {
        "Action", "Action-Adventure", "Adventure", "Casual", "Dungeon Crawler",
        "Exploration", "Fighting", "Horror", "Indie", "Music", "Narration",
        "Open World", "Platformer", "Puzzle", "Racing", "Rogue-Lite", "RPG",
        "Shooter", "Simulation", "Sports", "Stealth", "Strategy", "Survival",
        "Turn-Based", "Turn-Based Strategy",
    }
    genres = sorted({
        tag.strip() for tags in games["egs_tags"] for tag in tags.split(",")
        if tag.strip() in genre_vocabulary
    })
    return events, games, genres


@app.cell
def _(mo):
    dark = mo.app_meta().theme == "dark"
    palette = {
        "ink": "#e9eff6" if dark else "#182b45",
        "muted": "#b0bfd2" if dark else "#53667c",
        "grid": "#344256" if dark else "#e2e8f0",
        "blue": "#7bafff" if dark else "#315fbe",
        "teal": "#53d6bd" if dark else "#007f70",
        "surface": "#1c293b" if dark else "#ffffff",
    }

    def chart_style(figure, height=350):
        """Apply shared readable chart styling without changing global Plotly state."""
        figure.update_layout(
            template="plotly_dark" if dark else "plotly_white",
            height=height, font={"family": "system-ui, sans-serif", "size": 14, "color": palette["muted"]},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 12, "r": 20, "t": 36, "b": 10},
            hoverlabel={"bgcolor": palette["surface"], "font_size": 14},
            legend={"orientation": "h", "y": 1.2, "x": 0},
        )
        figure.update_xaxes(zeroline=False, gridcolor=palette["grid"], automargin=True)
        figure.update_yaxes(zeroline=False, gridcolor=palette["grid"], automargin=True)
        return figure

    def plot(figure):
        """Render standard Plotly controls with responsive sizing and no vendor logo."""
        return mo.ui.plotly(figure, config={"displaylogo": False, "responsive": True})

    return chart_style, palette, plot


@app.cell
def _(mo):
    reset_filters = mo.ui.button(
        value=0, on_click=lambda value: value + 1, label="Reset all filters", full_width=True
    )
    return (reset_filters,)


@app.cell
def _(genres, mo, reset_filters):
    _reset = reset_filters.value
    search = mo.ui.text(placeholder="Try Alien or Amnesia…", label="Find a game", full_width=True)
    years = mo.ui.range_slider(2018, 2025, step=1, value=(2018, 2025), label="Giveaway years", show_value=True, full_width=True)
    genre_filter = mo.ui.multiselect(genres, value=[], label="Genres · match any", full_width=True)
    time_budget = mo.ui.dropdown(
        {"Any length": 500, "One sitting · ≤ 3 h": 3, "A weekend · ≤ 8 h": 8,
         "A few evenings · ≤ 15 h": 15, "A longer journey · ≤ 30 h": 30},
        value="Any length", label="Main-story time", full_width=True,
    )
    minimum_score = mo.ui.slider(0, 100, step=5, value=0, label="Minimum critic score", show_value=True, full_width=True)
    return genre_filter, minimum_score, search, time_budget, years


@app.cell
def _(
    genre_filter,
    minimum_score,
    mo,
    reset_filters,
    search,
    time_budget,
    years,
):
    mo.sidebar(
        mo.vstack([
            mo.Html('<div class="atlas-brand"><span class="atlas-symbol">G / A</span><strong>GIVEAWAY ATLAS</strong></div>'),
            mo.Html('<div class="atlas-eyebrow">YOUR EXPLORATION</div>'),
            search, years, genre_filter, time_budget, minimum_score,
            reset_filters,
            mo.Html('<p class="atlas-small">Filters update the metrics, charts, and tables together. Select several genres to match any of them.</p>'),
        ], gap=1.4),
        footer=mo.Html('<div class="atlas-sidebar-foot">EPIC GAMES STORE<br><strong>Independent portfolio study</strong><br>40-game design sample · 2018–2025</div>'),
        width="270px",
    )
    return


@app.cell
def _(events, genre_filter, minimum_score, search, time_budget, years):
    def select_view(data, year_bounds, query="", selected_genres=(), max_hours=500, score_floor=0):
        """Filter event rows, then derive one row per game for unbiased game summaries.

        Year bounds apply to giveaway starts. Genre matching uses OR semantics;
        title search is literal and case-insensitive. Empty selections produce
        empty frames. A game's full sample history remains available separately.
        """
        mask = (
            data["giveaway_year"].between(*year_bounds)
            & data["hltb_main_story"].le(max_hours)
            & data["mc_criticScore"].ge(score_floor)
            & data["title"].str.contains(query.strip(), case=False, regex=False)
        )
        if selected_genres:
            wanted = set(selected_genres)
            mask &= data["egs_tags"].map(
                lambda tags: bool(wanted.intersection(tag.strip() for tag in tags.split(",")))
            )
        filtered_events = data.loc[mask].sort_values(["from_date", "title"]).reset_index(drop=True)
        filtered_games = filtered_events.drop_duplicates("title").reset_index(drop=True)
        counts = filtered_events.groupby("title", as_index=False).agg(
            windows_in_view=("from_date", "size"), first_in_view=("from_date", "min")
        )
        filtered_games = filtered_games.merge(counts, on="title", validate="1:1")
        return filtered_events, filtered_games

    filtered_events, filtered_games = select_view(
        events, years.value, search.value, genre_filter.value, time_budget.value, minimum_score.value
    )
    return filtered_events, filtered_games


@app.cell
def _(filtered_events, filtered_games, games, mo, years):
    _n = len(filtered_games)
    _game_word = "game" if _n == 1 else "games"
    _low, _high = years.value
    _score = f'{filtered_games["mc_criticScore"].median():.0f}' if _n else "—"
    _time = f'{filtered_games["hltb_main_story"].median():.1f}<small> h</small>' if _n else "—"
    _price = f'${filtered_games["egs_original_price_usd"].median():.2f}' if _n else "—"
    _metrics = [
        (str(_n), "Games in view", f"of {len(games)} sampled games"),
        (_score, "Median critic score", f"{_n} {_game_word} · Metacritic / 100"),
        (_time, "Median main story", f"{_n} estimates · HowLongToBeat"),
        (_price, "Median cached list price", "USD · observation dates unavailable"),
    ]
    _cards = "".join(
        f'<div class="atlas-metric"><span>{label}</span><strong>{value}</strong><p>{caption}</p></div>'
        for value, label, caption in _metrics
    )
    mo.Html(f'''
        <div class="atlas-heading">
          <div><div class="atlas-eyebrow">EPIC GAMES STORE / AN INDEPENDENT STUDY</div>
          <h1>The Giveaway Atlas<span>.</span></h1>
          <p>Explore the games, the time they ask for, and when they were free.</p></div>
          <div class="atlas-sample">DESIGN SAMPLE<strong>40 games / 2018–2025</strong></div>
        </div>
        <div class="atlas-scope"><span class="atlas-dot"></span><strong>{_n} {_game_word}</strong>
        <span>· {len(filtered_events)} game giveaway windows · {_low}–{_high}</span>
        <span class="atlas-scope-note">Sample only. Historical giveaways; availability has ended.</span></div>
        <div class="atlas-metrics">{_cards}</div>
    ''')
    return


@app.cell
def _(chart_style, filtered_games, genres, go, mo, palette, plot):
    _figure = go.Figure()
    _short = filtered_games["hltb_main_story"].le(8) & filtered_games["mc_criticScore"].ge(80)
    for _mask, _name, _color in [
        (~_short, "Other games in view", palette["blue"]),
        (_short, "Weekend picks · ≤ 8 h & 80+", palette["teal"]),
    ]:
        _data = filtered_games.loc[_mask]
        _figure.add_trace(go.Scatter(
            x=_data["hltb_main_story"], y=_data["mc_criticScore"], mode="markers", name=_name,
            customdata=_data[["title", "egs_original_price_usd"]].to_numpy(),
            marker={"size": 12, "color": _color, "opacity": 0.85, "line": {"width": 1.5, "color": palette["surface"]}},
            hovertemplate="<b>%{customdata[0]}</b><br>Main story: %{x:.1f} h<br>Critic score: %{y:.0f}/100<br>Cached list price: $%{customdata[1]:.2f}<extra></extra>",
        ))
    _figure.add_hline(y=80, line_dash="dot", line_color=palette["grid"])
    _figure.add_vline(x=8, line_dash="dot", line_color=palette["grid"])
    _figure.update_xaxes(type="log", title="Main-story hours · logarithmic scale", tickvals=[1, 2, 4, 8, 16, 32, 64, 128])
    _figure.update_yaxes(title="Metacritic critic score", range=[min(50, filtered_games["mc_criticScore"].min() - 5) if len(filtered_games) else 50, 100])
    if filtered_games.empty:
        _figure.add_annotation(text="No games match. Try widening your filters.", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    _scatter = plot(chart_style(_figure, 370))

    # Bundled Pyodide has pandas 2.2.3; the project stays on 3.0+. Plain column
    # assignment keeps this presentation code compatible with both runtimes.
    _tags = filtered_games[["title", "egs_tags"]].copy()
    _tags["tag"] = _tags["egs_tags"].str.split(", ")
    _tags = _tags.explode("tag").reset_index(drop=True)
    _tags = _tags.loc[_tags["tag"].isin(genres)].drop_duplicates(["title", "tag"])
    _counts = _tags.groupby("tag", as_index=False).agg(games=("title", "nunique"))
    _counts = _counts.sort_values(["games", "tag"], ascending=[False, True]).head(8).sort_values("games").reset_index(drop=True)
    _bars = go.Figure(go.Bar(
        x=_counts["games"], y=_counts["tag"], orientation="h", marker_color=palette["blue"],
        text=_counts["games"], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x} games in view<extra></extra>",
    ))
    _bars.update_xaxes(title="Distinct games", dtick=5 if len(filtered_games) > 15 else 1)
    _bars.update_yaxes(showgrid=False)
    if _counts.empty:
        _bars.update_xaxes(visible=False)
        _bars.update_yaxes(visible=False)
        _bars.add_annotation(
            text="No genre counts for this selection.", x=0.5, y=0.5,
            xref="paper", yref="paper", showarrow=False,
        )
    _tag_chart = plot(chart_style(_bars, 370))
    discovery_charts = mo.hstack([
        mo.vstack([
            mo.Html('<div class="atlas-section-head"><span>01 / DISCOVER</span><h2>A good game. A little time.</h2><p>Each dot is a game. Hover for details; zoom to explore. Teal marks 80+ scores and stories of eight hours or less.</p></div>'),
            _scatter,
        ]).style({"flex": "1 1 540px", "min-width": "0"}),
        mo.vstack([
            mo.Html('<div class="atlas-section-head"><span>02 / THE MIX</span><h2>What’s in the library?</h2><p>The eight most common genre tags in view. Games can belong to more than one genre.</p></div>'),
            _tag_chart,
        ]).style({"flex": "1 1 320px", "min-width": "0"}),
    ], wrap=True, gap=2, align="start").style({"border-bottom": "1px solid var(--atlas-border)", "padding-bottom": "1rem"})
    return (discovery_charts,)


@app.cell
def _(filtered_games, mo):
    _table = filtered_games.sort_values(["mc_criticScore", "title"], ascending=[False, True])[[
        "title", "mc_criticScore", "hltb_main_story", "egs_original_price_usd", "windows_in_view"
    ]].reset_index(drop=True).rename(columns={
        "title": "Game", "mc_criticScore": "Critic / 100", "hltb_main_story": "Main story · h",
        "egs_original_price_usd": "Cached price · USD", "windows_in_view": "Windows in view",
    })
    game_table = mo.ui.table(
        _table, selection="single", initial_selection=[0] if len(_table) else [],
        page_size=8, show_column_summaries=False, show_data_types=False,
        format_mapping={"Critic / 100": "{:.0f}", "Main story · h": "{:.1f}", "Cached price · USD": "${:.2f}"},
        label="Games in view · select a row to inspect its history and sources",
    )
    return (game_table,)


@app.cell
def _(events, filtered_events, game_table, games, html, mo, quote):
    if len(game_table.value) == 0:
        game_detail = mo.Html('<div class="atlas-detail"><div class="atlas-eyebrow">GAME FILE</div><h3>Find your next game.</h3><p>Select a table row to see its giveaway history and source records.</p></div>')
    else:
        _title = game_table.value.iloc[0]["Game"]
        _game = games.loc[games["title"].eq(_title)].iloc[0]
        _history = events.loc[events["title"].eq(_title)].sort_values("from_date")
        _history_html = "".join(
            '<li><strong>{}</strong><span>to {} · sheet row {}</span></li>'.format(
                row.from_date.strftime("%d %b %Y"), row.to_date.strftime("%d %b %Y"), row.source_sheet_row
            ) for row in _history.itertuples()
        )
        _safe_title = html.escape(_title)
        _description = html.escape(_game["egs_short_description"])
        _publisher = html.escape(_game["egs_publisher"])
        _developer = html.escape(_game["developer_wiki"])
        _tag_html = " ".join('<span>{}</span>'.format(html.escape(tag.strip())) for tag in _game["egs_tags"].split(","))
        _mc_url = "https://www.metacritic.com/game/" + quote(_game["mc_slug"], safe="") + "/"
        _wiki_url = html.escape(_game["link_wiki"], quote=True)
        _sheet_url = "https://docs.google.com/spreadsheets/d/1B2S4kj4PY_U7W5daQyLbv1XvFIFm64o0lFv0Q4fxZIA/edit#range=A" + str(_history.iloc[0]["source_sheet_row"])
        _hours = f'{_game["hltb_main_story"]:.1f}'
        _score = f'{_game["mc_criticScore"]:.0f}'
        _price = f'{_game["egs_original_price_usd"]:.2f}'
        _in_view = len(filtered_events.loc[filtered_events["title"].eq(_title)])
        game_detail = mo.vstack([
            mo.Html(f'''<div class="atlas-detail">
                <div class="atlas-eyebrow">GAME FILE / {_in_view} WINDOW(S) IN VIEW</div>
                <h3>{_safe_title}</h3>
                <div class="atlas-game-stats"><strong>{_score}<small> critic / 100</small></strong><strong>{_hours}<small> hours</small></strong><strong>${_price}<small> cached</small></strong></div>
                <p>{_description}</p>
                <p class="atlas-small">Developer: {_developer}<br>Publisher: {_publisher}</p>
                <h4>Giveaway history · full sample</h4><ul class="atlas-timeline">{_history_html}</ul>
                <div class="atlas-links"><a href="{_mc_url}" target="_blank" rel="noopener noreferrer">Metacritic ↗</a><a href="{_wiki_url}" target="_blank" rel="noopener noreferrer">Wikipedia ↗</a><a href="{_sheet_url}" target="_blank" rel="noopener noreferrer">Source sheet ↗</a></div>
            </div>'''),
            mo.accordion({"All store tags & matched records": mo.vstack([
                mo.Html(f'<div class="atlas-tags">{_tag_html}</div>'),
                mo.ui.table(_game[["egs_match_title", "mc_title", "hltb_game_name", "title_wiki", "egs_namespace", "egs_offer_id"]].rename_axis("Source field").reset_index(name="Cached record"), selection=None, show_column_summaries=False, show_data_types=False),
                mo.md("HLTB game URL and price observation date are not stored in the cache. Metacritic score platform is unspecified."),
            ])}),
        ], gap=0.5)
    return (game_detail,)


@app.cell
def _(chart_style, filtered_events, go, mo, palette, pd, plot, years):
    _year_list = list(range(years.value[0], years.value[1] + 1))
    _counts = pd.DataFrame({"year": _year_list})
    for _name, _mask in [
        ("First in sample history", filtered_events["sample_occurrence"].eq(1)),
        ("Returning in sample history", filtered_events["sample_occurrence"].gt(1)),
    ]:
        _group = filtered_events.loc[_mask].groupby("giveaway_year").size().reset_index(name=_name)
        _counts = _counts.merge(_group, left_on="year", right_on="giveaway_year", how="left").drop(columns="giveaway_year")
        _counts[_name] = _counts[_name].fillna(0).astype(int)
    _figure = go.Figure()
    for _name, _color in [("First in sample history", palette["blue"]), ("Returning in sample history", palette["teal"])]:
        _figure.add_bar(x=_counts["year"], y=_counts[_name], name=_name, marker_color=_color, hovertemplate="%{x}<br>%{y} game windows<extra>%{fullData.name}</extra>")
    _figure.update_layout(barmode="stack", bargap=0.55)
    _figure.update_xaxes(dtick=1, title="Giveaway start year")
    _figure.update_yaxes(dtick=1, title="Game giveaway windows")
    _event_table = filtered_events[["title", "from_date", "to_date", "sample_occurrence", "source_sheet_row"]].copy()
    for _column in ["from_date", "to_date"]:
        _event_table[_column] = _event_table[_column].dt.strftime("%Y-%m-%d")
    _event_table.columns = ["Game", "Started", "Ended", "Occurrence in sample history", "Source sheet row"]
    history_view = mo.vstack([
        mo.Html('<div class="atlas-section-head"><span>03 / HISTORY</span><h2>When did these games appear?</h2><p>One count per game and giveaway window. Two games given away together count twice. This selected sample cannot establish the program’s yearly cadence.</p></div>'),
        plot(chart_style(_figure, 320)),
        mo.ui.table(_event_table, selection=None, page_size=10, show_column_summaries=False, show_data_types=False, label="Source-backed windows in view · download for inspection"),
    ], gap=1)
    return (history_view,)


@app.cell
def _(mo):
    methodology_view = mo.md("""
    ## A small, inspectable slice

    This prototype uses **40 real games and 42 giveaway windows** selected from
    the repository’s saved data. It illustrates the finished exploration experience;
    it is not an estimate of the whole Epic giveaway program.

    **What made the cut.** Completed, ordinary PC game giveaways in 2018–2025,
    with no special source notes. Titles agree across Epic, Metacritic,
    HowLongToBeat, and Wikipedia after ignoring only case and punctuation.
    Every displayed score, main-story estimate, cached USD price, and genre
    record is present. Shared store IDs, conflicting displayed metadata,
    duplicated windows, and edition/collection names are excluded.

    **How the sample was chosen.** From 122 eligible games, a fixed title hash
    orders games within each first-giveaway year; selection rotates across years
    until 40 games are included. This prioritizes a useful range for the mock-up,
    not representativeness. Fully enriched games can differ systematically from
    those without enrichment. Matching cached names is not independent source verification.

    **What a number means.** Metrics and genre counts use distinct games;
    history counts game/window pairs. A repeat never adds another copy of a game
    to the score or price median. Year filters select giveaway starts. Game files
    retain full *sample* history so narrowing a year does not hide an earlier window.
    Genres use OR matching and can overlap.

    **Price.** Saved US list price for the matched product. Observation dates are
    unavailable. It is not today’s price, the price on the giveaway date, money
    saved, or Epic’s expenditure.

    **Ratings and time.** Metacritic critic scores are out of 100; the cache does
    not identify which platform supplies the score. HowLongToBeat main-story
    values are community estimates. “Weekend picks” means ≤ 8 hours and a critic
    score ≥ 80, a transparent browsing shortcut rather than a prediction for you.
    The playtime chart uses a logarithmic scale so long games remain visible.

    **Provenance.** Source windows come from the 29 April 2026 community-sheet
    snapshot; every event retains its Excel row number. Product metadata comes
    from the saved enrichment caches. Open a game file to inspect matched titles
    and source links, or download the tables. The repository includes the full
    selection script, input fingerprints, and per-event audit evidence.

    **Implementation.** Python, pandas, Plotly, and marimo. The static export runs
    Python in your browser via WebAssembly; it needs no application server and
    can be hosted on a conventional website. The initial runtime download needs
    an internet connection. This project is independent of Epic Games.
    """)
    return (methodology_view,)


@app.cell
def _(mo):
    view_selector = mo.ui.tabs({
        "Discover games": mo.Html(""),
        "Giveaway history": mo.Html(""),
        "Data & methods": mo.Html(""),
    })
    view_selector
    return (view_selector,)


@app.cell
def _(
    discovery_charts,
    filtered_games,
    game_detail,
    game_table,
    history_view,
    methodology_view,
    mo,
    view_selector,
):
    _empty = mo.callout("No games match this combination. Widen the year range, lower the score, or reset the filters.", kind="info") if filtered_games.empty else mo.Html("")
    _browser = mo.hstack([
        mo.vstack([
            mo.Html('<div class="atlas-section-head"><span>THE COLLECTION</span><h2>Explore the games</h2><p>Sort a column, download your selection, or choose a row to open its game file.</p></div>'),
            game_table,
        ]).style({"flex": "1.6 1 540px", "min-width": "0"}),
        game_detail.style({"flex": "1 1 320px", "min-width": "0"}),
    ], wrap=True, gap=2, align="start")
    _views = {
        "Discover games": mo.vstack([_empty, discovery_charts, _browser], gap=2),
        "Giveaway history": history_view,
        "Data & methods": methodology_view,
    }
    _views[view_selector.value]
    return


@app.cell
def _(mo):
    mo.Html('<footer class="atlas-footer"><strong>THE GIVEAWAY ATLAS</strong><span>Independent analysis · Python / pandas / Plotly / marimo</span><span>Design sample · historical offers</span></footer>')
    return


if __name__ == "__main__":
    app.run()
